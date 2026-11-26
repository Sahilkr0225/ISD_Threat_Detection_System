"""Unit tests for causal behavioural feature engineering."""

import numpy as np
import pandas as pd

from backend.app.data.preprocessing import clean_behavioral_data
from backend.app.features.feature_engineering import (
    APPROVED_MODEL_FEATURES,
    engineer_behavioral_features,
)


def _make_sample_cleaned_df() -> pd.DataFrame:
    raw = pd.DataFrame(
        {
            "user": ["EMP1"] * 6 + ["EMP2"] * 4,
            "day": pd.to_datetime(
                [
                    "2010-01-02",
                    "2010-01-03",
                    "2010-01-04",
                    "2010-01-05",
                    "2010-01-06",
                    "2010-01-07",
                    "2010-01-02",
                    "2010-01-03",
                    "2010-01-04",
                    "2010-01-05",
                ]
            ),
            "total_logon_activity": [2, 2, 2, 2, 6, 3, 0, 1, 1, 1],
            "after_hours_activity": [0, 0, 0, 0, 3, 1, 0, 0, 0, 0],
            "http_activity_count": [10, 10, 10, 10, 50, 12, 0, 5, 5, 5],
            "total_emails": [4, 4, 4, 4, 20, 5, 0, 2, 2, 2],
            "file_activity_count": [0, 0, 0, 0, 10, 1, 0, 0, 0, 0],
            "usb_activity_count": [0, 0, 0, 0, 5, 0, 0, 0, 0, 0],
        }
    )
    cleaned, _ = clean_behavioral_data(raw)
    return cleaned


def test_feature_engineering_zero_denominator_and_insufficient_history() -> None:
    cleaned = _make_sample_cleaned_df()
    feat_df = engineer_behavioral_features(cleaned, window=14, min_periods=3)

    # EMP2 day 0 has login_count == 0 -> after_hours_ratio must be 0.0 (no ZeroDivisionError/NaN)
    emp2_first = feat_df[(feat_df["employee_id"] == "EMP2")].iloc[0]
    assert emp2_first["after_hours_ratio"] == 0.0

    # First 3 observations (< min_periods prior observations) must have 0.0 rolling deviation
    emp1_rows = feat_df[feat_df["employee_id"] == "EMP1"].reset_index(drop=True)
    assert emp1_rows.loc[0, "login_hist_dev_14obs"] == 0.0
    assert emp1_rows.loc[1, "login_hist_dev_14obs"] == 0.0
    assert emp1_rows.loc[2, "login_hist_dev_14obs"] == 0.0

    # EMP1 days 0..3 had constant login_count == 2 (past_std == 0 -> guarded by epsilon=1.0)
    # Day 4 has login_count == 6 -> exact +4.0 deviation without 1000x amplification or inf/NaN
    assert emp1_rows.loc[4, "login_hist_dev_14obs"] == 4.0
    assert np.isfinite(feat_df[APPROVED_MODEL_FEATURES].to_numpy()).all()


def test_no_future_leakage_in_causal_rolling_features() -> None:
    cleaned = _make_sample_cleaned_df()
    baseline_feats = engineer_behavioral_features(cleaned, window=14, min_periods=3)

    # Perturb the final future day for EMP1 dramatically
    modified = cleaned.copy()
    mask = (modified["employee_id"] == "EMP1") & (
        modified["activity_date"] == pd.Timestamp("2010-01-07")
    )
    modified.loc[mask, "login_count"] = 999
    modified.loc[mask, "http_activity_count"] = 9999

    perturbed_feats = engineer_behavioral_features(modified, window=14, min_periods=3)

    # All earlier days (before 2010-01-07) must be 100% identical
    earlier_base = baseline_feats[baseline_feats["activity_date"] < pd.Timestamp("2010-01-07")]
    earlier_pert = perturbed_feats[perturbed_feats["activity_date"] < pd.Timestamp("2010-01-07")]
    pd.testing.assert_frame_equal(
        earlier_base[APPROVED_MODEL_FEATURES].reset_index(drop=True),
        earlier_pert[APPROVED_MODEL_FEATURES].reset_index(drop=True),
    )


def test_identifiers_and_ground_truth_excluded_from_model_features() -> None:
    forbidden = {"employee_id", "activity_date", "user", "day", "O", "C", "E", "A", "N", "avg_sentiment", "role", "department", "functional_unit", "is_anomaly", "label"}
    assert forbidden.isdisjoint(set(APPROVED_MODEL_FEATURES))

