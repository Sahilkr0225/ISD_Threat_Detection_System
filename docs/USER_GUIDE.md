# User Guide — Security Operations Console

## First-Time Administrator Setup
Before starting the application for the first time, provision an initial `ADMINISTRATOR` account interactively (passwords must be 12–128 characters):
```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_admin.py
```

## Starting the Application
1. **Start the FastAPI Backend** (from `D:\ISD_Threat_Detection_System`):
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start the React Frontend** (in a second terminal):
   ```powershell
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser and sign in.

## System Roles (RBAC)
*(Note: Monitored employees in the CERT r4.2 dataset are subjects of analysis and do not log into the SOC portal.)*
- **`ADMINISTRATOR`:** Full operational, model evaluation, user provisioning (`/users`), and audit log (`/audit-logs`) access.
- **`SECURITY_ANALYST`:** Security monitoring and alert investigation triage (`OPEN` -> `UNDER_REVIEW` -> `RESOLVED` / `DISMISSED`). No access to model evaluation, user management, or audit logs.
- **`AUDITOR`:** Read-only oversight across security operations, AI Model Performance (`/model`), Dataset & System (`/system`), and Security Audit Logs (`/audit-logs`). Cannot mutate alert statuses or manage users.

## Operational Workflow
1. **Security Overview (`/`):** Review monitored employees, daily activity records, open alerts, Critical alerts awaiting review vs. total Critical alerts, active/completed investigations, and recent investigation history with actor attribution.
2. **Employee Monitoring (`/employees`):** Search by Employee ID or filter by department; click an employee to inspect their recorded activity period, highest investigation priority, and activity timeline.
3. **Suspicious Activity (`/alerts`):** Filter by Investigation Priority, Status, Employee ID, or From/To Date; read each alert's plain-language activity summary and click **Review Alert**.
4. **Alert Investigation Workspace (`/alerts/:alertId`):**
   - Read **Why This Alert Requires Attention** and the **Unusual Activity Detected** cards.
   - Follow **Recommended Investigation Steps** (external checks to verify authorization/logs).
   - For `ADMINISTRATOR` and `SECURITY_ANALYST`: click **Start Investigation**, add an analyst note, and **Complete Investigation** or **Dismiss Alert** (with confirmation).
   - Expand **Advanced Technical Details** at the bottom if you need raw anomaly scores, validation percentiles, or historical z-deviations.
5. **Governance & Access (`/users`, `/audit-logs`):** Administrators can create accounts, assign roles, reset passwords, and activate/deactivate users; Administrators and Auditors can filter and inspect immutable security audit logs.
6. **Advanced & Technical (`/model`, `/system`):** Administrators and Auditors can inspect Phase 2 research evaluation metrics, separate ROC-AUC/AP ablation charts, threshold comparisons (research-only), and CERT r4.2 provenance.
