# Handle Easy

Split the restaurant bill among guests at the table. **Handle Easy is an
overlay on Odoo POS** — Odoo stays the source of truth for orders and
products; this app only owns tables, guest sessions, per-guest item
assignment, the split calculation, and payments. It never touches Odoo's
SQL directly (it talks to Odoo through a service layer, mocked for now).

## How it works

1. Staff open a session on a table and (optionally) bind the table's open
   Odoo POS order — its lines are mirrored into the session.
2. Each table has a QR code pointing to `/table/<qr_token>`.
3. Guests scan it, enter a name, and tick what they consumed. Shared lines
   (a bottle of wine) split equally between the guests who tick them.
4. The backend computes each guest's share; each guest pays their part.
5. When everything is paid the session closes and Odoo is told the order is
   settled.

## Stack

- **Frontend:** React + React Router + Context API + Axios + Bootstrap (Vite)
- **Backend:** Flask + Flask-JWT-Extended (httpOnly cookie) + SQLAlchemy +
  Alembic (Flask-Migrate)
- **DB:** PostgreSQL
- **Odoo:** `OdooClient` service, mock-first (`ODOO_MOCK=1`)

## Run locally (without Docker)

```bash
# 1. Config
cp .env.example .env            # tweak if needed

# 2. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)   # or set env vars however you like
flask db upgrade                       # create tables
flask seed                             # demo restaurant + open session
python src/app.py                      # API on http://localhost:3001

# 3. Frontend (another terminal)
npm install
npm run dev                            # SPA on http://localhost:3000
```

Demo login: **admin@demo.com / demo1234**. `flask seed` prints a guest URL
(`/table/<token>`) for table 8, which already has an imported order.

## Run with Docker

```bash
docker compose up --build
# frontend → http://localhost:3000, backend → http://localhost:3001
```

## Project layout

```
src/
  app.py  wsgi.py
  api/
    models.py schemas? utils.py admin.py commands.py
    routes/        auth, tables, sessions, customers, items, payments, reviews
    services/
      odoo/        client (mock/xmlrpc), sync, fixtures
      qr/          token + PNG generator
      payment/     mock gateway (Stripe-shaped)
      billing.py   compute_split — the splitting core
  front/
    pages/  components/  layouts/  hooks/  services/
```

## Wiring real Odoo later

Set `ODOO_MOCK=0` and fill each company's `odoo_url / odoo_database /
odoo_username / odoo_api_key`. The XML-RPC calls are stubbed in
`src/api/services/odoo/client.py` — implement the `NotImplementedError`
branches and the rest of the app is unchanged.
