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

API docs: http://localhost:8000/docs
