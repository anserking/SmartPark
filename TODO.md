# SmartPark project todos

These are the project tasks tracked for completing the MVP. Core implementation,
verification, and deployment documentation are complete. The remaining work is
ordered below: migrate map/providers, verify the migrated journey, then deploy.

Repository setup: the source is cloned into this folder. `origin` points to
`https://github.com/anserking/SmartPark.git`; `upstream` retains the original
`Johnkelvin-J/parking` source. The target repository had no branch refs when
checked.

1. [x] **Auditing the existing repository** (`repo-audit`)
   - Inspect the source tree, README, dependencies, architecture, Firebase, map/search/navigation workflows, license, tests, and technical debt.
   - Findings: React 18, TypeScript, Vite, Tailwind/shadcn UI, Leaflet maps, TanStack Query, and Firebase auth/Firestore/storage. The existing map, geolocation hook, parking spot types/services, layout, and UI controls are reusable; there is no destination geocoding, routing, FastAPI/PostGIS backend, DSA engine, or test suite. `DashboardPage.tsx` and `ParkingSpotsPage.tsx` disable TypeScript checking. README claims MIT, but no license file was present in the clone.
   - The source was cloned from `Johnkelvin-J/parking`; the current folder initially contained only `Skills/context.md` and this checklist.
2. [x] **Finalizing the implementation architecture** (`architecture-decisions`)
   - Depends on: `repo-audit`
   - Decision: keep React/TypeScript/Vite/Tailwind and retain Leaflet, since its existing map works and can display route GeoJSON without a costly migration. Add FastAPI and PostgreSQL/PostGIS; replace Firebase-backed parking data with backend APIs, use Zustand for navigation state, and keep routing credentials server-side. Remove unused Firebase-dependent user features from the core journey; implement only simple environment-configured protection for the minimal admin rather than adding complex authentication.
3. [x] **Establishing backend and database foundations** (`backend-database-foundation`)
   - Depends on: `architecture-decisions`
   - Added the FastAPI service, environment-based settings, database-aware health endpoint, SQLAlchemy 2 models, PostGIS/Alembic initial schema, local setup instructions, and Python ignores. Verified with 2 passing tests, Python compilation, and migrations `0001`–`0002` applied to the provided Neon database with PostGIS 3.6.4.
4. [x] **Establishing the frontend foundation** (`frontend-foundation`)
    - Depends on: `architecture-decisions`
    - Added a Fetch API client with Zod response validation, shared SmartPark types, and the Zustand navigation state machine with guarded driving/parking/walking transitions. Added two state tests; `npm test` and the production build pass. The original lockfile was out of sync, so `npm install` repaired it; npm reported 29 dependency advisories, not auto-fixed.
    - Main parking routes are publicly accessible and no longer require Firebase sign-in; optional login and registration pages remain available.
5. [x] **Implementing geographic data services** (`geographic-data-services`)
   - Depends on: `backend-database-foundation`
   - Added Photon geocoding and Overpass clients for node/way/relation parking queries, with process-local TTL caching, provider timeout/rate-limit errors, OSM-ID deduplication, and geometry normalization that preserves closed areas and relation holes instead of reducing every result to a point. Added offline tests for geocoding, queries, deduplication, area geometry, and rate-limit metadata; all 8 backend tests pass.
6. [x] **Implementing required DSA algorithms** (`dsa-engine`)
   - Depends on: `backend-database-foundation`
    - Added and tested the normalized Trie, adjacency-list graph builder with access/one-way handling, binary-heap Dijkstra with distances/predecessors/path reconstruction, heap-based vehicle-aware parking ranking, and stable merge sort for fee sorting. Added algorithm complexity documentation. Real road-network ingestion is tracked separately below.
7. [x] **Ingesting a real Karachi road network** (`road-network-ingestion`)
    - Depends on: `geographic-data-services`, `dsa-engine`
    - Build repeatable, bounded OSM road-data ingestion for Bahria University Karachi, Saddar, and Clifton. Persist real intersections and directed road edges, respect road access and one-way tags for driving, and provide pedestrian-accessible edges for walking; do not generate fake coordinates or use library shortest paths.
    - Progress: added a bounded Overpass query with caching, OSM node/way normalization, per-mode access and direction handling, an atomic repeatable import script, and a migration for mode-specific road access. Neon connectivity was verified, PostGIS 3.6.4 confirmed, and migrations `0001`–`0002` applied.
    - Imported the Karachi graph successfully: 13,472 nodes and 46,738 directed edges. Explicitly flush nodes before edges so database foreign keys are satisfied.
    - Provider refreshes may still fail when Overpass is unavailable; the successfully imported graph is persisted in the configured database.
8. [x] **Building destination search and autocomplete** (`destination-search`)
   - Depends on: `frontend-foundation`, `geographic-data-services`, `dsa-engine`
   - Added search/detail API endpoints with persistence, provider failure handling, Photon geocoding and caching, and Trie-backed suggestions. Added a debounced accessible frontend autocomplete with destination selection and details, optional location bias, and stale-request cancellation. Search is backed by geocoding, not a static list.
9. [x] **Building parking discovery and recommendations** (`parking-recommendations`)
    - Depends on: `geographic-data-services`, `dsa-engine`, `road-network-ingestion`
   - Add nearby/recommendation endpoints, known-compatibility filtering, road-distance ranking, and top-five results with clear destination/user distances, known fees, and verification/availability states.
   - Added nearby search and top-five recommendations that merge OSM discoveries with maintained records, filter explicit incompatibilities, and rank using Dijkstra over the imported road graph with a labeled straight-line fallback.
   - Results show destination and user distances, known fees, verification, availability, and data source. Overpass failures return an explicit provider error rather than fabricated results.
10. [x] **Building the interactive map experience** (`interactive-map`)
   - Depends on: `frontend-foundation`
   - Add a responsive Karachi-centered map with geolocation, destination/parking/route layers, selected-parking state, custom markers, and clear visual distinctions. Keep the destination visible but muted during driving.
   - Implemented on the existing Leaflet map: geolocation and Karachi fallback center, destination and parking markers, driving/walking route layers, route framing, muted destination during driving, and hiding only the selected parking marker after parking is confirmed.
11. [x] **Integrating driving and walking routes** (`routing-integration`)
    - Depends on: `backend-database-foundation`
    - Integrate OpenRouteService on the backend; return normalized route GeoJSON, distance, and duration for driving and walking. Handle credentials/provider errors and document bike-profile limitations.
    - Added `POST /api/routes/{mode}` with server-only OpenRouteService credentials, normalized GeoJSON, distance/duration, and explicit missing-key, provider, and rate-limit errors. Car and bike use `driving-car`; walking uses `foot-walking`. Bike-profile limitations are documented. All backend tests pass.
12. [x] **Implementing the drive-to-walk journey** (`navigation-workflow`)
    - Depends on: `destination-search`, `interactive-map`, `parking-recommendations`, `routing-integration`
    - Connect destination and vehicle selection, parking selection, driving, manual parking confirmation, walking, arrival, completion, and reset. On parking confirmation, hide only the active parking marker and driving route, retain parking coordinates, emphasize the destination, and switch to walking mode.
    - Connected destination and vehicle selection, recommendations, driving and walking routes, manual parking confirmation, arrival, cancellation, and reset. Parking confirmation preserves the selected coordinates while switching route and map state.
13. [x] **Building parking administration tools** (`parking-administration`)
    - Depends on: `backend-database-foundation`, `geographic-data-services`
    - Added protected parking CRUD with constant-time bearer-key comparison, disabled-by-default API behavior when no key is configured, and an admin UI that keeps the key only in page memory.
14. [x] **Revamping the SmartPark PWA experience** (`pwa-ux-revamp`)
    - Depends on: `navigation-workflow`, `parking-administration`
    - Delivered the responsive map-first journey, streamlined navigation, lazy-loaded pages, installable PWA manifest/icon, and offline app shell. Network-backed API and map data still require connectivity.
15. [x] **Verifying the complete SmartPark journey** (`integration-testing`)
    - Depends on: `dsa-engine`, `navigation-workflow`, `parking-administration`, `pwa-ux-revamp`
    - Added and ran focused frontend and backend coverage for navigation state, recommendations, admin authorization/CRUD, and road-network persistence. Latest checks: 9 frontend tests, 43 backend tests, and a production build pass.
16. [x] **Complete a terms-compliant Google Maps migration** (`google-maps-platform`)
    - Depends on: `interactive-map`, `destination-search`, `parking-recommendations`, `routing-integration`
    - Replace Leaflet/OpenStreetMap in views that show Google Places or Geocoding content; review route and road-distance layers for the same compatibility requirement.
    - Stop shared persistent storage and indexing of Google place names and addresses; follow Google’s data-retention and attribution rules.
    - Switched destination and nearby parking searches to Google Places (New), both visible maps to Google Maps JavaScript API, and route navigation to Google Routes. Removed the Leaflet dependency. Parking recommendations no longer query the OSM road graph; distance estimates are clearly labeled straight-line. Google place names and addresses remain transient; the older database detail endpoint serves only preexisting records.
    - The same user-provided demo key is configured locally for server and browser use. The browser key is public by design; configure website restrictions, billing, and quotas in Google Cloud before production.
    - Live Bahria University text search returned one result and nearby parking returned five results on 2026-11-20.

17. [x] **Re-verify the journey after the provider migration** (`post-provider-integration-testing`)
    - Depends on: `google-maps-platform`
    - Re-run destination search, nearby parking, recommendations, driving/walking routes, and the complete search-to-arrival flow against the migrated providers.
    - Update and run focused frontend/backend checks, then confirm local setup and production build.
    - Passing: 50 backend tests, 9 frontend tests, and production build. The live local API returned 200 for Bahria University search, top-five Google parking recommendations, and both driving and walking Google routes. The frontend navigation-state tests cover parking confirmation and arrival.

18. [ ] **Deploy the documented MVP** (`documentation-deployment`)
    - Depends on: `post-provider-integration-testing`
    - Deployment documentation and container/static-host configuration are complete.
    - Hosting target chosen: Netlify frontend and Render backend. Added `render.yaml` and documented required build-time and runtime settings.
    - Remaining: connect the repository to those hosting accounts, configure production database and provider keys, apply migrations, and verify the public journey.
