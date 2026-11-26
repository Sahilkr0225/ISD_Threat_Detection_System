"""Unit tests for Phase 2 Isolation Forest training, scoring, persistence, and evaluation."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.app.ml.evaluation import (
    calibrate_thresholds_on_validation,
    evaluate_anomaly_scores,
)
from backend.app.ml.isolation_forest import (
    load_model_bundle,
    save_model_bundle,
    score_anomalies,
    train_isolation_forest,
)


def _make_synthetic_cluster(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    X_train = pd.DataFrame(rng.normal(0.0, 1.0, size=(200, 4)), columns=["f1", "f2", "f3", "f4"])
    X_val_norm = rng.normal(0.0, 1.0, size=(90, 4))
    X_val_anom = rng.normal(8.0, 0.5, size=(10, 4))
    X_val = pd.DataFrame(np.vstack([X_val_norm, X_val_anom]), columns=["f1", "f2", "f3", "f4"])
    y_val = np.array([0] * 90 + [1] * 10)
    return X_train, X_val, y_val


def test_isolation_forest_detects_clear_outliers_deterministically() -> None:
    X_train, X_val, y_val = _make_synthetic_cluster(seed=42)
    m1 = train_isolation_forest(X_train, n_estimators=100, random_state=42, n_jobs=1)
    m2 = train_isolation_forest(X_train, n_estimators=100, random_state=42, n_jobs=1)

    s1 = score_anomalies(m1, X_val)
    s2 = score_anomalies(m2, X_val)
    np.testing.assert_allclose(s1, s2)

    # Outlier cluster must score higher than normal cluster
    assert float(s1[y_val == 1].mean()) > float(s1[y_val == 0].mean())


def test_model_bundle_save_and_load_roundtrip(tmp_path: Path) -> None:
    X_train, X_val, _ = _make_synthetic_cluster(seed=42)
    model = train_isolation_forest(X_train, n_estimators=50, random_state=42, n_jobs=1)
    scores_before = score_anomalies(model, X_val)

    bundle_path = tmp_path / "iforest.joblib"
    save_model_bundle(
        model=model,
        feature_names=list(X_train.columns),
        metadata={"phase": 2},
        output_path=bundle_path,
    )
    loaded = load_model_bundle(bundle_path)
    scores_after = score_anomalies(loaded["model"], X_val)

    assert loaded["feature_names"] == list(X_train.columns)
    assert loaded["metadata"]["phase"] == 2
    np.testing.assert_allclose(scores_before, scores_after)


def test_train_rejects_non_finite_values() -> None:
    X_bad = pd.DataFrame({"f1": [1.0, np.nan], "f2": [0.0, 1.0]})
    with pytest.raises(ValueError, match="NaN or infinite"):
        train_isolation_forest(X_bad)


def test_evaluation_and_validation_calibration() -> None:
    _, X_val, y_val = _make_synthetic_cluster(seed=42)
    model = train_isolation_forest(X_val[y_val == 0], n_estimators=100, random_state=42, n_jobs=1)
    scores = score_anomalies(model, X_val)

    thresholds = calibrate_thresholds_on_validation(y_val, scores)
    assert "f1_optimal_threshold" in thresholds
    assert "top_1pct_threshold" in thresholds

    metrics = evaluate_anomaly_scores(
        y_true=y_val,
        anomaly_scores=scores,
        top_k_list=(10, 20),
        threshold=thresholds["f1_optimal_threshold"],
    )
    assert metrics["roc_auc"] > 0.95
    assert metrics["pr_auc"] > 0.90
    assert metrics["top_k"]["top_10"]["hits"] >= 9


def test_feature_ordering_and_threshold_direction() -> None:
    X_train, X_val, y_val = _make_synthetic_cluster(seed=42)
    model = train_isolation_forest(X_train, n_estimators=50, random_state=42, n_jobs=1)

    # Shuffled columns passed as raw numpy array change scores; enforcing column order preserves them
    scores_ordered = score_anomalies(model, X_val[["f1", "f2", "f3", "f4"]])
    scores_wrong_order = score_anomalies(model, X_val[["f4", "f3", "f2", "f1"]])
    assert not np.allclose(scores_ordered, scores_wrong_order)

    # Higher score >= threshold triggers alert
    high_thr = float(np.quantile(scores_ordered, 0.90))
    preds = (scores_ordered >= high_thr).astype(int)
    assert int(preds.sum()) >= 1
    assert float(scores_ordered[preds == 1].min()) >= high_thr

