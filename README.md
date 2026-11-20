# SmartPark

SmartPark helps drivers in Karachi find parking near a destination, choose a
vehicle-compatible facility, drive to it, confirm parking, and continue on foot.

## MVP features

- Destination search and autocomplete powered by Google Places (New).
- Nearby Google parking discovery with car/bike compatibility filtering.
- Top-five recommendations ranked by imported road distance when the Karachi
  road graph covers the area; otherwise, results are clearly labeled as
  straight-line estimates.
- A Google map with destination, user, parking, driving, and walking layers.
- A guarded drive → park → walk → arrive navigation flow using OpenRouteService.
- Admin-key-protected parking record management for create, edit, verify,
  unavailable, and delete actions.
- Installable PWA shell. Network-backed API results and map tiles still require
  connectivity.

## Architecture

- **Frontend:** React, TypeScript, Vite, Tailwind, React Router, TanStack Query,
  Zustand, and Google Maps JavaScript API.
- **API:** FastAPI, Pydantic, SQLAlchemy 2, and Alembic.
- **Database:** PostgreSQL with PostGIS. Use a hosted PostGIS-compatible
  database such as Neon.
- **External data:** Google Places for destination and parking search, Overpass
  for imported OSM roads, and OpenRouteService for driving/walking directions.

The browser receives the public Maps JavaScript demo key. Keep database,
admin, and OpenRouteService secrets in the backend environment.

## Run locally

Requirements: Node.js 18+, Python 3.11+, and a hosted PostgreSQL database with
PostGIS enabled.

1. Install frontend dependencies:

   ```powershell
   npm ci
   Copy-Item .env.example .env.local
   ```

   Local Vite requests use a same-origin `/api` proxy to `http://localhost:8002`,
   so browser CORS is not involved. Set `VITE_GOOGLE_MAPS_API_KEY` in
   `.env.local` to load the map.

2. Configure and run the backend:

   ```powershell
   Set-Location backend
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   Set `DATABASE_URL` to the hosted PostGIS connection string. Before exposing
   admin tools, set a long random `ADMIN_API_KEY`. For directions, set
   `OPENROUTESERVICE_API_KEY` and `GOOGLE_MAPS_API_KEY` for Places searches.
   Enable Maps JavaScript API and Places API (New), with billing and quotas.
   Set `CORS_ORIGINS` for any direct cross-origin
   production calls.

   ```powershell
   python -m alembic upgrade head
   python -m uvicorn app.main:app --reload --port 8002
   ```

   The health endpoint is `http://localhost:8002/api/health`. If that port is in
   use, configure `VITE_API_PROXY_TARGET` in `.env.local` to match the backend's
   host and port.

3. In a second terminal at the repository root, start the frontend:

   ```powershell
   npm run dev
   ```

   Open the URL Vite prints, usually `http://localhost:5173` or
   `http://localhost:5174`. The admin interface is at `/admin`; it remains
   unavailable until `ADMIN_API_KEY` is configured on the backend.

See [HOW_TO_RUN.md](./HOW_TO_RUN.md) for a compact Windows checklist and
[backend/README.md](./backend/README.md) for API, data, and migration details.

## Tests and build

```powershell
npm test
npm run build
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Deployment

Deployment configuration and environment-variable guidance are in
[HOW_TO_RUN.md](./HOW_TO_RUN.md). Deploy the frontend and API separately, apply
Alembic migrations before starting the API, and set the Vite API URL at frontend
build time. Do not commit `.env` files or provider credentials.

## Data, attribution, and known limits

- The dashboard uses a Google map and displays Google Places parking. Nearby
  facilities are not live occupancy data and show unknown availability until
  maintained through SmartPark administration.
- Straight-line recommendations are explicitly labeled whenever the imported
  road graph is missing or does not cover the searched facilities.
- Road import fetches bounded areas around Bahria University Karachi, Saddar,
  and Clifton. Provider outages can prevent refreshing the graph; see
  [backend/README.md](./backend/README.md).
- OpenRouteService has no motorcycle-specific profile. SmartPark uses its
  `driving-car` profile for cars and bikes and does not guarantee motorcycle
  restrictions.
- Offline mode caches only the application shell. Search, recommendations,
  directions, and map tiles require a network connection.

Contributions are welcome! Please feel free to submit a Pull Request.
