# Run and deploy SmartPark

See [README.md](./README.md) for the architecture and complete local setup.
This guide covers the Windows commands and deployment checklist.

## Local development

### Backend

Use Python 3.11+ and a hosted PostgreSQL/PostGIS database.

```powershell
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure `DATABASE_URL` in `backend\.env`. Set `ADMIN_API_KEY` to a long,
random value and `GOOGLE_MAPS_API_KEY` for server-side Places and Routes
requests. `CORS_ORIGINS`
should include the frontend origin for direct cross-origin production calls.

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8002
```

### Frontend

In another terminal:

```powershell
Set-Location E:\React\SmartPark
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Vite proxies `/api` to `http://localhost:8002` during development, avoiding
browser CORS configuration. Set `VITE_API_PROXY_TARGET` in `.env.local` if the
backend uses another host or port. Open `http://localhost:5173`.
Set `VITE_GOOGLE_MAPS_API_KEY` in `.env.local` for the Google map. The same
demo key may be used in both env files; it will be visible in the browser.
Enable Maps JavaScript API, Places API (New), and Routes API in the Google Cloud project,
and configure billing, quotas, and appropriate key restrictions. If Vite
chooses port 5174, open `http://localhost:5174` and include that origin in
`CORS_ORIGINS` when calling the API directly.

### Tests

```powershell
npm test
npm run build
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Production deployment

Deploy the static frontend to Netlify and FastAPI backend to Render, backed by
a hosted PostGIS database:

1. Create a PostGIS-enabled database and store its connection string as the
   backend's `DATABASE_URL` secret.
2. Create the Render service from `render.yaml`, using `backend\Dockerfile`. Run
   `python -m alembic upgrade head` as a release/pre-deploy command before
   serving traffic.
3. Set backend secrets `ADMIN_API_KEY` and `GOOGLE_MAPS_API_KEY`.
   Configure `CORS_ORIGINS` with the exact production frontend origin.
4. Deploy the frontend to Netlify. Use `npm run build`
   and `dist` as the publish directory. Set `VITE_API_BASE_URL` to the
   production API URL and `VITE_GOOGLE_MAPS_API_KEY` at build time.
5. Verify `/api/health`, destination search, parking recommendations, routes,
   and `/admin` using the configured key. The Maps JavaScript key is public;
   do not expose the admin key as a `VITE_*` variable.

The root `Dockerfile` builds the frontend for Nginx. Supply the public backend
URL as a build argument:

```powershell
docker build --build-arg VITE_API_BASE_URL=https://api.example.com -t smartpark-web .
```

Netlify SPA routing is configured in `netlify.toml`. This repository does not
contain a deployed project or provider account configuration; public deployment
must be completed in the chosen hosting accounts.

