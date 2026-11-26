"""Offline evaluation and validation-only threshold calibration for anomaly scores."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_anomaly_scores(
    y_true: np.ndarray,
    anomaly_scores: np.ndarray,
    scenarios: Optional[np.ndarray] = None,
    top_k_list: Sequence[int] = (100, 250, 500, 1000),
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate continuous anomaly scores against ground-truth binary labels."""
    y = np.asarray(y_true, dtype=int)
    scores = np.asarray(anomaly_scores, dtype=float)
    if len(y) != len(scores):
        raise ValueError("y_true and anomaly_scores must have identical length.")
    if len(np.unique(y)) < 2:
        raise ValueError("y_true must contain both positive and negative classes for ROC/PR evaluation.")

    roc_auc = float(roc_auc_score(y, scores))
    pr_auc = float(average_precision_score(y, scores))
    base_rate = float(y.mean())

    order = np.argsort(-scores)
    sorted_y = y[order]
    total_positives = int(y.sum())

    top_k_metrics: Dict[str, Dict[str, float]] = {}
    for k in top_k_list:
        k_eff = min(int(k), len(y))
        hits = int(sorted_y[:k_eff].sum())
        top_k_metrics[f"top_{k}"] = {
            "k": k_eff,
            "hits": hits,
            "precision_at_k": round(hits / k_eff, 4),
            "recall_at_k": round(hits / total_positives, 4),
            "lift_over_base_rate": round((hits / k_eff) / base_rate, 2),
        }

    result: Dict[str, Any] = {
        "n_samples": int(len(y)),
        "n_positives": total_positives,
        "base_positive_rate": round(base_rate, 6),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "score_summary": {
            "min": round(float(scores.min()), 4),
            "median": round(float(np.median(scores)), 4),
            "p95": round(float(np.quantile(scores, 0.95)), 4),
            "p99": round(float(np.quantile(scores, 0.99)), 4),
            "max": round(float(scores.max()), 4),
        },
        "top_k": top_k_metrics,
    }

    if threshold is not None:
        y_pred = (scores >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
        result["threshold_eval"] = {
            "threshold": round(float(threshold), 6),
            "predicted_alerts": int(y_pred.sum()),
            "alert_rate_pct": round(100.0 * float(y_pred.mean()), 4),
            "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y, y_pred, zero_division=0)), 4),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        }
        if scenarios is not None:
            scen_arr = np.asarray(scenarios)
            per_scenario: Dict[str, Dict[str, Any]] = {}
            for sc in sorted(np.unique(scen_arr[y == 1])):
                mask = scen_arr == sc
                sc_total = int(mask.sum())
                sc_tp = int(((y_pred == 1) & mask).sum())
                per_scenario[f"scenario_{int(sc)}"] = {
                    "total": sc_total,
                    "detected": sc_tp,
                    "recall": round(sc_tp / sc_total, 4) if sc_total > 0 else 0.0,
                }
            result["threshold_eval"]["per_scenario_recall"] = per_scenario

    return result


def calibrate_thresholds_on_validation(
    y_val: np.ndarray,
    val_scores: np.ndarray,
) -> Dict[str, float]:
    """Derive candidate operating thresholds strictly on validation data."""
    y = np.asarray(y_val, dtype=int)
    scores = np.asarray(val_scores, dtype=float)

    precisions, recalls, thresholds = precision_recall_curve(y, scores)
    # Compute F1 for each threshold (precision_recall_curve returns len(thresholds) == len(precisions) - 1)
    p_t = precisions[:-1]
    r_t = recalls[:-1]
    denom = p_t + r_t
    f1s = np.divide(
        2 * p_t * r_t,
        denom,
        out=np.zeros_like(denom, dtype=float),
        where=denom > 0,
    )
    best_f1_idx = int(np.argmax(f1s))

    return {
        "f1_optimal_threshold": float(thresholds[best_f1_idx]),
        "top_1pct_threshold": float(np.quantile(scores, 0.99)),
        "top_2pct_threshold": float(np.quantile(scores, 0.98)),
        "sklearn_default_zero_threshold": 0.0,
    }

