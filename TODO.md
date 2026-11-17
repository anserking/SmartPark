# SmartPark project todos

These are the project tasks tracked for completing the MVP. The repository
audit, architecture decisions, backend/database foundation, and geographic data
services, DSA algorithms, and frontend foundation are complete; remaining tasks
are pending or in progress. Dependencies
are listed so the work can be sequenced without blocking independent tasks.

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
   - Added the FastAPI service, environment-based settings, database-aware health endpoint, SQLAlchemy 2 models, PostGIS/Alembic initial schema, local setup instructions, and Python ignores. Verified with 2 passing tests, Python compilation, and offline SQL migration generation. Applying the migration against a live PostGIS database remains unverified because none is configured here.
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
7. [ ] **Ingesting a real Karachi road network** (`road-network-ingestion`)
    - Depends on: `geographic-data-services`, `dsa-engine`
    - Build repeatable, bounded OSM road-data ingestion for Bahria University Karachi, Saddar, and Clifton. Persist real intersections and directed road edges, respect road access and one-way tags for driving, and provide pedestrian-accessible edges for walking; do not generate fake coordinates or use library shortest paths.
8. [ ] **Building destination search and autocomplete** (`destination-search`)
   - Depends on: `frontend-foundation`, `geographic-data-services`, `dsa-engine`
   - Build the search API and debounced frontend autocomplete, result selection, destination details, geocoding/cache, and Trie-backed suggestions. Search must not rely only on a static list.
9. [ ] **Building parking discovery and recommendations** (`parking-recommendations`)
    - Depends on: `geographic-data-services`, `dsa-engine`, `road-network-ingestion`
   - Add nearby/recommendation endpoints, known-compatibility filtering, road-distance ranking, and top-five results with clear destination/user distances, known fees, and verification/availability states.
10. [ ] **Building the interactive map experience** (`interactive-map`)
   - Depends on: `frontend-foundation`
   - Add a responsive Karachi-centered map with geolocation, destination/parking/route layers, selected-parking state, custom markers, and clear visual distinctions. Keep the destination visible but muted during driving.
11. [ ] **Integrating driving and walking routes** (`routing-integration`)
    - Depends on: `backend-database-foundation`
    - Integrate OpenRouteService on the backend; return normalized route GeoJSON, distance, and duration for driving and walking. Handle credentials/provider errors and document bike-profile limitations.
12. [ ] **Implementing the drive-to-walk journey** (`navigation-workflow`)
    - Depends on: `destination-search`, `interactive-map`, `parking-recommendations`, `routing-integration`
    - Connect destination and vehicle selection, parking selection, driving, manual parking confirmation, walking, arrival, completion, and reset. On parking confirmation, hide only the active parking marker and driving route, retain parking coordinates, emphasize the destination, and switch to walking mode.
13. [ ] **Building parking administration tools** (`parking-administration`)
    - Depends on: `backend-database-foundation`, `geographic-data-services`
    - Add a minimal protected interface for listing, creating, editing, verifying, marking unavailable, correcting, and deleting parking records.
14. [ ] **Verifying the complete SmartPark journey** (`integration-testing`)
    - Depends on: `dsa-engine`, `navigation-workflow`, `parking-administration`
    - Test search/geodata, DSA edge cases, recommendations, routes, navigation transitions, and admin CRUD; exercise and fix the complete search-to-arrival journey.
15. [ ] **Documenting and deploying the MVP** (`documentation-deployment`)
    - Depends on: `integration-testing`
    - Update setup, architecture, database, algorithms, attribution, environment-variable, and limitation documentation. Deploy the frontend/backend/database and verify the public demo without exposing API keys.
