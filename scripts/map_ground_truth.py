"""Map CERT r4.2 ground-truth labels onto processed splits (stored separately from features)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import METRICS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from backend.app.data.ground_truth import extract_r42_ground_truth_days


def main() -> None:
    answers_path = RAW_DATA_DIR / "answers.tar.bz2"
    gt_days, meta = extract_r42_ground_truth_days(answers_path)

    cleaned_keys = pd.read_parquet(
        PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet",
        columns=["employee_id", "activity_date"],
    )
    cleaned_keys["activity_date"] = pd.to_datetime(cleaned_keys["activity_date"]).dt.normalize()

    merged = cleaned_keys.merge(
        gt_days,
        on=["employee_id", "activity_date"],
        how="left",
    )
    merged["is_malicious_day"] = merged["is_malicious_day"].fillna(0).astype("int64")
    merged["scenario"] = merged["scenario"].fillna(0).astype("int64")
    merged["malicious_event_count"] = merged["malicious_event_count"].fillna(0).astype("int64")

    labels_out = PROCESSED_DATA_DIR / "ground_truth_labels.parquet"
    merged.to_parquet(labels_out, index=False)

    # Check matched vs unmatched employee-days
    matched_keys = merged[merged["is_malicious_day"] == 1][["employee_id", "activity_date"]]
    unmatched = gt_days.merge(matched_keys, on=["employee_id", "activity_date"], how="left", indicator=True)
    unmatched_count = int((unmatched["_merge"] == "left_only").sum())

    split_counts = {}
    for split_name in ("train", "validation", "test"):
        s_keys = pd.read_parquet(
            PROCESSED_DATA_DIR / f"{split_name}.parquet",
            columns=["employee_id", "activity_date"],
        )
        s_keys["activity_date"] = pd.to_datetime(s_keys["activity_date"]).dt.normalize()
        s_merged = s_keys.merge(
            merged, on=["employee_id", "activity_date"], how="left"
        )
        pos = int(s_merged["is_malicious_day"].sum())
        split_counts[split_name] = {
            "total_rows": int(len(s_merged)),
            "malicious_days": pos,
            "malicious_rate_pct": round(100.0 * pos / len(s_merged), 4),
            "scenario_counts": {
                str(k): int(v)
                for k, v in s_merged[s_merged["is_malicious_day"] == 1]["scenario"]
                .value_counts()
                .sort_index()
                .items()
            },
        }

    summary = {
        "source_archive": str(answers_path.name),
        "extraction_meta": meta,
        "matched_malicious_days_in_dataset": int(merged["is_malicious_day"].sum()),
        "unmatched_malicious_days": unmatched_count,
        "split_ground_truth_distribution": split_counts,
    }
    (METRICS_DIR / "ground_truth_mapping_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

