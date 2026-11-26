"""Model metadata, evaluation metrics, inference, and data summary endpoints."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import (
    get_db,
    get_predictor,
    get_priority_classifier,
    get_risk_scorer,
)
from backend.app.core.config import METRICS_DIR
from backend.app.database.repository import get_data_summary
from backend.app.ml.predictor import ModelInferenceError, ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer
from backend.app.schemas.api_schemas import (
    DataSummaryResponse,
    ModelInfoResponse,
    ModelPredictBatchRequest,
    ModelPredictResponse,
)

router = APIRouter(tags=["Model & Data"])

DISCLAIMER = (
    "Anomaly and risk scores are statistical prioritization indicators of behavioural "
    "deviation; they do not represent probabilities or definitive evidence of malicious intent."
)


@router.get("/model/info", response_model=ModelInfoResponse)
def read_model_info(predictor: ModelPredictor = Depends(get_predictor)) -> dict:
    """Return loaded model configuration, feature schema, and calibrated thresholds."""
    return {
        "model_version": predictor.model_version,
        "algorithm": str(predictor.metadata.get("algorithm", "IsolationForest")),
        "scaled": bool(predictor.metadata.get("scaled", False)),
        "feature_count": len(predictor.feature_names),
        "feature_names": predictor.feature_names,
        "hyperparameters": {
            "n_estimators": predictor.metadata.get("n_estimators"),
            "max_samples": predictor.metadata.get("max_samples"),
            "contamination": predictor.metadata.get("contamination"),
            "random_state": predictor.metadata.get("random_state"),
        },
        "calibrated_thresholds": predictor.calibrated_thresholds,
        "disclaimer": DISCLAIMER,
    }


@router.get("/model/metrics")
def read_model_metrics() -> Dict[str, Any]:
    """Return verified Phase 2 offline evaluation metrics (not derived from alert statuses)."""
    eval_path = METRICS_DIR / "phase2_evaluation.json"
    audit_path = METRICS_DIR / "phase2_verification_audit.json"
    if not eval_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phase 2 evaluation metrics artifact is unavailable.",
        )

    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    audit_data = (
        json.loads(audit_path.read_text(encoding="utf-8"))
        if audit_path.exists()
        else {}
    )
    return {
        "model_version": eval_data.get("selected_model", "full_engineered_20"),
        "metric_definitions": {
            "roc_auc": "Threshold-independent ranking metric (NOT classification accuracy).",
            "average_precision": "sklearn average_precision_score across all thresholds.",
            "trapezoidal_pr_auc": "Trapezoidal area under the precision-recall curve.",
        },
        "validation_ablation": eval_data.get("validation_ablation"),
        "validation_trapezoidal_pr_auc": audit_data.get("task2_exact_metrics", {}).get(
            "validation_trapezoidal_pr_auc"
        ),
        "validation_threshold_metrics": audit_data.get("task2_exact_metrics", {}).get(
            "validation_thresholds"
        ),
        "held_out_test_summary": {
            "n_samples": eval_data.get("held_out_test_evaluation", {}).get("n_samples"),
            "n_positives": eval_data.get("held_out_test_evaluation", {}).get("n_positives"),
            "base_positive_rate": eval_data.get("held_out_test_evaluation", {}).get(
                "base_positive_rate"
            ),
            "roc_auc": eval_data.get("held_out_test_evaluation", {}).get("roc_auc"),
            "average_precision": eval_data.get("held_out_test_evaluation", {}).get("pr_auc"),
            "trapezoidal_pr_auc": audit_data.get("task2_exact_metrics", {}).get(
                "test_trapezoidal_pr_auc"
            ),
        },
        "held_out_test_threshold_metrics": audit_data.get("task2_exact_metrics", {}).get(
            "test_thresholds"
        ),
    }


@router.post("/model/predict", response_model=ModelPredictResponse)
def predict_observations(
    payload: ModelPredictBatchRequest,
    predictor: ModelPredictor = Depends(get_predictor),
    scorer: RiskScorer = Depends(get_risk_scorer),
    classifier: PriorityClassifier = Depends(get_priority_classifier),
) -> dict:
    """Score a batch of validated 20-feature model-ready observations."""
    records = [obs.model_dump() for obs in payload.observations]
    try:
        raw_preds = predictor.predict_batch(records)
    except ModelInferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    predictions = []
    for pred in raw_preds:
        s = float(pred["anomaly_score"])
        risk = scorer.score_to_risk(s)
        prio = classifier.classify(s)
        predictions.append(
            {
                "anomaly_score": s,
                "risk_score": round(risk, 2),
                "priority": prio,
                "estimator_default_is_anomaly": bool(pred["estimator_default_is_anomaly"]),
                "is_flagged_for_review": classifier.is_alert(prio),
            }
        )

    return {
        "model_version": predictor.model_version,
        "disclaimer": DISCLAIMER,
        "predictions": predictions,
    }


@router.get("/data/summary", response_model=DataSummaryResponse)
def read_data_summary(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Return imported historical demonstration dataset coverage and table counts."""
    summary = get_data_summary(conn)
    summary["note"] = (
        "Historical CERT r4.2 held-out test partition demonstration dataset; "
        "not live organisational monitoring."
    )
    return summary

