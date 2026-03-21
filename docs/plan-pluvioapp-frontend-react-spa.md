# Implementation Plan: PluvioApp Phase 2 — Interactive Map Frontend

**Based on:** `docs/technical-brief-pluvioapp-frontend-react-spa.md`
**Status:** Approved — ready for implementation

---

## 1. Summary

We are building a React SPA inside `frontend/` of the existing PluvioApp repo. The app renders a full-screen Mapbox map of Colombia, lets users select a location (click or type coordinates) and search radius, queries the existing FastAPI backend for nearby stations, displays results as cards and map markers, and allows drilling into any station to see its metadata and a yearly rainfall trend chart. No backend changes are needed — the frontend consumes the existing API as-is.

---

## 2. Step-by-Step Implementation Logic

**Step 1 — Project scaffolding and tooling**
What: Initialize the Vite + React + TypeScript project inside `frontend/` using `npm create vite@latest`. Install all dependencies: `react-map-gl`, `mapbox-gl`, `recharts`, `tailwindcss`, `postcss`, `autoprefixer`, `@turf/circle`. Configure Tailwind (`tailwind.config.js`, `postcss.config.js`, Tailwind directives in `index.css`). Configure TypeScript strict mode in `tsconfig.json`. Set up ESLint with `@typescript-eslint` and Prettier. Add `package.json` scripts: `dev`, `build`, `lint`, `format`, `format:check`. Create `frontend/.env.example` with `VITE_MAPBOX_TOKEN` and `VITE_API_BASE_URL`. Update root `.gitignore` to include `frontend/node_modules/` and `frontend/dist/`.
Why first: Every subsequent step depends on the build tooling, type checking, and dev server being operational.
Depends on: nothing

**Step 2 — TypeScript type definitions**
What: Create `src/types/station.ts` and `src/types/rainfall.ts` with exported interfaces that mirror the backend Pydantic models exactly. Interfaces: `StationSearchParams`, `DataSummary`, `StationResponse`, `StationDetail`, `StationSearchResponse`, `RainfallYearly`, `YearlyResponse`, `RainfallStats`, `HealthResponse`. Also create `src/types/index.ts` as a barrel export.
Why second: The API client, components, and hooks all depend on these types. Establishing them early catches contract mismatches before any UI work.
Depends on: Step 1

**Step 3 — API client layer**
What: Create `src/api/client.ts` with a thin typed wrapper around `fetch`. The wrapper handles: base URL from `VITE_API_BASE_URL`, JSON parsing, error handling (throws typed errors for network failures, 404, 422, etc.). Then create `src/api/stations.ts` with functions `searchStations(params)`, `getStation(stationId)` and `src/api/rainfall.ts` with functions `getYearlyRainfall(stationId)`, `getRainfallStats(stationId)`, and `src/api/health.ts` with `getHealth()`. Each function takes typed params and returns typed responses. Create `src/api/index.ts` barrel export.
Why third: Components need to call the API. Having a typed client before building UI means components can focus on rendering, not HTTP plumbing.
Depends on: Step 2

**Step 4 — Custom hooks**
What: Create `src/hooks/useStationSearch.ts` — manages search state (loading, error, results of type `StationSearchResponse | null`), exposes a `search(params)` function that calls the API client. Create `src/hooks/useStationDetail.ts` — given a `stationId`, fetches station detail, stats, and yearly rainfall in parallel; manages loading/error state for all three. These hooks encapsulate all async logic so components remain purely presentational.
Why here: Hooks sit between the API layer and components. Building them before UI components keeps the components thin.
Depends on: Step 3

**Step 5 — App shell and layout**
What: Implement `src/App.tsx` as the top-level component. It manages the app-level view state: `"search"`, `"results"`, or `"detail"`. It holds the search results and selected station ID in state. It renders a full-screen layout with the map always visible in the background and panels overlaid on top. Define the responsive layout breakpoints: on desktop (lg+), panels sit on the left side over the map; on mobile, panels stack vertically or slide up as bottom sheets. Use a simple state machine — no router.
Why here: The shell defines how all other components are composed. Building it before the individual components ensures the layout contract is clear.
Depends on: Step 1

**Step 6 — Map component**
What: Create `src/components/map/StationMap.tsx` using `react-map-gl`. The map loads with the Mapbox token from env, centered on Colombia (lat 4.5, lon -73.5, zoom 5.5). Map style: `mapbox://styles/mapbox/outdoors-v12`. It accepts props: `onMapClick(lat, lon)` callback, optional `searchCenter` and `searchRadius` (to draw a circle layer using `@turf/circle` to generate a GeoJSON polygon rendered as a Mapbox `fill` layer), optional `stations` array (to render markers), optional `selectedStationId` (to highlight one marker), and `onMarkerClick(stationId)` callback. The map click handler is debounced. Station markers are color-coded: green for `has_data=true` + `status=Activa`, gray for others. Clicking a marker shows a small popup with station name, status, distance, and a "View details" button. Import `mapbox-gl/dist/mapbox-gl.css` in the component. Lazy-load this component using `React.lazy` and `Suspense`.
Why here: The map is the visual backbone. Building it before search and results allows visual testing of the core experience.
Depends on: Step 5

**Step 7 — Search panel component**
What: Create `src/components/search/SearchPanel.tsx`. A floating panel (absolute-positioned over the map on desktop, stacked on mobile) containing: labeled lat/lon input fields (type `number`, step `0.01`, validated to Colombia bounds -4 to 13.5 lat, -82 to -66 lon), a labeled radius input (type `number`, default 50, min 1, max 500), and a search button. The panel receives `lat`, `lon` props (which update when the user clicks the map) and exposes an `onSearch(params)` callback. Inputs are controlled components. The search button is disabled while lat/lon are empty or out of bounds. Show a "Click on the map to select a location" hint when lat/lon are empty. Add a location marker pin on the map (via parent state) when lat/lon are filled.
Why here: This is the entry point to the user flow. It feeds the search hook.
Depends on: Steps 5, 6

**Step 8 — Station card and list components**
What: Create `src/components/stations/StationCard.tsx` — a card component showing: station name (or ID if name is null), status badge (colored pill with text: "Activa" green, "Suspendida" red, etc.), department, distance in km (formatted to 1 decimal), and a "has data" indicator (text label, not just color). The card is clickable (triggers station detail). Create `src/components/stations/StationList.tsx` — a scrollable list of `StationCard` components. Shows the result count at the top. Cards are already sorted by distance from the API. The list panel sits on the left side on desktop, bottom sheet on mobile. Include a "Back to search" button to return to the search state.
Why here: Once search works, results need to render. Cards are the primary way users browse stations.
Depends on: Steps 4, 5

**Step 9 — Station detail component**
What: Create `src/components/stations/StationDetail.tsx`. Full panel (left side on desktop, full-screen on mobile) showing: station name, ID, status badge, category, technology, altitude, lat/lon, department, municipality, operational area, hydro area/zone/subzone, stream, installed/suspended dates. Below the metadata: a stats summary section showing date range, total records, avg/max/min rainfall, coverage percentage. Below stats: the trend chart (Step 10). A "Back to results" button at the top. Loading spinner while data is being fetched. Error message if the station or stats fetch fails. Uses `useStationDetail` hook.
Why here: This is the deepest view in the flow. It requires the detail hook, which fetches station detail + stats + yearly data in parallel.
Depends on: Steps 4, 5

**Step 10 — Rainfall trend chart**
What: Create `src/components/charts/YearlyRainfallChart.tsx`. Uses Recharts to render a bar chart of yearly rainfall totals (`total_mm` per year). X-axis: years. Y-axis: total rainfall in mm. Tooltip showing year, total_mm, rainy_days, data_days on hover. Responsive container that adapts to parent width. The component receives `data: RainfallYearly[]` as a prop — it does not fetch data itself. Show a "No data available" message if the array is empty.
Why here: The chart is embedded inside the station detail view. Building it as a standalone component keeps it testable and reusable.
Depends on: Step 2

**Step 11 — Loading, error, and empty states**
What: Create `src/components/common/LoadingSpinner.tsx` (centered spinner with optional message), `src/components/common/ErrorMessage.tsx` (styled error with retry button), and `src/components/common/EmptyState.tsx` (friendly message for no results). Wire these into: the search flow (loading while API call is in progress), the results view (empty state if zero stations found), and the detail view (loading while fetching detail/stats/yearly). Map errors to user-friendly messages: network error → "Could not connect to the server", 422 → "Invalid search parameters", 404 → "Station not found".
Why here: All views are built by now — this step polishes the experience.
Depends on: Steps 7, 8, 9, 10

**Step 12 — Responsive design and mobile polish**
What: Review all components for responsive behavior. Ensure: search panel is full-width and stacked above the map on mobile (below `md`); results panel is a bottom sheet or full-width overlay on mobile; detail view is full-screen on mobile with a sticky back button; map is visible behind panels on desktop but takes full screen when panels are collapsed on mobile. Test at 375px width (iPhone SE). Add toggle button on mobile to switch between list view and map-focused view.
Why here: All components exist — this step is a layout pass, not new functionality.
Depends on: Steps 7, 8, 9

**Step 13 — Lint, format, and build verification**
What: Run `npm run lint` and fix all ESLint errors. Run `npm run format` to format all files with Prettier. Run `npm run build` and verify the production bundle compiles with no TypeScript errors. Verify `frontend/dist/` is generated. Test that the dev server starts cleanly.
Why last: Final quality gate before declaring the implementation complete.
Depends on: All prior steps

---

## 3. Files to Create

| File | Purpose | Key contents |
|------|---------|--------------|
| `frontend/package.json` | Dependencies and scripts | react, react-dom, react-map-gl, mapbox-gl, recharts, @turf/circle, tailwindcss, typescript, eslint, prettier |
| `frontend/vite.config.ts` | Vite configuration | React plugin, dev server port 5173 |
| `frontend/tsconfig.json` | TypeScript config | strict: true, JSX, path aliases |
| `frontend/tailwind.config.js` | Tailwind config | Content paths, theme extensions |
| `frontend/postcss.config.js` | PostCSS config | Tailwind and autoprefixer plugins |
| `frontend/.env.example` | Env var documentation | VITE_MAPBOX_TOKEN, VITE_API_BASE_URL |
| `frontend/.eslintrc.cjs` | ESLint config | @typescript-eslint rules, React hooks rules |
| `frontend/.prettierrc` | Prettier config | Formatting rules |
| `frontend/index.html` | Entry HTML | Root div, Vite script tag |
| `frontend/src/main.tsx` | React entry point | ReactDOM.createRoot, App mount |
| `frontend/src/App.tsx` | App shell | View state machine, layout, panel composition |
| `frontend/src/index.css` | Global styles | Tailwind directives (@tailwind base/components/utilities) |
| `frontend/src/types/station.ts` | Station TS interfaces | StationSearchParams, StationResponse, StationDetail, StationSearchResponse, DataSummary |
| `frontend/src/types/rainfall.ts` | Rainfall TS interfaces | RainfallYearly, YearlyResponse, RainfallStats, HealthResponse |
| `frontend/src/types/index.ts` | Barrel export | Re-exports all types |
| `frontend/src/api/client.ts` | Fetch wrapper | Base URL, JSON parsing, error handling |
| `frontend/src/api/stations.ts` | Station API functions | searchStations(), getStation() |
| `frontend/src/api/rainfall.ts` | Rainfall API functions | getYearlyRainfall(), getRainfallStats() |
| `frontend/src/api/health.ts` | Health API function | getHealth() |
| `frontend/src/api/index.ts` | Barrel export | Re-exports all API functions |
| `frontend/src/hooks/useStationSearch.ts` | Search hook | Loading/error/results state, search() trigger |
| `frontend/src/hooks/useStationDetail.ts` | Detail hook | Parallel fetch of detail + stats + yearly, loading/error state |
| `frontend/src/components/map/StationMap.tsx` | Mapbox map | Map rendering, click handler, markers, popup, radius circle layer |
| `frontend/src/components/search/SearchPanel.tsx` | Search form | Lat/lon/radius inputs, search button, validation |
| `frontend/src/components/stations/StationCard.tsx` | Station card | Name, status badge, department, distance, has_data |
| `frontend/src/components/stations/StationList.tsx` | Results list | Scrollable card list, result count, back button |
| `frontend/src/components/stations/StationDetail.tsx` | Detail view | Full metadata, stats summary, chart embed |
| `frontend/src/components/charts/YearlyRainfallChart.tsx` | Trend chart | Recharts bar chart, responsive, tooltip |
| `frontend/src/components/common/LoadingSpinner.tsx` | Loading indicator | Centered spinner with optional text |
| `frontend/src/components/common/ErrorMessage.tsx` | Error display | User-friendly message, retry button |
| `frontend/src/components/common/EmptyState.tsx` | Empty results | Friendly no-results message |
| `frontend/src/utils/format.ts` | Formatting helpers | Number formatting, date formatting, distance display |
| `frontend/src/utils/validation.ts` | Validation helpers | Colombia bounds check, radius bounds check |
| `frontend/public/` | Static assets | (empty or favicon) |

---

## 4. Files to Modify

| File | What changes | Risk |
|------|-------------|------|
| `.gitignore` (root) | Add `frontend/node_modules/` and `frontend/dist/` | Low — additive only, no existing lines changed |

---

## 5. Risks and Unknowns

**Risk 1 — Mapbox GL CSS import**
What: `mapbox-gl` requires its CSS to be imported for the map to render correctly. Vite handles CSS imports but the exact import path (`mapbox-gl/dist/mapbox-gl.css`) can vary across versions.
Why it matters: Map will render broken or invisible without it.
Resolution: Import the CSS in `main.tsx` or the map component. Test immediately after Step 6.

**Risk 2 — react-map-gl version compatibility**
What: `react-map-gl` v7 has breaking changes from v6 (different component API, different props). The `Map` component props and event handlers differ significantly.
Why it matters: Tutorials and examples may reference the wrong version.
Resolution: Use `react-map-gl` v7+ exclusively. Reference v7 docs only. Key difference: `Map` component uses `mapboxAccessToken` prop, not `mapStyle` object.

**Risk 3 — Map circle layer for search radius**
What: Drawing a geographic circle on a Mapbox map requires a GeoJSON polygon (approximated with 64+ points). A pixel-based circle won't scale correctly at different zoom levels.
Why it matters: Visual mismatch between the circle on the map and the actual search area.
Resolution: Use `@turf/circle` to generate a GeoJSON polygon from center + radius_km, then render it as a Mapbox `fill` + `line` layer.

**Risk 4 — Stations with null lat/lon**
What: The backend has orphan stations with `latitude=null, longitude=null`. These won't appear in search results (the backend excludes them), but `StationResponse` types allow null lat/lon.
Why it matters: If the frontend tries to place a marker at null coordinates, it will crash.
Resolution: Filter out stations with null lat/lon before rendering markers. This should not happen in search results but is a defensive measure.

**Risk 5 — Large result sets on wide radius**
What: A 500km radius search could return hundreds of stations. Rendering 500+ individual Mapbox markers as React components can cause performance issues.
Why it matters: Map interaction becomes sluggish.
Resolution: For v1, accept this since typical searches are 50-100km and return tens of stations. If performance issues arise, switch to a Mapbox `symbol` layer with GeoJSON source (renders natively in WebGL, no React overhead).

---

## 6. Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Search radius circle rendering | `@turf/circle` | Single-purpose package (~15KB), no transitive dependencies, generates correct geographic circles |
| Map style | `mapbox://styles/mapbox/outdoors-v12` | Shows topography and water features relevant to pluviometric/hydrology context |
| Marker click behavior | Popup first, then "View details" button | Less jarring than immediately switching views; lets user preview before committing |

---

## 7. Rollback and Safety Notes

This is greenfield — all work is in a new `frontend/` directory. The only modification to existing files is adding two lines to root `.gitignore`.

**Prerequisites before starting:**
- Node.js 20+ and npm installed
- Mapbox access token available
- Backend running (`uvicorn app.main:app`) with ingested data on `localhost:8000`

**The `frontend/` directory can be deleted entirely to roll back.** No backend code is touched.

---

## 8. Test Plan Preview

The brief does not include automated frontend tests in the DoD — the quality gates are lint, format, and build. Manual verification steps for each DoD item:

| DoD Item | Verification method |
|----------|-------------------|
| Project setup | `cd frontend && npm install && npm run dev` — dev server starts on 5173 |
| TypeScript types | `npm run build` passes — no `any` in API-related code (grep check) |
| API client | Start backend + frontend, trigger search, verify network tab shows correct API calls and typed responses |
| Map renders | Open app — Mapbox map loads centered on Colombia; click map — marker appears, lat/lon fields populate |
| Search works | Enter coordinates + radius, click search — results appear from backend |
| Station cards | Verify cards show name, status badge, department, distance, has_data; sorted by distance |
| Map markers | After search, markers visible on map at station locations; radius circle visible |
| Station detail | Click card or marker popup "View details" — detail panel shows all metadata + stats |
| Trend chart | Detail view shows bar chart with yearly totals; tooltip on hover |
| Loading/error states | Disconnect backend — error message appears; reconnect — loading spinner during search |
| Mobile responsive | Chrome DevTools at 375px — all views render correctly, no horizontal scroll |
| Accessibility | Tab through form — all inputs focusable; status badges have text labels |
| Lint/format | `npm run lint && npm run format:check` — zero errors |
| Build | `npm run build` — `frontend/dist/` generated, no errors |
| Environment | `.env.example` present with both vars documented |
| Gitignore | Root `.gitignore` includes frontend entries |

---

## 9. Expected Results

**Externally observable behavior when complete:**
- `cd frontend && npm install && npm run dev` starts on `localhost:5173`
- Full-screen map of Colombia loads (outdoors style with terrain and rivers)
- User clicks map → marker appears, lat/lon fields fill
- User enters radius (50km) and clicks Search → station cards appear, markers on map, circle overlay
- User clicks a map marker → popup with station name, status, distance, "View details" button
- User clicks "View details" or a station card → detail panel with metadata, stats, and yearly rainfall bar chart
- User clicks "Back" → returns to results
- Works on mobile (375px) — panels stack, map still visible
- `npm run build` produces `frontend/dist/` with no errors
- `npm run lint && npm run format:check` pass clean

**DoD coverage:**

| DoD Item | Covered by |
|----------|-----------|
| Project setup | Step 1 |
| TypeScript types | Step 2 |
| API client | Step 3 |
| Map renders | Step 6 |
| Search works | Steps 4, 7 |
| Station cards | Step 8 |
| Map markers | Step 6 |
| Station detail | Step 9 |
| Trend chart | Step 10 |
| Loading and error states | Step 11 |
| Mobile responsive | Step 12 |
| Accessibility | Steps 7, 8, 9 (throughout) |
| Lint/format | Step 13 |
| Build | Step 13 |
| Environment | Step 1 |
| Gitignore updated | Step 1 |
