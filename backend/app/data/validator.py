"""Schema, type, and data-quality validation for employee-day behavioural data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

# Raw columns required from master_behavioral_matrix.parquet
RAW_REQUIRED_COLUMNS = (
    "user",
    "day",
    "total_logon_activity",
    "after_hours_activity",
    "http_activity_count",
    "total_emails",
    "file_activity_count",
    "usb_activity_count",
)

RAW_NUMERIC_ACTIVITY_COLUMNS = (
    "total_logon_activity",
    "after_hours_activity",
    "http_activity_count",
    "total_emails",
    "file_activity_count",
    "usb_activity_count",
)

CANONICAL_REQUIRED_COLUMNS = (
    "employee_id",
    "activity_date",
    "login_count",
    "after_hours_login_count",
    "http_activity_count",
    "email_activity_count",
    "file_activity_count",
    "usb_activity_count",
)

CANONICAL_NUMERIC_ACTIVITY_COLUMNS = (
    "login_count",
    "after_hours_login_count",
    "http_activity_count",
    "email_activity_count",
    "file_activity_count",
    "usb_activity_count",
)


class DatasetValidationError(ValueError):
    """Raised when a dataset fails validation checks."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("Dataset validation failed:\n- " + "\n- ".join(self.errors))


@dataclass
class ValidationReport:
    """Structured summary of dataset validation results."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0
    unique_employees: int = 0
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    missing_counts: Dict[str, int] = field(default_factory=dict)


def validate_behavioral_dataframe(
    df: pd.DataFrame,
    canonical: bool = False,
) -> ValidationReport:
    """Validate raw or canonical employee-day behavioural DataFrame."""
    errors: List[str] = []
    warnings: List[str] = []

    if df is None or df.empty:
        return ValidationReport(
            is_valid=False,
            errors=["Dataset is empty (0 rows)."],
            row_count=0,
        )

    req_cols = CANONICAL_REQUIRED_COLUMNS if canonical else RAW_REQUIRED_COLUMNS
    num_cols = CANONICAL_NUMERIC_ACTIVITY_COLUMNS if canonical else RAW_NUMERIC_ACTIVITY_COLUMNS
    emp_col = "employee_id" if canonical else "user"
    date_col = "activity_date" if canonical else "day"

    missing_cols = [c for c in req_cols if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required column(s): {', '.join(missing_cols)}")

    # Missing values check
    missing_counts: Dict[str, int] = {}
    for col in df.columns:
        cnt = int(df[col].isna().sum())
        if cnt > 0:
            missing_counts[col] = cnt
            if col in req_cols:
                errors.append(f"Required column '{col}' contains {cnt} missing value(s).")

    # Employee identifier validation
    if emp_col in df.columns:
        emp_series = df[emp_col].dropna().astype(str).str.strip()
        empty_emp = int((emp_series == "").sum())
        if empty_emp > 0:
            errors.append(f"Column '{emp_col}' contains {empty_emp} blank identifier(s).")

    # Date parsing validation
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    if date_col in df.columns:
        non_null_dates = df[date_col].notna()
        parsed_dates = pd.to_datetime(
            df.loc[non_null_dates, date_col], format="mixed", errors="coerce"
        )
        bad_dates = int(parsed_dates.isna().sum())
        if bad_dates > 0:
            errors.append(f"Column '{date_col}' contains {bad_dates} unparseable date value(s).")
        valid_dates = parsed_dates.dropna()
        if not valid_dates.empty:
            date_min = str(valid_dates.min().date())
            date_max = str(valid_dates.max().date())

    # Numerical, infinite, and negative value checks
    for col in num_cols:
        if col not in df.columns:
            continue
        series = df[col]
        if pd.api.types.is_bool_dtype(series):
            errors.append(f"Column '{col}' has boolean dtype; expected numeric.")
            continue
        non_null = series.dropna()
        coerced = pd.to_numeric(non_null, errors="coerce")
        bad_num = int(coerced.isna().sum())
        if bad_num > 0:
            errors.append(f"Column '{col}' contains {bad_num} non-numeric value(s).")
            continue
        arr = coerced.to_numpy(dtype=float)
        inf_cnt = int(np.isinf(arr).sum())
        if inf_cnt > 0:
            errors.append(f"Column '{col}' contains {inf_cnt} infinite value(s).")
        neg_cnt = int((arr < 0).sum())
        if neg_cnt > 0:
            errors.append(f"Column '{col}' contains {neg_cnt} negative activity count(s).")

    # Duplicate employee-date uniqueness
    if emp_col in df.columns and date_col in df.columns:
        dup_cnt = int(df.duplicated(subset=[emp_col, date_col]).sum())
        if dup_cnt > 0:
            errors.append(
                f"Detected {dup_cnt} duplicate ({emp_col}, {date_col}) record(s)."
            )

    # Warn about optional metadata missing values
    for meta_col in ("role", "department", "functional_unit"):
        if meta_col in missing_counts:
            warnings.append(
                f"Optional metadata column '{meta_col}' has {missing_counts[meta_col]} missing value(s)."
            )

    unique_employees = (
        int(df[emp_col].dropna().astype(str).str.strip().nunique())
        if emp_col in df.columns
        else 0
    )

    return ValidationReport(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        row_count=len(df),
        unique_employees=unique_employees,
        date_min=date_min,
        date_max=date_max,
        missing_counts=missing_counts,
    )


def validate_or_raise(df: pd.DataFrame, canonical: bool = False) -> ValidationReport:
    """Validate DataFrame and raise DatasetValidationError if invalid."""
    report = validate_behavioral_dataframe(df, canonical=canonical)
    if not report.is_valid:
        raise DatasetValidationError(report.errors)
    return report

