# SmartPark

SmartPark helps drivers in Karachi find parking near a destination, choose a
vehicle-compatible facility, drive to it, confirm parking, and continue on foot.

## MVP features

- Destination search and autocomplete powered by Google Places (New).
- Destination-specific Google parking discovery, starting within 300 m and
  expanding only when no closer parking is found. Named car parks are recovered
  by text search even when Google classifies them under a different place type.
- Up to five recommendations ranked by straight-line distance to the destination.
- A Google map with destination, user, parking, driving, and walking layers.
- A selectable starting location using your position, place search, or a map pin.
- A guarded drive → park → walk → arrive navigation flow using Google Routes.
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
- **External data:** Google Places for destination and parking search and
  Google Routes for driving/walking directions. Legacy OSM import code is not
  used by the current journey.

The browser receives the public Maps JavaScript demo key. Keep database and
admin secrets in the backend environment.

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
   `GOOGLE_MAPS_API_KEY` for Places and Routes searches. Enable Maps JavaScript
   API, Places API (New), and Routes API, with billing and quotas.
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
- Recommendation distance is explicitly labeled as straight-line. The actual
  drive and walk routes come from Google Routes.
- Bike journeys currently use Google's drive mode; motorcycle-specific
  restrictions are not guaranteed.
- Offline mode caches only the application shell. Search, recommendations,
  directions, and map tiles require a network connection.

Contributions are welcome! Please feel free to submit a Pull Request.
