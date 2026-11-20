# SmartPark API

## Local setup

Requires Python 3.11+ and a PostgreSQL database with PostGIS enabled. A hosted
PostGIS-compatible database such as Neon is suitable.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to a PostgreSQL connection string. Set a long,
random `ADMIN_API_KEY` before exposing the administration API. Configure
`GOOGLE_MAPS_API_KEY` for Places API (New) destination and parking searches.
Configure `CORS_ORIGINS` as a JSON array containing the frontend origins. The initial
migration creates the PostGIS extension and SmartPark tables; the database role
must be allowed to create the extension or the extension must already be
installed.

```powershell
alembic upgrade head
uvicorn app.main:app --reload --port 8002
```

The health endpoint is `http://localhost:8002/api/health`. It checks both the
API and its database connection.

## Karachi road network

After applying the database migrations, run the repeatable, bounded import from
the `backend` directory:

```powershell
python -m app.ingest_road_network
```

The importer geocodes Bahria University Karachi, Saddar, and Clifton, then
retrieves OSM roads within a 2 km radius of each result. It stores OSM
intersection IDs and directed segments with calculated distances and
mode-specific access tags. It downloads and validates all three regions before
atomically replacing the existing road-network tables. Run it manually when
refreshing OSM data; normal map interactions do not make these requests.

## Destination search

`GET /api/destinations/search` searches Google Places (New) and returns
transient suggestions. It does not store Google place names or addresses.

| Parameter | Requirement |
| --- | --- |
| `q` | Required; 2–150 characters |
| `limit` | Optional; 1–10, defaults to 5 |
| `latitude` and `longitude` | Optional location bias; provide both together |

Search results contain an ID, name, category, address, and latitude/longitude.
`GET /api/destinations/{id}` only retrieves older stored destinations. Provider
rate limits return `429` and may include `Retry-After`; other provider failures
return `502`.

## Parking search and recommendations

`GET /api/parking/search` fetches Google Places parking facilities
near the requested coordinates. It accepts `latitude`, `longitude`,
`radius_meters` (100–50000, default 1500), and `limit` (1–50, default 10).
Results include Google place details and a clearly labeled straight-line
distance; it does not imply live availability.

`GET /api/parking/recommendations` accepts destination `latitude` and
`longitude`, `vehicle_type` (`car` or `bike`), an optional paired
`user_latitude`/`user_longitude`, `radius_meters` (100–50000, default 2000), and
`limit` (1–5, default 5). Explicitly incompatible parking is excluded. Results
include destination distance, optional straight-line distance from the user,
known fee, verification state, availability state, and data source. Distance
methods are explicit: `road` uses Dijkstra over the imported directed Karachi
network; `straight_line` is an honest fallback when the graph does not cover
the search. No straight-line estimate is represented as a road distance.

Google facilities are marked unverified with availability unknown.
Admin-maintained database records are included in recommendations.
Provider rate limits return `429`; other provider failures return `502`.

## Parking administration

Set `ADMIN_API_KEY` in the backend environment. Every `/api/admin/parking`
request requires `Authorization: Bearer <ADMIN_API_KEY>`. If no key is
configured, the API returns `503` and remains disabled.

- `GET /api/admin/parking` lists records.
- `POST /api/admin/parking` creates a record.
- `PATCH /api/admin/parking/{id}` edits fields, verifies a record, or changes
  its availability.
- `DELETE /api/admin/parking/{id}` removes a record.

The `/admin` frontend prompts for the key and keeps it only in page memory. Use
HTTPS in production and rotate the key if it is exposed.

## Driving and walking routes

Set `OPENROUTESERVICE_API_KEY` in the backend `.env` file. The key is sent only
from the backend and is never returned to the frontend.

`POST /api/routes/{mode}` accepts `car`, `bike`, or `walk`:

```json
{
  "origin": { "latitude": 24.86, "longitude": 67.01 },
  "destination": { "latitude": 24.87, "longitude": 67.02 }
}
```

The response contains a GeoJSON `LineString`, `distanceMeters`, and
`durationSeconds`. Car and motorcycle (`bike`) routes use OpenRouteService's
`driving-car` profile; walking routes use `foot-walking`. OpenRouteService has
no motorcycle-specific profile, so bike routes do not model motorcycle-only
restrictions or guarantees. Missing credentials return `503`, provider rate
limits return `429`, and other provider failures return `502`.

## Geographic providers

The backend uses Photon for destination geocoding and Overpass for OpenStreetMap
parking discovery. Provider results are normalized and cached in process for
`GEODATA_CACHE_TTL_SECONDS`; provider failures and rate limits are surfaced to
API callers. Respect provider usage policies and include OpenStreetMap
attribution in the app.

## Tests

```powershell
python -m pytest -q
```

## Production container

Build the API image from the `backend` directory. Configure environment values
through the hosting provider; do not copy `.env` into the image. Apply
`python -m alembic upgrade head` as a release/pre-deploy step before starting
`uvicorn app.main:app --host 0.0.0.0 --port 8000`.
