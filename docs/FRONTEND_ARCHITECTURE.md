# Frontend Architecture

**Stack:** React 18, TypeScript (strict mode), Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), React Router DOM v7, Axios, Recharts, Lucide React.

## Directory Layout
```text
frontend/
  src/
    api/          # Centralized Axios client & typed endpoint services
    components/
      common/     # KpiCard, Badges, RiskBar, Pagination, LoadingSkeleton, EmptyState, ErrorState, ConfirmDialog, ToastContext, ErrorBoundary
      layout/     # AppShell (collapsible dark-navy sidebar, breadcrumbs, API & dataset indicators)
    pages/        # Route-level lazy-loaded views (Overview, Employees, EmployeeDetail, AlertCenter, AlertDetail, Investigations, ModelEvaluation, DatasetSystem, NotFound)
    types/        # Strict TypeScript interfaces matching docs/API_CONTRACT.md
    utils/        # Number, percentile, and timezone-safe date formatters
```

## API & CORS Configuration
- `frontend/src/api/client.ts` reads `VITE_API_BASE_URL` (default `http://127.0.0.1:8000/api/v1`) with a `15,000ms` timeout and `AbortController` support.
- The FastAPI backend explicitly allows `http://localhost:5173` via `CORS_ORIGINS`.

## Route-Level Code Splitting & Performance
- All 9 route components are lazy-loaded via `React.lazy` + `Suspense`.
- All large tables (`Employees`, `EmployeeDetail`, `AlertCenter`, `Investigations`) use server-side pagination (`page_size=25`).

