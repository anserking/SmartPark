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

`GET /api/destinations/search` geocodes a destination with Photon, stores
results in the database, and returns matching cached suggestions from the
process-local Trie index.

| Parameter | Requirement |
| --- | --- |
| `q` | Required; 2–150 characters |
| `limit` | Optional; 1–10, defaults to 5 |
| `latitude` and `longitude` | Optional location bias; provide both together |

Search results contain an ID, name, category, address, and latitude/longitude.
Use `GET /api/destinations/{id}` to retrieve a stored destination. Provider
rate limits return `429` and may include `Retry-After`; other provider failures
return `502`.

## Geographic providers

The backend uses Photon for destination geocoding and Overpass for OpenStreetMap
parking discovery. Provider results are normalized and cached in process for
`GEODATA_CACHE_TTL_SECONDS`; provider failures and rate limits are surfaced to
API callers. Respect provider usage policies and include OpenStreetMap
attribution in the app.

## Tests

```powershell
pytest
```
