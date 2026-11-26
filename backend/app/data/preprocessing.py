"""Canonical schema mapping, cleaning, and chronological splitting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from backend.app.data.validator import (
    CANONICAL_NUMERIC_ACTIVITY_COLUMNS,
    validate_or_raise,
)

# Documented mapping from master_behavioral_matrix.parquet columns to canonical names
RAW_TO_CANONICAL_MAP: Dict[str, str] = {
    "user": "employee_id",
    "day": "activity_date",
    "total_logon_activity": "login_count",
    "after_hours_activity": "after_hours_login_count",
    "http_activity_count": "http_activity_count",
    "total_emails": "email_activity_count",
    "file_activity_count": "file_activity_count",
    "usb_activity_count": "usb_activity_count",
}

METADATA_COLUMNS: Tuple[str, ...] = ("role", "department", "functional_unit")

# Psychometric & sentiment columns audited in master_behavioral_matrix.parquet
# Excluded from initial unsupervised behavioural model per Section 13.
EXCLUDED_PSYCH_SENTIMENT_COLUMNS: Tuple[str, ...] = ("avg_sentiment", "O", "C", "E", "A", "N")


@dataclass
class CleaningSummary:
    """Reproducible summary of data cleaning operations."""

    original_row_count: int
    cleaned_row_count: int
    affected_records: int
    missing_values_handled: Dict[str, int]
    duplicate_records_handled: int
    invalid_values_handled: int
    remaining_data_quality_issues: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


def clean_behavioral_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, CleaningSummary]:
    """Validate, map to canonical schema, and clean master_behavioral_matrix data.

    Cleaning decisions:
    - Does NOT remove extreme activity values (potential threat signals).
    - Does NOT blindly replace missing numeric values with zero.
    - Converts exact-integer float count columns to int64 for memory efficiency.
    - Preserves employee_id, activity_date, and fills missing org metadata with 'Unknown'
      for reporting only (metadata is excluded from ML model features).
    """
    validate_or_raise(df, canonical=False)
    original_rows = len(df)

    selected_cols = list(RAW_TO_CANONICAL_MAP.keys()) + [
        c for c in METADATA_COLUMNS if c in df.columns
    ]
    cleaned = df[selected_cols].rename(columns=RAW_TO_CANONICAL_MAP).copy()

    cleaned["employee_id"] = cleaned["employee_id"].astype(str).str.strip()
    cleaned["activity_date"] = pd.to_datetime(cleaned["activity_date"], errors="raise")

    # Cast activity counts to int64 only when no fractional values exist
    for col in CANONICAL_NUMERIC_ACTIVITY_COLUMNS:
        series = pd.to_numeric(cleaned[col], errors="raise")
        if ((series % 1) != 0).any():
            cleaned[col] = series.astype("float64")
        else:
            cleaned[col] = series.astype("int64")

    missing_handled: Dict[str, int] = {}
    affected_mask = pd.Series(False, index=cleaned.index)
    for col in METADATA_COLUMNS:
        if col in cleaned.columns:
            na_mask = cleaned[col].isna()
            na_cnt = int(na_mask.sum())
            if na_cnt > 0:
                missing_handled[col] = na_cnt
                affected_mask = affected_mask | na_mask
                cleaned[col] = cleaned[col].fillna("Unknown").astype(str)

    # Sort deterministically by (employee_id, activity_date)
    cleaned = cleaned.sort_values(["employee_id", "activity_date"]).reset_index(drop=True)

    validate_or_raise(cleaned, canonical=True)

    summary = CleaningSummary(
        original_row_count=original_rows,
        cleaned_row_count=len(cleaned),
        affected_records=int(affected_mask.sum()),
        missing_values_handled=missing_handled,
        duplicate_records_handled=0,
        invalid_values_handled=0,
        remaining_data_quality_issues=[
            "Ground-truth insider threat labels are not present in master_behavioral_matrix.parquet."
        ],
    )
    return cleaned, summary


def chronological_split(
    df: pd.DataFrame,
    train_frac: float = 0.60,
    val_frac: float = 0.20,
    date_col: str = "activity_date",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Split dataset strictly by unique sorted dates (no random row splitting).

    Default: earliest 60% of unique dates -> train, next 20% -> validation, latest 20% -> test.
    """
    if not (0 < train_frac < 1 and 0 < val_frac < 1 and train_frac + val_frac < 1):
        raise ValueError("train_frac and val_frac must be positive and sum to < 1.0.")

    dates = pd.to_datetime(df[date_col])
    unique_dates = np.sort(dates.dt.normalize().unique())
    n_dates = len(unique_dates)
    if n_dates < 3:
        raise ValueError(f"Need at least 3 unique dates for 3-way chronological split; got {n_dates}.")

    train_end_idx = max(1, int(np.floor(n_dates * train_frac)))
    val_end_idx = max(train_end_idx + 1, int(np.floor(n_dates * (train_frac + val_frac))))
    if val_end_idx >= n_dates:
        val_end_idx = n_dates - 1

    train_dates = set(unique_dates[:train_end_idx])
    val_dates = set(unique_dates[train_end_idx:val_end_idx])
    test_dates = set(unique_dates[val_end_idx:])

    norm_dates = dates.dt.normalize()
    train_df = df[norm_dates.isin(train_dates)].copy().reset_index(drop=True)
    val_df = df[norm_dates.isin(val_dates)].copy().reset_index(drop=True)
    test_df = df[norm_dates.isin(test_dates)].copy().reset_index(drop=True)

    manifest = {
        "strategy": "chronological_unique_dates",
        "train_frac_target": train_frac,
        "val_frac_target": val_frac,
        "test_frac_target": round(1.0 - train_frac - val_frac, 4),
        "splits": {
            "train": {
                "date_min": str(pd.Timestamp(min(train_dates)).date()),
                "date_max": str(pd.Timestamp(max(train_dates)).date()),
                "unique_dates": len(train_dates),
                "row_count": len(train_df),
                "unique_employees": int(train_df["employee_id"].nunique()),
            },
            "validation": {
                "date_min": str(pd.Timestamp(min(val_dates)).date()),
                "date_max": str(pd.Timestamp(max(val_dates)).date()),
                "unique_dates": len(val_dates),
                "row_count": len(val_df),
                "unique_employees": int(val_df["employee_id"].nunique()),
            },
            "test": {
                "date_min": str(pd.Timestamp(min(test_dates)).date()),
                "date_max": str(pd.Timestamp(max(test_dates)).date()),
                "unique_dates": len(test_dates),
                "row_count": len(test_df),
                "unique_employees": int(test_df["employee_id"].nunique()),
            },
        },
        "ground_truth_available": False,
    }
    return train_df, val_df, test_df, manifest

