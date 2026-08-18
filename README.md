# goalapi

SOFTSOVE Portal API — FastAPI backend for task, project, and goal management.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Default owner login: `admin@softsove.com` / `admin123`  
Manager: `manager@softsove.com` / `manager123`

API docs: http://localhost:8000/docs

Copy `.env.example` to `.env`. Set `DATABASE_URL`, `APP_PUBLIC_URL`, `ADMIN_WHATSAPP`, Interakt, and SMTP when you have them.

Interakt task template URL button should be: `{APP_PUBLIC_URL}/t/{{1}}`

## PostgreSQL (aaPanel)

1. In aaPanel install **PostgreSQL** and create a database + user.
2. Copy `.env.example` to `.env` and set `DATABASE_URL`:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@127.0.0.1:5432/DBNAME
```

If the password has special characters (`@`, `#`, `%`, `/`), URL-encode them.

Tables are created automatically on first API start.
