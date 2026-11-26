"""Phase 2 Verification & Acceptance Audit Script (Tasks 1, 2, 4, 5, 6)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import auc, confusion_matrix, precision_recall_curve

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
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES
from backend.app.ml.isolation_forest import (
    RAW_BASELINE_FEATURES,
    load_model_bundle,
    score_anomalies,
    train_isolation_forest,
)


def _detailed_threshold_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    n_unique_dates: int,
) -> dict:
    y_pred = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    total = len(y_true)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    alerts = int(tp + fp)
    return {
        "threshold": round(float(threshold), 6),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "fpr": round(float(fpr), 4),
        "specificity": round(float(specificity), 4),
        "total_alerts": alerts,
        "alert_rate_pct": round(100.0 * alerts / total, 4),
        "avg_alerts_per_date": round(alerts / n_unique_dates, 2),
    }


def main() -> None:
    train_df = pd.read_parquet(PROCESSED_DATA_DIR / "train.parquet")
    val_df = pd.read_parquet(PROCESSED_DATA_DIR / "validation.parquet")
    test_df = pd.read_parquet(PROCESSED_DATA_DIR / "test.parquet")
    labels_df = pd.read_parquet(PROCESSED_DATA_DIR / "ground_truth_labels.parquet")
    labels_df["activity_date"] = pd.to_datetime(labels_df["activity_date"]).dt.normalize()

    # --- Task 1: Ground-truth mapping audit ---
    gt_audit = {}
    mal_emp_ids = set(labels_df.loc[labels_df["is_malicious_day"] == 1, "employee_id"].unique())
    mal_emp_all_rows = labels_df[labels_df["employee_id"].isin(mal_emp_ids)]
    gt_audit["unique_malicious_employees_overall"] = len(mal_emp_ids)
    gt_audit["malicious_employees_total_days_in_dataset"] = int(len(mal_emp_all_rows))
    gt_audit["malicious_employees_malicious_days"] = int((mal_emp_all_rows["is_malicious_day"] == 1).sum())
    gt_audit["malicious_employees_benign_days"] = int((mal_emp_all_rows["is_malicious_day"] == 0).sum())

    split_emp_counts = {}
    for s_name, s_df in [("train", train_df), ("validation", val_df), ("test", test_df)]:
        keys = s_df[["employee_id", "activity_date"]].copy()
        keys["activity_date"] = pd.to_datetime(keys["activity_date"]).dt.normalize()
        m = keys.merge(labels_df, on=["employee_id", "activity_date"], how="left")
        split_emp_counts[s_name] = {
            "unique_malicious_employees": int(m.loc[m["is_malicious_day"] == 1, "employee_id"].nunique()),
            "malicious_days": int((m["is_malicious_day"] == 1).sum()),
            "unique_dates": int(keys["activity_date"].nunique()),
        }
    gt_audit["per_split_counts"] = split_emp_counts

    # --- Task 5: Reload model bundle & verify ---
    bundle = load_model_bundle(MODELS_DIR / "isolation_forest_v1.joblib")
    model = bundle["model"]
    feat_names = bundle["feature_names"]
    meta = bundle["metadata"]
    thresholds = meta["calibrated_thresholds"]

    # Score validation & test
    val_scores = score_anomalies(model, val_df[feat_names])
    test_scores = score_anomalies(model, test_df[feat_names])

    # --- Task 4: Score relationship verification ---
    sample_X = test_df[feat_names].iloc[:500].to_numpy(dtype=np.float64)
    dec_fn = model.decision_function(sample_X)
    sc_samp = model.score_samples(sample_X)
    max_offset_diff = float(np.max(np.abs(dec_fn - (sc_samp - model.offset_))))

    # Align labels
    def align(df: pd.DataFrame) -> np.ndarray:
        k = df[["employee_id", "activity_date"]].copy()
        k["activity_date"] = pd.to_datetime(k["activity_date"]).dt.normalize()
        return k.merge(labels_df, on=["employee_id", "activity_date"], how="left")["is_malicious_day"].to_numpy(dtype=int)

    y_val = align(val_df)
    y_test = align(test_df)

    # --- Task 2: Exact confusion matrix metrics + trapezoidal PR-AUC ---
    p_val, r_val, _ = precision_recall_curve(y_val, val_scores)
    p_test, r_test, _ = precision_recall_curve(y_test, test_scores)

    val_detailed = {
        k: _detailed_threshold_metrics(y_val, val_scores, v, split_emp_counts["validation"]["unique_dates"])
        for k, v in thresholds.items()
    }
    test_detailed = {
        k: _detailed_threshold_metrics(y_test, test_scores, v, split_emp_counts["test"]["unique_dates"])
        for k, v in thresholds.items()
    }

    # Confusion matrix figure (2x2 on held-out test)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for ax, (t_name, m) in zip(axes.flat, test_detailed.items()):
        cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(f"{t_name}\n(thr={m['threshold']:.4f}, Recall={m['recall']:.2%})")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred Normal", "Pred Alert"])
        ax.set_yticklabels(["Actual Normal", "Actual Malicious"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", color="black", fontsize=11)
    fig.suptitle("Held-Out Test Confusion Matrices Across Validation-Calibrated Thresholds", fontsize=13)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "08_phase2_confusion_matrices.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Task 6a: Save validation & test prediction artifacts ---
    def save_preds(df: pd.DataFrame, scores: np.ndarray, out_name: str) -> None:
        out = df[["employee_id", "activity_date"]].copy()
        out["anomaly_score"] = scores
        for t_name, t_val in thresholds.items():
            out[f"pred_{t_name}"] = (scores >= t_val).astype(int)
        out.to_parquet(PROCESSED_DATA_DIR / out_name, index=False)

    save_preds(val_df, val_scores, "validation_predictions.parquet")
    save_preds(test_df, test_scores, "test_predictions.parquet")

    # --- Task 6b: Controlled behavioural diagnostic scenarios (synthetic, separate from CERT) ---
    med_row = train_df[feat_names].median().to_dict()
    diag_normal = dict(med_row)
    diag_after_hours_usb = dict(med_row)
    diag_after_hours_usb.update({
        "login_count": 6,
        "after_hours_login_count": 5,
        "after_hours_ratio": 5 / 6,
        "usb_activity_count": 15,
        "log_usb_activity": float(np.log1p(15)),
        "after_hours_hist_dev_14obs": 5.0,
        "usb_hist_dev_14obs": 12.0,
    })
    diag_file_spike = dict(med_row)
    diag_file_spike.update({
        "file_activity_count": 35,
        "log_file_activity": float(np.log1p(35)),
        "file_hist_dev_14obs": 15.0,
    })
    diag_df = pd.DataFrame([diag_normal, diag_after_hours_usb, diag_file_spike])[feat_names]
    diag_scores = score_anomalies(model, diag_df)
    diagnostics = [
        {"scenario": "baseline_median_day", "anomaly_score": round(float(diag_scores[0]), 6)},
        {"scenario": "synthetic_after_hours_usb_burst", "anomaly_score": round(float(diag_scores[1]), 6)},
        {"scenario": "synthetic_file_access_spike", "anomaly_score": round(float(diag_scores[2]), 6)},
    ]

    # --- Task 6c: Model agreement on validation (raw_baseline_6 vs full_engineered_20) ---
    raw_model = train_isolation_forest(
        train_df[RAW_BASELINE_FEATURES],
        n_estimators=200,
        max_samples=256,
        contamination="auto",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    raw_val_scores = score_anomalies(raw_model, val_df[RAW_BASELINE_FEATURES])
    spearman_corr = float(pd.Series(val_scores).corr(pd.Series(raw_val_scores), method="spearman"))
    top1pct_full = set(np.argsort(-val_scores)[:608])
    top1pct_raw = set(np.argsort(-raw_val_scores)[:608])
    jaccard_top1pct = len(top1pct_full & top1pct_raw) / len(top1pct_full | top1pct_raw)

    audit_report = {
        "task1_ground_truth_audit": gt_audit,
        "task2_exact_metrics": {
            "validation_trapezoidal_pr_auc": round(float(auc(r_val, p_val)), 4),
            "test_trapezoidal_pr_auc": round(float(auc(r_test, p_test)), 4),
            "validation_thresholds": val_detailed,
            "test_thresholds": test_detailed,
        },
        "task4_score_semantics": {
            "offset_": float(model.offset_),
            "max_abs_diff_decision_vs_score_samples_minus_offset": max_offset_diff,
        },
        "task5_model_bundle": {
            "bundle_keys": list(bundle.keys()),
            "sklearn_version": sklearn.__version__,
            "model_params": {
                "n_estimators": model.n_estimators,
                "max_samples": model.max_samples,
                "contamination": model.contamination,
                "random_state": model.random_state,
            },
            "feature_count": len(feat_names),
            "matches_approved_features_exact_order": feat_names == APPROVED_MODEL_FEATURES,
            "metadata": meta,
        },
        "task6_diagnostics_and_agreement": {
            "controlled_diagnostics": diagnostics,
            "validation_spearman_raw6_vs_eng20": round(spearman_corr, 4),
            "validation_top1pct_jaccard_raw6_vs_eng20": round(jaccard_top1pct, 4),
        },
    }

    out_path = METRICS_DIR / "phase2_verification_audit.json"
    out_path.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    print(json.dumps(audit_report, indent=2))


if __name__ == "__main__":
    main()

