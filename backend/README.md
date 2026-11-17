# SmartPark API

## Local setup

Requires Python 3.11+ and PostgreSQL with PostGIS enabled.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to a PostgreSQL connection string. The initial
migration creates the PostGIS extension and SmartPark tables; the database role
must be allowed to create the extension or the extension must already be
installed.

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The health endpoint is `http://localhost:8000/api/health`. It checks both the
API and its database connection. Configure `CORS_ORIGINS` as a JSON array when
the frontend runs from a different origin.

## Tests

```powershell
pytest
```
