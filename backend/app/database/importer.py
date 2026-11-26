"""Idempotent, batched import of held-out test predictions into SQLite."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import pandas as pd

from backend.app.core.config import (
    DATABASE_PATH,
    MODEL_BUNDLE_PATH,
    MODEL_VERSION,
    PROCESSED_DATA_DIR,
    VALIDATION_SCORE_REF_PATH,
)
from backend.app.database.connection import get_db_connection
from backend.app.database.repository import utc_now_iso
from backend.app.database.schema import init_database
from backend.app.explainability.explainer import generate_behavioural_explanations
from backend.app.ml.predictor import ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer


def ensure_validation_score_reference(
    val_pred_path: Union[str, Path] = PROCESSED_DATA_DIR / "validation_predictions.parquet",
    out_path: Union[str, Path] = VALIDATION_SCORE_REF_PATH,
) -> Path:
    """Persist sorted frozen validation anomaly scores to .npy for fast RiskScorer loading."""
    out = Path(out_path)
    val_df = pd.read_parquet(val_pred_path, columns=["anomaly_score"])
    scores = np.sort(val_df["anomaly_score"].to_numpy(dtype=np.float64))
    if scores.size == 0 or not np.isfinite(scores).all():
        raise ValueError("Validation prediction scores are empty or non-finite.")
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, scores)
    return out


def import_test_predictions_to_db(
    db_path: Union[str, Path] = DATABASE_PATH,
    test_parquet_path: Union[str, Path] = PROCESSED_DATA_DIR / "test.parquet",
    test_preds_path: Union[str, Path] = PROCESSED_DATA_DIR / "test_predictions.parquet",
    cleaned_history_path: Union[str, Path] = PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet",
    model_bundle_path: Union[str, Path] = MODEL_BUNDLE_PATH,
    val_ref_path: Union[str, Path] = VALIDATION_SCORE_REF_PATH,
) -> Dict[str, Any]:
    """Initialize SQLite schema and idempotently import held-out test data and alerts."""
    t0 = time.perf_counter()
    init_database(db_path)

    predictor = ModelPredictor(model_bundle_path)
    scorer = RiskScorer.from_npy(val_ref_path)
    classifier = PriorityClassifier(predictor.calibrated_thresholds)

    test_df = pd.read_parquet(test_parquet_path)
    test_preds = pd.read_parquet(test_preds_path, columns=["employee_id", "activity_date", "anomaly_score"])

    test_df["activity_date_str"] = pd.to_datetime(test_df["activity_date"]).dt.strftime("%Y-%m-%d")
    test_preds["activity_date_str"] = pd.to_datetime(test_preds["activity_date"]).dt.strftime("%Y-%m-%d")

    merged = test_df.merge(
        test_preds[["employee_id", "activity_date_str", "anomaly_score"]],
        on=["employee_id", "activity_date_str"],
        how="inner",
    )
    if len(merged) != len(test_df):
        raise ValueError(f"Alignment mismatch: test={len(test_df)}, merged={len(merged)}")

    scores = merged["anomaly_score"].to_numpy(dtype=np.float64)
    risk_scores = scorer.scores_to_risk(scores)
    priorities = [classifier.classify(float(s)) for s in scores]

    merged["risk_score"] = risk_scores
    merged["priority"] = priorities
    now_iso = utc_now_iso()

    # Employee metadata summary from test partition
    emp_agg = (
        merged.groupby("employee_id", as_index=False)
        .agg(
            role=("role", "first"),
            department=("department", "first"),
            functional_unit=("functional_unit", "first"),
            first_activity_date=("activity_date_str", "min"),
            last_activity_date=("activity_date_str", "max"),
        )
    )
    emp_rows = [
        (
            str(r.employee_id),
            None if pd.isna(r.role) else str(r.role),
            None if pd.isna(r.department) else str(r.department),
            None if pd.isna(r.functional_unit) else str(r.functional_unit),
            str(r.first_activity_date),
            str(r.last_activity_date),
        )
        for r in emp_agg.itertuples(index=False)
    ]

    obs_rows = [
        (
            str(r.employee_id),
            str(r.activity_date_str),
            int(r.login_count),
            int(r.after_hours_login_count),
            int(r.http_activity_count),
            int(r.email_activity_count),
            int(r.file_activity_count),
            int(r.usb_activity_count),
            int(r.total_activity_count),
            float(r.after_hours_ratio),
            int(r.is_weekend),
            MODEL_VERSION,
            float(r.anomaly_score),
            float(r.risk_score),
            str(r.priority),
            now_iso,
        )
        for r in merged.itertuples(index=False)
    ]

    with get_db_connection(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO employees (
                employee_id, role, department, functional_unit,
                first_activity_date, last_activity_date
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id) DO UPDATE SET
                role = excluded.role,
                department = excluded.department,
                functional_unit = excluded.functional_unit,
                first_activity_date = MIN(employees.first_activity_date, excluded.first_activity_date),
                last_activity_date = MAX(employees.last_activity_date, excluded.last_activity_date)
            """,
            emp_rows,
        )

        conn.executemany(
            """
            INSERT OR IGNORE INTO employee_observations (
                employee_id, activity_date,
                login_count, after_hours_login_count, http_activity_count,
                email_activity_count, file_activity_count, usb_activity_count,
                total_activity_count, after_hours_ratio, is_weekend,
                model_version, anomaly_score, risk_score, priority, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            obs_rows,
        )

        # Create alerts idempotently for flagged observations (priority != Informational)
        conn.execute(
            """
            INSERT OR IGNORE INTO alerts (
                observation_id, employee_id, anomaly_score, risk_score,
                priority, status, model_version, created_at, updated_at
            )
            SELECT
                observation_id, employee_id, anomaly_score, risk_score,
                priority, 'OPEN', model_version, ?, ?
            FROM employee_observations
            WHERE priority != 'Informational' AND model_version = ?
            """,
            (now_iso, now_iso, MODEL_VERSION),
        )

        # Fetch alerts that do not yet have explanations
        alerts_needing_exp = conn.execute(
            """
            SELECT
                a.alert_id,
                a.employee_id,
                o.activity_date,
                o.login_count,
                o.after_hours_login_count,
                o.http_activity_count,
                o.email_activity_count,
                o.file_activity_count,
                o.usb_activity_count,
                o.after_hours_ratio
            FROM alerts a
            JOIN employee_observations o ON o.observation_id = a.observation_id
            LEFT JOIN alert_explanations ae ON ae.alert_id = a.alert_id
            WHERE ae.explanation_id IS NULL
            """
        ).fetchall()

        if alerts_needing_exp:
            # Load full chronological employee history (cleaned_behavioral_data) for causal 14-obs lookback
            hist_df = pd.read_parquet(
                cleaned_history_path,
                columns=[
                    "employee_id",
                    "activity_date",
                    "login_count",
                    "after_hours_login_count",
                    "http_activity_count",
                    "email_activity_count",
                    "file_activity_count",
                    "usb_activity_count",
                ],
            )
            hist_df["activity_date_str"] = pd.to_datetime(hist_df["activity_date"]).dt.strftime("%Y-%m-%d")
            hist_df = hist_df.sort_values(["employee_id", "activity_date_str"]).reset_index(drop=True)

            # Build fast per-employee lookup arrays
            emp_hist_lookup: Dict[str, Tuple[List[str], List[dict]]] = {}
            for emp_id, grp in hist_df.groupby("employee_id", sort=False):
                dates_list = grp["activity_date_str"].tolist()
                recs_list = grp[
                    [
                        "login_count",
                        "after_hours_login_count",
                        "http_activity_count",
                        "email_activity_count",
                        "file_activity_count",
                        "usb_activity_count",
                    ]
                ].to_dict(orient="records")
                emp_hist_lookup[str(emp_id)] = (dates_list, recs_list)

            import bisect

            exp_rows: List[tuple] = []
            for al in alerts_needing_exp:
                emp_id = str(al["employee_id"])
                act_date = str(al["activity_date"])
                dates_list, recs_list = emp_hist_lookup.get(emp_id, ([], []))
                idx = bisect.bisect_left(dates_list, act_date)
                prior = recs_list[max(0, idx - 14) : idx]

                current_obs = {
                    "login_count": al["login_count"],
                    "after_hours_login_count": al["after_hours_login_count"],
                    "http_activity_count": al["http_activity_count"],
                    "email_activity_count": al["email_activity_count"],
                    "file_activity_count": al["file_activity_count"],
                    "usb_activity_count": al["usb_activity_count"],
                    "after_hours_ratio": al["after_hours_ratio"],
                }
                exps = generate_behavioural_explanations(current_obs, prior, top_n=3)
                for e in exps:
                    exp_rows.append(
                        (
                            int(al["alert_id"]),
                            e.feature_name,
                            e.activity_label,
                            e.current_value,
                            e.historical_mean,
                            e.historical_std,
                            e.stabilized_deviation,
                            e.direction,
                            e.historical_obs_count,
                            e.evidence_description,
                            e.investigation_recommendation,
                        )
                    )

            conn.executemany(
                """
                INSERT OR IGNORE INTO alert_explanations (
                    alert_id, feature_name, activity_label, current_value,
                    historical_mean, historical_std, deviation, direction,
                    historical_obs_count, evidence_description, investigation_recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                exp_rows,
            )

        counts = {
            "employees": int(conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]),
            "employee_observations": int(conn.execute("SELECT COUNT(*) FROM employee_observations").fetchone()[0]),
            "alerts": int(conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]),
            "alert_explanations": int(conn.execute("SELECT COUNT(*) FROM alert_explanations").fetchone()[0]),
            "investigation_history": int(conn.execute("SELECT COUNT(*) FROM investigation_history").fetchone()[0]),
        }
        prio_breakdown = {
            str(r["priority"]): int(r["cnt"])
            for r in conn.execute("SELECT priority, COUNT(*) AS cnt FROM alerts GROUP BY priority").fetchall()
        }

    elapsed = round(time.perf_counter() - t0, 3)
    return {
        "elapsed_seconds": elapsed,
        "source_rows": int(len(merged)),
        "table_counts": counts,
        "alerts_by_priority": prio_breakdown,
    }

