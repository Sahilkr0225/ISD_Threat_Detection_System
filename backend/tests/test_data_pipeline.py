"""Unit and integration tests for data loading, validation, cleaning, and chronological splitting."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.app.core.config import MASTER_BEHAVIORAL_PATH
from backend.app.data.loader import DatasetLoadError, load_dataset
from backend.app.data.preprocessing import (
    RAW_TO_CANONICAL_MAP,
    chronological_split,
    clean_behavioral_data,
)
from backend.app.data.validator import (
    DatasetValidationError,
    RAW_REQUIRED_COLUMNS,
    validate_behavioral_dataframe,
    validate_or_raise,
)


def _make_raw_df() -> pd.DataFrame:
    """Create a deterministic, valid raw DataFrame matching master_behavioral_matrix schema."""
    return pd.DataFrame(
        {
            "user": ["EMP001", "EMP001", "EMP001", "EMP002", "EMP002"],
            "day": pd.to_datetime(
                ["2010-01-02", "2010-01-03", "2010-01-04", "2010-01-02", "2010-01-05"]
            ),
            "total_logon_activity": [2, 3, 2, 4, 1],
            "after_hours_activity": [0, 1, 0, 2, 0],
            "http_activity_count": [40.0, 55.0, 30.0, 80.0, 10.0],
            "total_emails": [5.0, 7.0, 4.0, 12.0, 2.0],
            "avg_sentiment": [0.1, -0.2, 0.05, 0.3, -0.1],
            "file_activity_count": [0.0, 2.0, 0.0, 5.0, 0.0],
            "usb_activity_count": [0.0, 1.0, 0.0, 0.0, 0.0],
            "O": [30, 30, 30, 40, 40],
            "C": [25, 25, 25, 35, 35],
            "E": [20, 20, 20, 30, 30],
            "A": [28, 28, 28, 32, 32],
            "N": [22, 22, 22, 26, 26],
            "role": ["Technician", "Technician", "Technician", None, None],
            "department": ["3 - Engineering", "3 - Engineering", "3 - Engineering", None, None],
            "functional_unit": ["2 - Research", "2 - Research", "2 - Research", None, None],
        }
    )


def test_load_valid_parquet(tmp_path: Path) -> None:
    p = tmp_path / "sample.parquet"
    _make_raw_df().to_parquet(p, index=False)
    loaded = load_dataset(p)
    assert len(loaded) == 5
    assert list(loaded.columns) == list(_make_raw_df().columns)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "does_not_exist.parquet")


def test_load_unsupported_format_raises(tmp_path: Path) -> None:
    bad = tmp_path / "data.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="Unsupported file format"):
        load_dataset(bad)


def test_load_empty_parquet_raises(tmp_path: Path) -> None:
    empty_p = tmp_path / "empty.parquet"
    _make_raw_df().iloc[0:0].to_parquet(empty_p, index=False)
    with pytest.raises(DatasetLoadError, match="empty"):
        load_dataset(empty_p)


def test_validate_empty_dataframe() -> None:
    report = validate_behavioral_dataframe(_make_raw_df().iloc[0:0])
    assert report.is_valid is False
    assert any("empty" in e.lower() for e in report.errors)


def test_validate_missing_required_columns() -> None:
    df = _make_raw_df().drop(columns=["usb_activity_count"])
    report = validate_behavioral_dataframe(df)
    assert report.is_valid is False
    assert any("usb_activity_count" in e for e in report.errors)


def test_validate_invalid_dates() -> None:
    df = _make_raw_df()
    df["day"] = df["day"].astype(str)
    df.loc[0, "day"] = "not-a-valid-date"
    report = validate_behavioral_dataframe(df)
    assert report.is_valid is False
    assert any("unparseable date" in e.lower() for e in report.errors)


def test_validate_invalid_numeric_and_infinite_values() -> None:
    df = _make_raw_df()
    df["http_activity_count"] = df["http_activity_count"].astype(object)
    df.loc[0, "http_activity_count"] = "invalid"
    df.loc[1, "total_emails"] = np.inf
    df.loc[2, "file_activity_count"] = -3.0

    report = validate_behavioral_dataframe(df)
    assert report.is_valid is False
    assert any("non-numeric" in e.lower() for e in report.errors)
    assert any("infinite" in e.lower() for e in report.errors)
    assert any("negative" in e.lower() for e in report.errors)


def test_validate_missing_required_value_and_duplicate_emp_date() -> None:
    df = _make_raw_df()
    df.loc[0, "total_logon_activity"] = np.nan
    df.loc[1, "day"] = df.loc[0, "day"]  # duplicate (EMP001, 2010-01-02)
    with pytest.raises(DatasetValidationError):
        validate_or_raise(df)


def test_clean_behavioral_data_canonical_mapping() -> None:
    df = _make_raw_df()
    cleaned, summary = clean_behavioral_data(df)
    for raw_col, canonical_col in RAW_TO_CANONICAL_MAP.items():
        assert canonical_col in cleaned.columns
        if raw_col != canonical_col:
            assert raw_col not in cleaned.columns
    assert summary.original_row_count == 5
    assert summary.cleaned_row_count == 5
    assert cleaned["role"].isna().sum() == 0


def test_chronological_split_no_date_overlap() -> None:
    df, _ = clean_behavioral_data(_make_raw_df())
    train_df, val_df, test_df, manifest = chronological_split(df, train_frac=0.5, val_frac=0.25)

    train_dates = set(train_df["activity_date"].dt.date)
    val_dates = set(val_df["activity_date"].dt.date)
    test_dates = set(test_df["activity_date"].dt.date)

    assert train_dates.isdisjoint(val_dates)
    assert train_dates.isdisjoint(test_dates)
    assert val_dates.isdisjoint(test_dates)
    assert max(train_dates) < min(val_dates) < min(test_dates)
    assert manifest["ground_truth_available"] is False


@pytest.mark.skipif(
    not MASTER_BEHAVIORAL_PATH.exists(),
    reason="Raw master_behavioral_matrix.parquet not present.",
)
def test_actual_master_dataset_smoke() -> None:
    df = load_dataset(MASTER_BEHAVIORAL_PATH, columns=list(RAW_REQUIRED_COLUMNS))
    report = validate_behavioral_dataframe(df, canonical=False)
    assert report.is_valid is True
    assert report.row_count == 330452
    assert report.unique_employees == 1000


def test_ground_truth_labels_aligned_if_present() -> None:
    gt_path = MASTER_BEHAVIORAL_PATH.parent.parent / "processed" / "ground_truth_labels.parquet"
    if not gt_path.exists():
        pytest.skip("ground_truth_labels.parquet not generated.")
    gt_df = pd.read_parquet(gt_path)
    assert len(gt_df) == 330452
    assert int(gt_df["is_malicious_day"].sum()) == 966

