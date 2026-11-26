# Frontend Testing & Verification

## Build & TypeScript Verification
```powershell
cd frontend
npm install
npm run build
```
- `tsc -b` runs with strict TypeScript checking (`strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`).
- `vite build` produces optimized route-split chunks in `frontend/dist/`.
- **Latest Verified Result:** `tsc -b && vite build` passed cleanly (including Phase 6 `Login`, `AccessDenied`, `UserManagement`, `AuditLogs`, `ProtectedRoute`, and `AuthContext`).

## Integration & RBAC Verification Scope
- **Authenticated API & Proxy Flow:** Verified `/api` Vite proxy configuration (`frontend/vite.config.ts`) and cookie/CSRF handling (`withCredentials: true`, `X-CSRF-Token` interceptor in `frontend/src/api/client.ts`).
- **Role-Specific Views:**
  - `ADMINISTRATOR`: Access to all 3 sidebar groups (`Security Operations`, `Advanced & Technical`, `Governance & Access`), User Management (`/users`), Audit Logs (`/audit-logs`), and investigation actions.
  - `SECURITY_ANALYST`: Access to `Security Operations` and investigation status transitions; restricted from `/model`, `/system`, `/users`, and `/audit-logs`.
  - `AUDITOR`: Read-only access to `Security Operations`, `Advanced & Technical`, and `Audit Logs`; investigation mutation controls replaced with read-only notice on `AlertDetail`.
- **Core Operational Pages (Verified):** Security Overview KPIs & charts, Employee Monitoring & detail timeline, Suspicious Activity filtering/pagination, Alert Detail causal explanations & investigation history (with actor attribution / `"Legacy / Unauthenticated"` fallback), Model Evaluation ablation & threshold selector, and Dataset & System provenance.
