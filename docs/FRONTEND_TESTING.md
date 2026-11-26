# Frontend Testing & Verification

## Build & TypeScript Verification
```powershell
cd frontend
npm install
npm run build
```
- `tsc -b` runs with strict TypeScript checking (`strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`).
- `vite build` produces optimized route-split chunks in `frontend/dist/`.

## End-to-End Integration Verification
Verified against the live FastAPI backend (`http://127.0.0.1:8000`) and Vite dev server (`http://localhost:5173`):
1. Security Overview KPIs, daily anomaly trend chart, priority/status distribution charts, and Critical queue.
2. Employee Intelligence search, department filter, server-side pagination, and Employee Detail timeline.
3. Alert Center filtering (`priority`, `status`, `employee_id`, date range, sorting, pagination).
4. Investigation Workspace: Alert detail, causal explanations, `OPEN -> UNDER_REVIEW -> RESOLVED` transition with analyst note, confirmation dialog, and persisted `investigation_history`.
5. Model Evaluation: 6-feature vs 20-feature ablation and interactive 4-threshold confusion matrix selector.
6. Dataset & System provenance and limitations page.

