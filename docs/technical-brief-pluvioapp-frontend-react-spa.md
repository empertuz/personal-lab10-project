# Technical Brief: PluvioApp Phase 2 — Frontend (React SPA)

**Scope:** Build the first version of the frontend as a React SPA inside `frontend/` of the existing `pluvio-app-cl` repo. The app consumes the Phase 1 FastAPI backend (11 endpoints, already built and reviewed) and provides a map-centric interface for geographic station search and rainfall data visualization.

---

## 1. Task Title

**PluvioApp Phase 2 — Interactive Map Frontend (React + Vite + Mapbox + Recharts)**

---

## 2. Context

- **Current state:** A fully working FastAPI + SQLite backend exists with 11 REST API endpoints, 6,222 stations, ~40M rainfall records, 18 passing tests, and clean linting. There is no frontend — users can only interact via Swagger UI or raw HTTP calls.
- **Pain points:** No visual interface for geographic search, no way to explore stations on a map, no rainfall trend visualization. The backend is usable but not accessible to non-technical users.
- **Goal:** Deliver a responsive, map-centric SPA where users can select a location on Colombia's map (click or manual input), define a search radius, browse matching stations as cards or map markers, and drill into any station to see its metadata and a yearly rainfall trend chart.

---

## 3. Technical Requirements

- **Language and runtime:** TypeScript (strict mode), Node.js 20+.
- **Framework:** React 18+ with Vite as bundler/dev server. Single-page application — no SSR.
- **Styling:** Tailwind CSS 3+. No component libraries (MUI, Ant, etc.). Custom components styled with Tailwind utility classes.
- **Map:** Mapbox GL JS (`react-map-gl` wrapper). Token stored as `VITE_MAPBOX_TOKEN` environment variable. Map centered on Colombia on load (approx lat: 4.5, lon: -73.5, zoom: 5.5).
- **Charts:** Recharts for one trend chart (yearly rainfall totals as a bar or line chart).
- **HTTP client:** `fetch` API with a thin typed wrapper, or a lightweight client like `ky`. No Axios.
- **State management:** React built-in (`useState`, `useReducer`, `useContext`). No Redux, Zustand, or external state libraries for v1.
- **Routing:** None needed for v1 — single-page with view states (search → results → detail) managed via component state. If routing is added, use `react-router-dom` v6.

### Project Structure

```
frontend/
├── public/
├── src/
│   ├── api/              # Typed API client functions
│   ├── components/       # Reusable UI components
│   │   ├── map/          # Map-related components
│   │   ├── search/       # Search form components
│   │   ├── stations/     # Station cards, list, detail
│   │   └── charts/       # Rainfall trend chart
│   ├── types/            # TypeScript interfaces (mirroring backend models)
│   ├── hooks/            # Custom React hooks
│   ├── utils/            # Helpers (formatting, validation)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css         # Tailwind directives
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
└── vite.config.ts
```

### TypeScript Interfaces (mirroring backend Pydantic models)

```typescript
// Station types
interface StationSearchParams {
  lat: number;        // -4.0 to 13.5
  lon: number;        // -82.0 to -66.0
  radius_km: number;  // 0 to 500
  status?: string;
  category?: string;
  has_data?: boolean;
  include_summary?: boolean;
}

interface DataSummary {
  date_from: string | null;
  date_to: string | null;
  total_records: number;
}

interface StationResponse {
  id: string;
  name: string | null;
  category: string | null;
  status: string | null;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  department: string | null;
  municipality: string | null;
  distance_km: number;
  has_data: boolean;
  data_summary: DataSummary | null;
}

interface StationDetail extends Omit<StationResponse, 'distance_km'> {
  technology: string | null;
  installed_at: string | null;
  suspended_at: string | null;
  operational_area: string | null;
  hydro_area: string | null;
  hydro_zone: string | null;
  hydro_subzone: string | null;
  stream: string | null;
}

interface StationSearchResponse {
  center: { lat: number; lon: number };
  radius_km: number;
  count: number;
  stations: StationResponse[];
}

// Rainfall types
interface RainfallYearly {
  year: number;
  total_mm: number;
  avg_daily_mm: number;
  max_daily_mm: number;
  rainy_days: number;
  data_days: number;
}

interface YearlyResponse {
  station_id: string;
  count: number;
  data: RainfallYearly[];
}

interface RainfallStats {
  station_id: string;
  date_from: string | null;
  date_to: string | null;
  total_records: number;
  avg_mm: number | null;
  max_mm: number | null;
  min_mm: number | null;
  coverage_pct: number | null;
}

// Health
interface HealthResponse {
  status: string;
  tables: Record<string, number>;
}
```

### User Flow (detailed)

**State 1 — Landing / Search:**
- Full-screen Mapbox map centered on Colombia
- Floating search panel (top-left or centered overlay on mobile) with:
  - Lat/Lon input fields (numeric, pre-validated to Colombia bounds)
  - "Or click on the map" hint — clicking the map fills the lat/lon fields and drops a marker
  - Radius input (km, default suggestion: 50)
  - Search button
- On map click: place a marker at clicked coordinates, auto-fill lat/lon fields

**State 2 — Results:**
- Search radius drawn as a circle on the map
- Left panel (or bottom sheet on mobile) shows station cards:
  - Each card: station name, status badge (Activa/Suspendida), department, distance_km, has_data indicator
  - Cards sorted by distance (closest first)
- Map shows station markers within the radius (color-coded by status or has_data)
- Toggle between card list view and map-focused view
- Clicking a card highlights the corresponding map marker (and vice versa)

**State 3 — Station Detail:**
- Expands from card click or map marker click
- Shows: all station metadata fields, stats summary (date range, total records, avg/max/min rainfall, coverage %)
- One trend chart: yearly rainfall totals (bar chart via Recharts) from `GET /api/rainfall/{station_id}/yearly`
- Back button to return to results

### API Endpoints Used by Frontend

| Frontend Action | Endpoint | Method |
|----------------|----------|--------|
| Search stations | `/api/stations/search?lat=X&lon=Y&radius_km=Z&include_summary=true` | GET |
| Station detail | `/api/stations/{station_id}` | GET |
| Rainfall stats | `/api/rainfall/{station_id}/stats` | GET |
| Yearly rainfall (chart) | `/api/rainfall/{station_id}/yearly` | GET |
| Health check | `/api/health` | GET |

### Backend CORS

Already configured to allow `http://localhost:5173` (Vite's default dev port). No backend changes needed.

---

## 4. Constraints

- **Forbidden:** SSR frameworks (Next.js, Remix); CSS-in-JS (styled-components, Emotion); component libraries (MUI, Ant Design, Chakra); external state management libraries (Redux, Zustand, Jotai); Axios.
- **Required code standards:**
  - TypeScript strict mode (`"strict": true` in tsconfig)
  - ESLint with `@typescript-eslint` rules
  - Prettier for formatting
  - All API responses typed — no `any` types for API data
  - All components as functional components with hooks
- **Accessibility:** Semantic HTML (`<main>`, `<nav>`, `<section>`, `<button>`). Form inputs must have labels. Interactive elements must be keyboard-accessible. Color is not the only indicator of status (use text labels alongside color badges).
- **Performance:** Lazy-load the map component. Debounce map click events. Show loading spinners during API calls. Handle and display API errors gracefully (network errors, 404s, 422s).
- **Mobile responsive:** Breakpoints at `sm` (640px), `md` (768px), `lg` (1024px). On mobile: search panel stacks vertically above map; results appear as a bottom sheet or full-screen overlay; detail view is full-screen.
- **Environment variables:** Mapbox token as `VITE_MAPBOX_TOKEN`. API base URL as `VITE_API_BASE_URL` (default: `http://localhost:8000`).
- **No backend modifications:** The frontend must work with the existing backend API as-is. No new endpoints, no schema changes.
- **Consistent with existing repo:** The `frontend/` directory is self-contained with its own `package.json`, but the `.gitignore` at root should be updated to include `frontend/node_modules/` and `frontend/dist/`.

---

## 5. Definition of Done

- [ ] **Project setup:** `frontend/` directory exists with Vite + React + TypeScript scaffolding. `npm install && npm run dev` starts the dev server on port 5173 without errors.
- [ ] **TypeScript types:** All backend response models have corresponding TypeScript interfaces in `src/types/`. No `any` types used for API data.
- [ ] **API client:** Typed API functions exist for all 5 endpoints used (station search, station detail, rainfall stats, rainfall yearly, health). Each function returns typed data and handles errors.
- [ ] **Map renders:** Mapbox map loads on the landing page, centered on Colombia. Map click drops a marker and populates lat/lon fields.
- [ ] **Search works:** User can input lat/lon (manually or via map click) + radius and trigger a search. Results come back from the backend and display correctly.
- [ ] **Station cards:** Search results render as cards showing name, status, department, distance, has_data. Sorted by distance.
- [ ] **Map markers:** Search results render as markers on the map with the search radius circle visible. Clicking a marker selects that station.
- [ ] **Station detail:** Clicking a card or marker shows station detail with all metadata fields and stats summary (date range, record count, avg/max/min, coverage).
- [ ] **Trend chart:** Station detail includes a yearly rainfall bar chart (Recharts) showing `total_mm` per year from the `/yearly` endpoint.
- [ ] **Loading and error states:** All API calls show a loading indicator while pending. API errors (network, 404, 422) display user-friendly messages — no silent failures.
- [ ] **Mobile responsive:** Layout adapts at `sm`/`md`/`lg` breakpoints. Search, results, and detail views are usable on a 375px-wide screen.
- [ ] **Accessibility:** All form inputs have labels. Buttons are keyboard-accessible. Status indicators use text + color (not color alone).
- [ ] **Lint/format:** `npm run lint` (ESLint) and `npm run format:check` (Prettier) pass with zero errors.
- [ ] **Build:** `npm run build` produces a production bundle in `frontend/dist/` with no TypeScript or build errors.
- [ ] **Environment:** `.env.example` in `frontend/` documents `VITE_MAPBOX_TOKEN` and `VITE_API_BASE_URL`. App works with only these two env vars set.
- [ ] **Gitignore updated:** Root `.gitignore` includes `frontend/node_modules/` and `frontend/dist/`.

---

## Quality Checklist (Verified)

- [x] All 5 sections present and non-vague
- [x] DoD fully verifiable (pass/fail criteria)
- [x] Constraints consistent with requirements (Tailwind, not MUI; Recharts, not D3; fetch, not Axios)
- [x] Brief consistent with existing codebase (TS interfaces match Pydantic models exactly; CORS already allows port 5173; no backend changes required)
