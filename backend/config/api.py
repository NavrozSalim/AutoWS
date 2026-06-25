"""Root NinjaAPI instance: mounts auth + lasoo routers and global error handling."""
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from ninja import Router, Schema
from ninja.errors import ValidationError
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController

from lasoo.api import router as lasoo_router
from lasoo.errors import LasooError

logger = logging.getLogger("lasoo")

api = NinjaExtraAPI(title="Leeso Marketplace API", version="1.0.0")

# JWT auth controller -> /api/token/pair, /api/token/refresh, /api/token/verify
api.register_controllers(NinjaJWTDefaultController)


class RegisterIn(Schema):
    username: str
    email: str = ""
    password: str


class RegisterOut(Schema):
    id: int
    username: str


accounts_router = Router(tags=["accounts"])


@accounts_router.post("/register", response={201: RegisterOut})
def register(request, payload: RegisterIn):
    User = get_user_model()
    username = payload.username.strip()
    if not username or not payload.password:
        raise LasooError("Username and password are required.")
    if len(payload.password) < 8:
        raise LasooError("Password must be at least 8 characters.")
    try:
        user = User.objects.create_user(
            username=username, email=payload.email.strip(), password=payload.password
        )
    except IntegrityError as exc:
        raise LasooError("That username is already taken.", status_code=409) from exc
    return 201, {"id": user.id, "username": user.username}


api.add_router("/accounts", accounts_router)
api.add_router("/lasoo", lasoo_router)


@api.exception_handler(LasooError)
def handle_lasoo_error(request, exc: LasooError):
    return api.create_response(request, {"detail": exc.message}, status=exc.status_code)


@api.exception_handler(ValidationError)
def handle_validation_error(request, exc: ValidationError):
    return api.create_response(request, {"detail": exc.errors}, status=422)
