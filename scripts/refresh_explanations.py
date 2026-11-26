"""Idempotent refresh of alert_explanations wording without touching alerts or history."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import DATABASE_PATH, METRICS_DIR
from backend.app.explainability.explainer import build_direction_aware_text


def refresh_explanations_in_db(db_path: Path) -> Dict[str, int]:
    """Update only evidence_description and investigation_recommendation in place."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                ae.explanation_id,
                ae.feature_name,
                ae.activity_label,
                ae.current_value,
                ae.historical_mean,
                ae.historical_std,
                ae.deviation,
                ae.direction,
                ae.historical_obs_count,
                o.after_hours_ratio
            FROM alert_explanations ae
            JOIN alerts a ON a.alert_id = ae.alert_id
            JOIN employee_observations o ON o.observation_id = a.observation_id
            """
        ).fetchall()

        updates = []
        for r in rows:
            evidence, rec = build_direction_aware_text(
                feature_name=str(r["feature_name"]),
                activity_label=str(r["activity_label"]),
                current_value=float(r["current_value"]),
                historical_mean=float(r["historical_mean"]) if r["historical_mean"] is not None else None,
                historical_std=float(r["historical_std"]) if r["historical_std"] is not None else None,
                stabilized_deviation=float(r["deviation"]) if r["deviation"] is not None else None,
                direction=str(r["direction"]),
                historical_obs_count=int(r["historical_obs_count"]),
                after_hours_ratio=float(r["after_hours_ratio"]) if r["after_hours_ratio"] is not None else None,
            )
            updates.append((evidence, rec, int(r["explanation_id"])))

        conn.executemany(
            """
            UPDATE alert_explanations
            SET evidence_description = ?, investigation_recommendation = ?
            WHERE explanation_id = ?
            """,
            updates,
        )
        conn.commit()
        return {"refreshed_explanation_rows": len(updates)}
    finally:
        conn.close()


def main() -> None:
    backup_path = DATABASE_PATH.with_suffix(".db.bak")
    shutil.copy2(DATABASE_PATH, backup_path)
    result = refresh_explanations_in_db(DATABASE_PATH)
    result["backup_path"] = str(backup_path.name)
    (METRICS_DIR / "explanation_refresh_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
