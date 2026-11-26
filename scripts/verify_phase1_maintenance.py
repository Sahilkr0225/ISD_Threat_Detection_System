"""Quantitative verification for Phase 1 maintenance tasks 2, 4, and 5."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import (
    FEATURE_MATRIX_V1_PATH,
    MASTER_BEHAVIORAL_PATH,
    METRICS_DIR,
    PROCESSED_DATA_DIR,
)
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES


def verify_task2_leakage() -> dict:
    """Compare feature_matrix_v1 *_z_user against full-timeline per-user z-score."""
    cols = [
        "user",
        "day",
        "total_logon_activity",
        "http_activity_count",
        "total_emails",
        "file_activity_count",
        "usb_activity_count",
        "total_logon_activity_z_user",
        "http_activity_count_z_user",
        "total_emails_z_user",
        "file_activity_count_z_user",
        "usb_activity_count_z_user",
    ]
    df = pd.read_parquet(FEATURE_MATRIX_V1_PATH, columns=cols)
    results = {}
    for base in [
        "total_logon_activity",
        "http_activity_count",
        "total_emails",
        "file_activity_count",
        "usb_activity_count",
    ]:
        z_col = f"{base}_z_user"
        grp = df.groupby("user")[base]
        full_mean = grp.transform("mean")
        full_std_ddof1 = grp.transform("std", ddof=1)
        full_std_ddof0 = grp.transform("std", ddof=0)

        recomputed_ddof1 = ((df[base] - full_mean) / full_std_ddof1.replace(0, np.nan)).fillna(0.0)
        recomputed_ddof0 = ((df[base] - full_mean) / full_std_ddof0.replace(0, np.nan)).fillna(0.0)

        diff_ddof1 = float(np.abs(df[z_col] - recomputed_ddof1).max())
        diff_ddof0 = float(np.abs(df[z_col] - recomputed_ddof0).max())
        corr_ddof1 = float(df[z_col].corr(recomputed_ddof1))
        results[z_col] = {
            "max_abs_diff_vs_full_timeline_ddof1": round(diff_ddof1, 8),
            "max_abs_diff_vs_full_timeline_ddof0": round(diff_ddof0, 8),
            "corr_vs_full_timeline_ddof1": round(corr_ddof1, 8),
        }
    del df
    return results


def verify_task4_numerical_stability() -> dict:
    """Inspect historical deviation distributions, zero-variance windows, and after_hours_ratio."""
    df = pd.read_parquet(PROCESSED_DATA_DIR / "engineered_features.parquet")
    dev_cols = [c for c in APPROVED_MODEL_FEATURES if "hist_dev" in c]
    base_map = {
        "login_hist_dev_14obs": "login_count",
        "after_hours_hist_dev_14obs": "after_hours_login_count",
        "http_hist_dev_14obs": "http_activity_count",
        "email_hist_dev_14obs": "email_activity_count",
        "file_hist_dev_14obs": "file_activity_count",
        "usb_hist_dev_14obs": "usb_activity_count",
        "total_activity_hist_dev_14obs": "total_activity_count",
    }

    df = df.sort_values(["employee_id", "activity_date"]).reset_index(drop=True)
    obs_rank = df.groupby("employee_id").cumcount()
    insufficient_history_count = int((obs_rank < 3).sum())

    dev_stats = {}
    for dcol in dev_cols:
        s = df[dcol]
        bcol = base_map[dcol]
        past_std = df.groupby("employee_id")[bcol].transform(
            lambda x: x.shift(1).rolling(14, min_periods=3).std(ddof=0)
        )
        zero_var_windows = int(((obs_rank >= 3) & (past_std == 0)).sum())
        abs_s = s.abs()
        dev_stats[dcol] = {
            "min": round(float(s.min()), 4),
            "p01": round(float(s.quantile(0.01)), 4),
            "median": round(float(s.median()), 4),
            "p95": round(float(s.quantile(0.95)), 4),
            "p99": round(float(s.quantile(0.99)), 4),
            "p999": round(float(s.quantile(0.999)), 4),
            "max": round(float(s.max()), 4),
            "nan_count": int(s.isna().sum()),
            "inf_count": int(np.isinf(s.to_numpy()).sum()),
            "zero_variance_windows": zero_var_windows,
            "abs_gt_10": int((abs_s > 10).sum()),
            "abs_gt_100": int((abs_s > 100).sum()),
            "abs_gt_1000": int((abs_s > 1000).sum()),
        }

    # Semantic check on after_hours_ratio
    ah_gt_login = int((df["after_hours_login_count"] > df["login_count"]).sum())
    zero_login = int((df["login_count"] == 0).sum())
    ah_ratio_gt_1 = int((df["after_hours_ratio"] > 1.0).sum())

    return {
        "total_rows": len(df),
        "insufficient_history_rows": insufficient_history_count,
        "after_hours_semantics": {
            "zero_login_rows": zero_login,
            "after_hours_gt_login_rows": ah_gt_login,
            "after_hours_ratio_gt_1_rows": ah_ratio_gt_1,
            "after_hours_ratio_max": round(float(df["after_hours_ratio"].max()), 4),
        },
        "deviation_stats": dev_stats,
    }


def verify_task5_redundancy() -> list:
    """Find highly correlated pairs (|r| >= 0.80) among approved features in train.parquet."""
    train_df = pd.read_parquet(PROCESSED_DATA_DIR / "train.parquet", columns=APPROVED_MODEL_FEATURES)
    corr = train_df.corr().abs()
    high_pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = float(corr.iloc[i, j])
            if val >= 0.80:
                high_pairs.append(
                    {"feature_a": cols[i], "feature_b": cols[j], "abs_pearson_r": round(val, 4)}
                )
    high_pairs.sort(key=lambda x: x["abs_pearson_r"], reverse=True)
    return high_pairs


def main() -> None:
    report = {
        "task2_leakage": verify_task2_leakage(),
        "task4_stability": verify_task4_numerical_stability(),
        "task5_high_correlations": verify_task5_redundancy(),
    }
    out = METRICS_DIR / "maintenance_verification.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

