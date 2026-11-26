"""Phase 2: Unsupervised Isolation Forest training, ablation, calibration, and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import (
    FIGURES_DIR,
    METRICS_DIR,
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    RANDOM_SEED,
)
from backend.app.ml.evaluation import (
    calibrate_thresholds_on_validation,
    evaluate_anomaly_scores,
)
from backend.app.ml.isolation_forest import (
    FULL_ENGINEERED_FEATURES,
    RAW_BASELINE_FEATURES,
    save_model_bundle,
    score_anomalies,
    train_isolation_forest,
)


def _align_labels(split_df: pd.DataFrame, labels_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    keys = split_df[["employee_id", "activity_date"]].copy()
    keys["activity_date"] = pd.to_datetime(keys["activity_date"]).dt.normalize()
    merged = keys.merge(labels_df, on=["employee_id", "activity_date"], how="left")
    if merged["is_malicious_day"].isna().any():
        raise ValueError("Missing ground-truth labels after alignment.")
    return merged["is_malicious_day"].to_numpy(dtype=int), merged["scenario"].to_numpy(dtype=int)


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    train_df = pd.read_parquet(PROCESSED_DATA_DIR / "train.parquet")
    val_df = pd.read_parquet(PROCESSED_DATA_DIR / "validation.parquet")
    test_df = pd.read_parquet(PROCESSED_DATA_DIR / "test.parquet")
    labels_df = pd.read_parquet(PROCESSED_DATA_DIR / "ground_truth_labels.parquet")
    labels_df["activity_date"] = pd.to_datetime(labels_df["activity_date"]).dt.normalize()

    y_val, scen_val = _align_labels(val_df, labels_df)
    y_test, scen_test = _align_labels(test_df, labels_df)

    configs = {
        "raw_baseline_6": RAW_BASELINE_FEATURES,
        "full_engineered_20": FULL_ENGINEERED_FEATURES,
    }

    trained_models = {}
    val_scores_map = {}
    val_eval_map = {}

    for name, feat_cols in configs.items():
        t_fit = time.perf_counter()
        model = train_isolation_forest(
            train_df[feat_cols],
            n_estimators=200,
            max_samples=256,
            contamination="auto",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        fit_sec = round(time.perf_counter() - t_fit, 3)

        val_scores = score_anomalies(model, val_df[feat_cols])
        val_metrics = evaluate_anomaly_scores(
            y_val,
            val_scores,
            scenarios=scen_val,
            top_k_list=(100, 250, 500, 1000),
        )
        val_metrics["fit_seconds"] = fit_sec
        val_metrics["feature_count"] = len(feat_cols)

        trained_models[name] = model
        val_scores_map[name] = val_scores
        val_eval_map[name] = val_metrics

    # Select winner strictly on validation PR-AUC (tiebreak: ROC-AUC)
    selected_name = max(
        configs.keys(),
        key=lambda k: (val_eval_map[k]["pr_auc"], val_eval_map[k]["roc_auc"]),
    )
    selected_model = trained_models[selected_name]
    selected_features = configs[selected_name]
    selected_val_scores = val_scores_map[selected_name]

    # Calibrate candidate thresholds strictly on validation
    thresholds = calibrate_thresholds_on_validation(y_val, selected_val_scores)

    # Evaluate selected model on validation & held-out test using calibrated thresholds
    val_threshold_results = {
        t_name: evaluate_anomaly_scores(
            y_val, selected_val_scores, scenarios=scen_val, threshold=t_val
        )["threshold_eval"]
        for t_name, t_val in thresholds.items()
    }

    test_scores = score_anomalies(selected_model, test_df[selected_features])
    test_eval_base = evaluate_anomaly_scores(
        y_test,
        test_scores,
        scenarios=scen_test,
        top_k_list=(100, 250, 500, 1000),
    )
    test_threshold_results = {
        t_name: evaluate_anomaly_scores(
            y_test, test_scores, scenarios=scen_test, threshold=t_val
        )["threshold_eval"]
        for t_name, t_val in thresholds.items()
    }

    # Save winning model bundle
    model_path = MODELS_DIR / "isolation_forest_v1.joblib"
    save_model_bundle(
        model=selected_model,
        feature_names=selected_features,
        metadata={
            "model_name": selected_name,
            "algorithm": "IsolationForest",
            "scaled": False,
            "n_estimators": 200,
            "max_samples": 256,
            "contamination": "auto",
            "random_state": RANDOM_SEED,
            "calibrated_thresholds": thresholds,
            "validation_roc_auc": val_eval_map[selected_name]["roc_auc"],
            "validation_pr_auc": val_eval_map[selected_name]["pr_auc"],
            "test_roc_auc": test_eval_base["roc_auc"],
            "test_pr_auc": test_eval_base["pr_auc"],
        },
        output_path=model_path,
    )

    # Plot 1: Validation ROC & PR comparison (6-feature vs 20-feature)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for name, label in [
        ("raw_baseline_6", "Raw Baseline (6 features)"),
        ("full_engineered_20", "Full Engineered (20 features)"),
    ]:
        sc = val_scores_map[name]
        fpr, tpr, _ = roc_curve(y_val, sc)
        prec, rec, _ = precision_recall_curve(y_val, sc)
        ax1.plot(fpr, tpr, label=f"{label} (AUC={val_eval_map[name]['roc_auc']:.4f})")
        ax2.plot(rec, prec, label=f"{label} (AP={val_eval_map[name]['pr_auc']:.4f})")

    ax1.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax1.set_title("Validation ROC Curve (Ablation)")
    ax1.set_xlabel("False Positive Rate")
    ax1.set_ylabel("True Positive Rate")
    ax1.legend()

    ax2.axhline(y_val.mean(), color="k", linestyle="--", alpha=0.5, label=f"Base rate ({y_val.mean():.4f})")
    ax2.set_title("Validation Precision-Recall Curve (Ablation)")
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precision")
    ax2.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "06_phase2_pr_roc_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Plot 2: Held-out Test Score Distribution (Normal vs Malicious Days)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(test_scores[y_test == 0], bins=60, density=True, alpha=0.65, label="Non-Malicious Days", color="#2b5c8f")
    ax.hist(test_scores[y_test == 1], bins=30, density=True, alpha=0.70, label="Malicious Days (r4.2)", color="#c0504d")
    ax.axvline(thresholds["top_1pct_threshold"], color="black", linestyle="--", label=f"Val Top-1% Threshold ({thresholds['top_1pct_threshold']:.4f})")
    ax.set_title(f"Held-Out Test Anomaly Score Distribution ({selected_name})")
    ax.set_xlabel("Anomaly Score (-decision_function)")
    ax.set_ylabel("Density")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "07_phase2_test_score_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    elapsed_sec = round(time.perf_counter() - t0, 3)

    report = {
        "phase": 2,
        "elapsed_seconds": elapsed_sec,
        "selected_model": selected_name,
        "model_artifact": str(model_path.relative_to(PROJECT_ROOT)),
        "validation_ablation": val_eval_map,
        "validation_calibrated_thresholds": {k: round(v, 6) for k, v in thresholds.items()},
        "validation_threshold_evaluations": val_threshold_results,
        "held_out_test_evaluation": {
            **test_eval_base,
            "threshold_evaluations": test_threshold_results,
        },
    }
    (METRICS_DIR / "phase2_evaluation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

