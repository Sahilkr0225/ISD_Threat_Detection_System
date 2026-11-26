"""Causal behavioural feature engineering for employee-day activity data.

All rolling/historical features use strictly past observations (`shift(1)`)
grouped by `employee_id` and sorted by `activity_date` to prevent future leakage.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

EPSILON = 1.0
DEFAULT_ROLLING_WINDOW = 14
DEFAULT_MIN_PERIODS = 3

OBSERVABLE_ACTIVITY_FEATURES: List[str] = [
    "login_count",
    "after_hours_login_count",
    "http_activity_count",
    "email_activity_count",
    "file_activity_count",
    "usb_activity_count",
]

ENGINEERED_FEATURES: List[str] = [
    "total_activity_count",
    "after_hours_ratio",
    "is_weekend",
    "log_http_activity",
    "log_email_activity",
    "log_file_activity",
    "log_usb_activity",
    "login_hist_dev_14obs",
    "after_hours_hist_dev_14obs",
    "http_hist_dev_14obs",
    "email_hist_dev_14obs",
    "file_hist_dev_14obs",
    "usb_hist_dev_14obs",
    "total_activity_hist_dev_14obs",
]

APPROVED_MODEL_FEATURES: List[str] = OBSERVABLE_ACTIVITY_FEATURES + ENGINEERED_FEATURES

EXCLUDED_COLUMNS_RATIONALE: Dict[str, str] = {
    "employee_id": "Identifier — excluded to prevent memorizing specific users.",
    "activity_date": "Raw date — excluded so model generalizes across time.",
    "role": "Organisational metadata with 9.5% missingness — reserved for analyst context.",
    "department": "Organisational metadata with 10.9% missingness — reserved for analyst context.",
    "functional_unit": "Organisational metadata with 9.7% missingness — reserved for analyst context.",
    "avg_sentiment": "Sentiment-derived attribute — excluded per observable-behaviour policy.",
    "O": "Psychometric OCEAN trait — excluded per observable-behaviour policy.",
    "C": "Psychometric OCEAN trait — excluded per observable-behaviour policy.",
    "E": "Psychometric OCEAN trait — excluded per observable-behaviour policy.",
    "A": "Psychometric OCEAN trait — excluded per observable-behaviour policy.",
    "N": "Psychometric OCEAN trait — excluded per observable-behaviour policy.",
}


def _causal_rolling_deviation(
    series: pd.Series,
    window: int,
    min_periods: int,
    epsilon: float,
) -> pd.Series:
    """Compute (x_t - mean_{t-W..t-1}) / max(std_{t-W..t-1}, epsilon).

    Current observation x_t is excluded from its baseline via shift(1).
    When fewer than `min_periods` prior observations exist, returns 0.0.
    """
    past = series.shift(1)
    past_mean = past.rolling(window=window, min_periods=min_periods).mean()
    past_std = past.rolling(window=window, min_periods=min_periods).std(ddof=0)

    denom = np.maximum(past_std, epsilon)
    dev = (series - past_mean) / denom
    # Insufficient history -> neutral 0.0 deviation (never NaN or inf)
    return dev.fillna(0.0).replace([np.inf, -np.inf], 0.0)


def engineer_behavioral_features(
    df: pd.DataFrame,
    window: int = DEFAULT_ROLLING_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
    epsilon: float = EPSILON,
) -> pd.DataFrame:
    """Generate causal behavioural features from a cleaned canonical DataFrame."""
    if df.empty:
        raise ValueError("Cannot engineer features on an empty DataFrame.")

    out = df.copy()
    out["activity_date"] = pd.to_datetime(out["activity_date"], errors="raise")
    out = out.sort_values(["employee_id", "activity_date"]).reset_index(drop=True)

    # 1. Instantaneous observable behavioural features
    out["total_activity_count"] = (
        out["login_count"]
        + out["http_activity_count"]
        + out["email_activity_count"]
        + out["file_activity_count"]
        + out["usb_activity_count"]
    )
    out["after_hours_ratio"] = np.where(
        out["login_count"] > 0,
        out["after_hours_login_count"] / np.maximum(out["login_count"], 1),
        0.0,
    )
    out["is_weekend"] = (out["activity_date"].dt.dayofweek >= 5).astype("int64")

    # Log-scaled intensity features for heavy-tailed activity counts
    out["log_http_activity"] = np.log1p(out["http_activity_count"].astype(float))
    out["log_email_activity"] = np.log1p(out["email_activity_count"].astype(float))
    out["log_file_activity"] = np.log1p(out["file_activity_count"].astype(float))
    out["log_usb_activity"] = np.log1p(out["usb_activity_count"].astype(float))

    # 2. Strictly causal per-employee rolling deviations (last `window` active observations)
    dev_specs = {
        "login_count": "login_hist_dev_14obs",
        "after_hours_login_count": "after_hours_hist_dev_14obs",
        "http_activity_count": "http_hist_dev_14obs",
        "email_activity_count": "email_hist_dev_14obs",
        "file_activity_count": "file_hist_dev_14obs",
        "usb_activity_count": "usb_hist_dev_14obs",
        "total_activity_count": "total_activity_hist_dev_14obs",
    }

    grouped = out.groupby("employee_id", sort=False)
    for src_col, target_col in dev_specs.items():
        out[target_col] = grouped[src_col].transform(
            lambda s: _causal_rolling_deviation(
                s.astype(float), window=window, min_periods=min_periods, epsilon=epsilon
            )
        )

    return out


def get_feature_manifest() -> List[dict]:
    """Return structured metadata for all 20 approved model features."""
    descriptions = {
        "login_count": ("total_logon_activity", "int64", "Daily logon event count", "Direct canonical mapping", "None required (0 missing)"),
        "after_hours_login_count": ("after_hours_activity", "int64", "After-hours logon event count", "Direct canonical mapping", "None required (0 missing)"),
        "http_activity_count": ("http_activity_count", "int64", "Daily HTTP request count", "Direct canonical mapping", "None required (0 missing)"),
        "email_activity_count": ("total_emails", "int64", "Daily email count", "Direct canonical mapping", "None required (0 missing)"),
        "file_activity_count": ("file_activity_count", "int64", "Daily file access count", "Direct canonical mapping", "None required (0 missing)"),
        "usb_activity_count": ("usb_activity_count", "int64", "Daily USB connection/activity count", "Direct canonical mapping", "None required (0 missing)"),
        "total_activity_count": ("multiple", "int64", "Total daily observable activity volume", "Sum of login, HTTP, email, file, USB counts", "None"),
        "after_hours_ratio": ("after_hours_activity / total_logon_activity", "float64", "Proportion of logins occurring after hours", "after_hours_login_count / max(login_count, 1)", "Zero when login_count == 0"),
        "is_weekend": ("day", "int64", "Weekend indicator (Sat/Sun = 1)", "1 if dayofweek >= 5 else 0", "None"),
        "log_http_activity": ("http_activity_count", "float64", "Log-scaled HTTP activity intensity", "log1p(http_activity_count)", "None"),
        "log_email_activity": ("total_emails", "float64", "Log-scaled email activity intensity", "log1p(email_activity_count)", "None"),
        "log_file_activity": ("file_activity_count", "float64", "Log-scaled file activity intensity", "log1p(file_activity_count)", "None"),
        "log_usb_activity": ("usb_activity_count", "float64", "Log-scaled USB activity intensity", "log1p(usb_activity_count)", "None"),
    }

    manifest: List[dict] = []
    for feat in APPROVED_MODEL_FEATURES:
        if feat in descriptions:
            src, dtype, desc, calc, miss = descriptions[feat]
            hist_req = "0 prior observations"
        else:
            base = feat.replace("_hist_dev_14obs", "")
            src = base
            dtype = "float64"
            desc = f"Causal 14-observation rolling z-deviation of {base}"
            calc = "(x_t - mean(x_{t-14..t-1})) / max(std(x_{t-14..t-1}), 1.0)"
            miss = "0.0 when fewer than 3 prior observations"
            hist_req = "Minimum 3 prior employee observations (up to 14)"

        manifest.append(
            {
                "feature_name": feat,
                "source_column": src,
                "dtype": dtype,
                "description": desc,
                "calculation_method": calc,
                "missing_value_strategy": miss,
                "historical_requirement": hist_req,
                "leakage_safe": True,
                "approved_for_training": True,
            }
        )
    return manifest

