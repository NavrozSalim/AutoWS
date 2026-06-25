# Leeso / Lasoo Marketplace Integration

A full-stack system to connect Lasoo marketplace stores, create listings (form or
CSV/Excel), validate them, convert them to Lasoo's `Variants_BulkUpsert` payload,
upload to **Staging first**, complete a staging checklist, then switch to
**Production**.

- **Backend:** Django + Django Ninja + PostgreSQL (JWT auth)
- **Frontend:** React (Vite + TypeScript) + Tailwind CSS
- **Per-store config:** Each connection stores its own base URLs, endpoint paths,
  and encrypted AuthKeys — so one user can connect multiple Lasoo stores.

---

## Architecture

```
backend/                 Django + Ninja API
  config/                project settings, root API, URLs
  lasoo/
    models.py            connections, listings, orders, shipments
    schemas.py           Ninja request/response schemas
    serializers.py       model -> safe dict (masks secrets)
    api.py               all /api/lasoo/* routes (JWT + per-user scoping)
    checklist.py         8-step staging checklist
    services/
      crypto.py          AES-256-GCM encrypt/decrypt + masking
      mapper.py          fields -> Variants_BulkUpsert payload
      validator.py       per-variant validation messages
      client.py          LasooClient (per-connection base URL + AuthKey)
      connection_service.py
      listing_service.py
      order_service.py
      shipping_service.py
    utils/csv_import.py   CSV/Excel parsing + template
frontend/                React SPA
  src/pages/             Marketplaces, Connect, ConnectionDetail, Listings,
                         CreateListing, BulkUpload, Orders, Shipping, Login
  src/api/               axios client (JWT refresh) + typed Lasoo calls
```

---

## Backend setup

```bash
cd backend
py -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

Create a Postgres database:

```bash
createdb leeso        # or use psql / pgAdmin
```

Configure environment — copy `.env.example` to `.env` and fill in:

```bash
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux
```

Generate the encryption key (required) and paste it into `LASOO_ENCRYPTION_KEY`:

```bash
python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
```

Run migrations and start the server:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver          # http://localhost:8000
```

API docs are auto-generated at `http://localhost:8000/api/docs`.

Run the unit tests (mapper + validator — the riskiest logic):

```bash
python manage.py test
```

---

## Frontend setup

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

The dev server proxies `/api` to `http://localhost:8000`, so no extra CORS config
is needed in development.

---

## Per-store configuration (important)

Lasoo base URLs, endpoint paths, and AuthKeys are **not** read from `.env`. They
are entered in the **Connect Marketplace** form and stored per connection, so each
store can use independent Staging/Production settings. `.env` only holds
app-wide secrets (Django secret, database URL, encryption key) and optional
default values that prefill the Connect form.

---

## Environment flow

1. Connect a store with its **Staging** base URL + AuthKey (Production optional).
2. Create/upload listings → validate → **Upload to Staging**.
3. Lasoo maps the variants (mark the manual checklist step).
4. Create test orders in Lasoo → **Fetch from Lasoo** to retrieve invoices.
5. Send shipping info → mark shipping complete.
6. Approve for production (manual checklist step).
7. Once all 8 staging steps are done **and** a Production AuthKey is set,
   **Switch to Production** unlocks, then **Upload to Production**.

---

## Security

- AuthKeys encrypted at rest with AES-256-GCM (`LASOO_ENCRYPTION_KEY`).
- Frontend only ever receives masked keys (`****abcd`).
- Stored request payloads scrub the AuthKey (`"auth": "***"`).
- Every API query is scoped to the authenticated user; you can only access your
  own connections, listings, and orders.

---

## Configurable endpoints

Default Lasoo endpoint paths are placeholders. When Lasoo provides the real
Postman endpoints, update them per store in the **Advanced** section of the
Connect form (or via `PUT /api/lasoo/connections/{id}`), or change the defaults
in `backend/.env`.
