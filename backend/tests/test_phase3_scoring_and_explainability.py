"""Unit tests for ModelPredictor, RiskScorer, PriorityClassifier, and BehaviouralExplainer."""

from pathlib import Path

import numpy as np
import pytest

from backend.app.core.config import MODEL_BUNDLE_PATH, VALIDATION_SCORE_REF_PATH
from backend.app.explainability.explainer import generate_behavioural_explanations
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES
from backend.app.ml.predictor import ModelInferenceError, ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer


def _sample_feature_dict() -> dict:
    return {feat: 0.0 for feat in APPROVED_MODEL_FEATURES}


def test_model_predictor_loads_and_predicts_consistently() -> None:
    if not MODEL_BUNDLE_PATH.exists():
        pytest.skip("Model bundle not present.")
    predictor = ModelPredictor(MODEL_BUNDLE_PATH)
    assert predictor.feature_names == APPROVED_MODEL_FEATURES

    vec = _sample_feature_dict()
    single = predictor.predict_single(vec)
    batch = predictor.predict_batch([vec, vec])

    assert len(batch) == 2
    assert single["anomaly_score"] == pytest.approx(batch[0]["anomaly_score"], rel=1e-9)
    assert isinstance(single["estimator_default_is_anomaly"], bool)


def test_model_predictor_rejects_invalid_inputs() -> None:
    if not MODEL_BUNDLE_PATH.exists():
        pytest.skip("Model bundle not present.")
    predictor = ModelPredictor(MODEL_BUNDLE_PATH)

    bad_missing = _sample_feature_dict()
    del bad_missing["login_count"]
    with pytest.raises(ModelInferenceError, match="Missing required"):
        predictor.predict_single(bad_missing)

    bad_nan = _sample_feature_dict()
    bad_nan["usb_activity_count"] = float("nan")
    with pytest.raises(ModelInferenceError, match="NaN or infinite"):
        predictor.predict_single(bad_nan)

    bad_extra = _sample_feature_dict()
    bad_extra["is_malicious_day"] = 1
    with pytest.raises(ModelInferenceError, match="Unexpected non-model"):
        predictor.predict_single(bad_extra)

    with pytest.raises(FileNotFoundError):
        ModelPredictor(Path("models/nonexistent_bundle.joblib"))


def test_risk_scorer_range_monotonicity_and_ties() -> None:
    ref = np.array([-0.20, -0.10, -0.10, 0.0, 0.10, 0.25])
    scorer = RiskScorer(ref)

    s_low = scorer.score_to_risk(-0.30)
    s_tie = scorer.score_to_risk(-0.10)
    s_mid = scorer.score_to_risk(0.05)
    s_high = scorer.score_to_risk(0.50)

    assert 0.0 <= s_low <= s_tie <= s_mid <= s_high <= 100.0
    assert s_low == 0.0
    assert s_high == 100.0
    # Deterministic tie handling (side='right' includes both -0.10 entries -> 3/6 = 50.0)
    assert s_tie == pytest.approx(50.0)

    if VALIDATION_SCORE_REF_PATH.exists():
        frozen_scorer = RiskScorer.from_npy(VALIDATION_SCORE_REF_PATH)
        assert frozen_scorer.reference_size == 60812


def test_priority_classifier_boundaries_and_ordering() -> None:
    thresholds = {
        "top_1pct_threshold": 0.12,
        "top_2pct_threshold": 0.09,
        "sklearn_default_zero_threshold": 0.0,
        "f1_optimal_threshold": -0.04,
    }
    clf = PriorityClassifier(thresholds)

    assert clf.classify(0.12) == "Critical"
    assert clf.classify(0.09) == "High"
    assert clf.classify(0.0) == "Medium"
    assert clf.classify(-0.04) == "Low"
    assert clf.classify(-0.05) == "Informational"

    with pytest.raises(ValueError, match="Thresholds must be ordered"):
        PriorityClassifier({**thresholds, "top_1pct_threshold": -0.5})


def test_explainability_causal_and_insufficient_history() -> None:
    current = {
        "login_count": 5,
        "after_hours_login_count": 4,
        "http_activity_count": 80,
        "email_activity_count": 6,
        "file_activity_count": 2,
        "usb_activity_count": 12,
        "after_hours_ratio": 0.8,
    }
    # Insufficient history (< 3 prior obs) must not fabricate historical stats
    exps_short = generate_behavioural_explanations(current, prior_observations=[current, current], top_n=3)
    assert len(exps_short) == 3
    assert all(e.historical_mean is None and e.direction == "insufficient_history" for e in exps_short)

    # Sufficient prior history (4 normal observations)
    normal_day = {
        "login_count": 2,
        "after_hours_login_count": 0,
        "http_activity_count": 80,
        "email_activity_count": 6,
        "file_activity_count": 1,
        "usb_activity_count": 0,
    }
    exps = generate_behavioural_explanations(current, prior_observations=[normal_day] * 4, top_n=3)
    assert len(exps) == 3
    # Strongest deviation should be usb_activity_count (+12.0 with floor 1.0)
    assert exps[0].feature_name == "usb_activity_count"
    assert exps[0].stabilized_deviation == 12.0
    assert exps[0].historical_obs_count == 4
    # Distinct primary activities only (no duplicate log_* or *_hist_dev_* entries)
    assert len({e.feature_name for e in exps}) == 3


def test_explainability_direction_aware_cases() -> None:
    baseline_day = {
        "login_count": 3,
        "after_hours_login_count": 0,
        "http_activity_count": 100,
        "email_activity_count": 10,
        "file_activity_count": 5,
        "usb_activity_count": 2,
    }
    prior = [baseline_day] * 5

    # Case 1: Zero recorded http/email/usb while login is unchanged
    zero_day = {
        "login_count": 3,
        "after_hours_login_count": 0,
        "http_activity_count": 0,
        "email_activity_count": 0,
        "file_activity_count": 3,  # decreased but non-zero
        "usb_activity_count": 2,   # unchanged
        "after_hours_ratio": 0.0,
    }
    exps_zero = {e.feature_name: e for e in generate_behavioural_explanations(zero_day, prior, top_n=6)}
    assert exps_zero["http_activity_count"].direction == "below_baseline"
    assert exps_zero["http_activity_count"].stabilized_deviation == -100.0
    assert "No web activities were recorded (0)" in exps_zero["http_activity_count"].evidence_description
    assert "logs are complete" in exps_zero["http_activity_count"].investigation_recommendation

    assert exps_zero["file_activity_count"].direction == "below_baseline"
    assert "lower than usual" in exps_zero["file_activity_count"].evidence_description

    assert exps_zero["usb_activity_count"].direction == "near_baseline"
    assert exps_zero["usb_activity_count"].stabilized_deviation == 0.0
    assert "consistent with" in exps_zero["usb_activity_count"].investigation_recommendation

    # Case 2: Increased USB & after-hours
    spike_day = {
        "login_count": 5,
        "after_hours_login_count": 4,
        "http_activity_count": 100,
        "email_activity_count": 10,
        "file_activity_count": 5,
        "usb_activity_count": 12,
        "after_hours_ratio": 0.8,
    }
    exps_spike = {e.feature_name: e for e in generate_behavioural_explanations(spike_day, prior, top_n=6)}
    assert exps_spike["usb_activity_count"].direction == "above_baseline"
    assert exps_spike["usb_activity_count"].stabilized_deviation == 10.0
    assert "removable-device" in exps_spike["usb_activity_count"].investigation_recommendation
    assert exps_spike["after_hours_login_count"].direction == "above_baseline"
    assert "authorized" in exps_spike["after_hours_login_count"].investigation_recommendation

