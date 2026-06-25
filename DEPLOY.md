# Deployment (Docker, single server + single domain)

This runs the whole stack with Docker Compose on one server:

- **db** — PostgreSQL 16 (data persisted in a named volume)
- **backend** — Django + Gunicorn (migrations run automatically on start)
- **frontend** — React build served by Nginx, which also proxies `/api`,
  `/admin`, and `/static` to the backend

Only the **frontend** container is exposed (port 80). Everything else talks over
the internal Docker network.

```
Browser ──▶ frontend (nginx :80)
                 ├── /            → React SPA
                 ├── /api/*       → backend:8000
                 ├── /admin/*     → backend:8000
                 └── /static/*    → backend:8000
backend (gunicorn :8000) ──▶ db (postgres :5432)
```

## 1. Prerequisites

- A server with Docker Engine + Docker Compose plugin installed
- A domain pointed at the server's public IP (an `A` record)
- Ports 80 (and 443 if you add TLS) open in the firewall

## 2. Configure environment

From the project root:

```bash
cp .env.docker.example .env
```

Edit `.env` and set real values. Important ones:

- `DJANGO_SECRET_KEY` — long random string
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
- `CORS_ALLOWED_ORIGINS=https://yourdomain.com`
- `CSRF_TRUSTED_ORIGINS=https://yourdomain.com`
- `POSTGRES_PASSWORD` — strong password
- `LASOO_ENCRYPTION_KEY` — base64 of 32 bytes

Generate secrets:

```bash
# Django secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Lasoo encryption key (base64 of 32 bytes)
python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
```

> `docker compose` automatically reads the `.env` file in this directory.

## 3. Build and start

```bash
docker compose build
docker compose up -d
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f backend
```

Migrations run automatically when the backend container starts.

## 4. Create an admin user

```bash
docker compose exec backend python manage.py createsuperuser
```

The app is now reachable at `http://yourdomain.com`.

## 5. Add HTTPS (recommended)

The simplest path is to put a TLS-terminating reverse proxy in front, or run
Certbot on the host and proxy to the frontend container. A common approach:

1. Install Nginx + Certbot on the host (outside Docker).
2. Change the frontend port mapping in `docker-compose.yml` to e.g.
   `"8080:80"` so the host Nginx can bind 80/443.
3. Host Nginx proxies `https://yourdomain.com` → `http://127.0.0.1:8080`,
   forwarding `X-Forwarded-Proto https`.

Django already trusts `X-Forwarded-Proto` (see `SECURE_PROXY_SSL_HEADER`), so
HTTPS detection works once the proxy sets that header. Make sure
`CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` use the `https://` scheme.

## 6. Common operations

```bash
# Apply code changes
git pull
docker compose build
docker compose up -d

# Run migrations manually (normally automatic)
docker compose exec backend python manage.py migrate

# Open a Django shell
docker compose exec backend python manage.py shell

# Stop everything
docker compose down

# Stop AND delete the database volume (destructive!)
docker compose down -v
```

## 7. Backups

The database lives in the `pgdata` volume. Back it up with:

```bash
docker compose exec db pg_dump -U postgres leeso > backup_$(date +%F).sql
```

Restore with:

```bash
cat backup.sql | docker compose exec -T db psql -U postgres leeso
```

## Notes

- `DEBUG=False` enables secure cookies; you must serve over HTTPS for login to
  work in browsers, otherwise the secure session/CSRF cookies won't be sent.
  For a quick HTTP-only test, set `DJANGO_DEBUG=True` temporarily.
- Static files for the Django admin are collected at build time and served by
  WhiteNoise from the backend container.
