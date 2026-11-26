# Frontend Architecture

**Stack:** React 18, TypeScript (strict mode), Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), React Router DOM v7, Axios, Recharts, Lucide React.

## Directory Layout
```text
frontend/
  src/
    api/          # Centralized Axios client (withCredentials + X-CSRF-Token) & typed services (auth, users, audit, alerts, dashboard, employees, model)
    components/
      auth/       # ProtectedRoute (authentication & allowedRoles RBAC guard)
      common/     # KpiCard, Badges, RiskBar, Pagination, LoadingSkeleton, EmptyState, ErrorState, ConfirmDialog, ToastContext, ErrorBoundary
      layout/     # AppShell (role-filtered sidebar groups, user/role badge, logout, API health indicator)
    context/      # AuthContext (session hydration via /auth/me, login/logout, hasRole helper)
    pages/        # Lazy-loaded views: Login, AccessDenied, Overview, Employees, EmployeeDetail, AlertCenter, AlertDetail, Investigations, ModelEvaluation, DatasetSystem, UserManagement, AuditLogs, NotFound
    types/        # Strict TypeScript interfaces matching docs/API_CONTRACT.md
    utils/        # Number, percentile, and timezone-safe date formatters
```

## API, Proxy & Cookie Configuration
- `frontend/vite.config.ts` proxies `/api` requests in development to `http://127.0.0.1:8000` so `isd_session` and `isd_csrf` cookies remain same-origin on `http://localhost:5173`.
- `frontend/src/api/client.ts` defaults `API_BASE_URL` to `/api/v1` (overridable via `VITE_API_BASE_URL`), sets `withCredentials: true`, attaches `X-CSRF-Token` from the `isd_csrf` cookie on `POST`/`PUT`/`PATCH`/`DELETE` requests, and triggers session reset on `401`.

## Route-Level RBAC & Performance
- All route components are lazy-loaded via `React.lazy` + `Suspense`.
- **Role-Based Route Access:**
  - `ADMINISTRATOR`, `SECURITY_ANALYST`, `AUDITOR`: `/`, `/employees`, `/employees/:employeeId`, `/alerts`, `/alerts/:alertId`, `/investigations` (with `AUDITOR` shown read-only notice on `AlertDetail`).
  - `ADMINISTRATOR`, `AUDITOR`: `/model`, `/system`, `/audit-logs`.
  - `ADMINISTRATOR` only: `/users`.
- All large tables (`Employees`, `EmployeeDetail`, `AlertCenter`, `Investigations`, `AuditLogs`) use server-side pagination (`page_size=25`).
