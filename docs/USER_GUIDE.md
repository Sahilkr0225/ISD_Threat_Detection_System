# User Guide — Security Operations Console

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
3. Open `http://localhost:5173` in your browser.

## Administrator Workflow
1. **Security Overview (`/`):** Review monitored employees, daily activity records, open alerts, Critical alerts awaiting review vs. total Critical alerts, and active/completed investigations.
2. **Employee Monitoring (`/employees`):** Search by Employee ID or filter by department; click an employee to inspect their recorded activity period, highest investigation priority, and activity timeline.
3. **Suspicious Activity (`/alerts`):** Filter by Investigation Priority, Status, Employee ID, or From/To Date; read each alert's plain-language activity summary and click **Review Alert**.
4. **Alert Investigation Workspace (`/alerts/:alertId`):**
   - Read **Why This Alert Requires Attention** and the **Unusual Activity Detected** cards.
   - Follow **Recommended Investigation Steps** (external checks to verify authorization/logs).
   - Click **Start Investigation**, add an analyst note, and **Complete Investigation** or **Dismiss Alert** (with confirmation).
   - Expand **Advanced Technical Details** at the bottom if you need raw anomaly scores, validation percentiles, or historical z-deviations.
5. **Advanced & Technical (`AI Model Performance` `/model`, `Dataset & System` `/system`):** Inspect Phase 2 research evaluation metrics, separate ROC-AUC/AP ablation charts, threshold comparisons (research-only), and CERT r4.2 provenance.
