"""Run Phase 1 cleaning, feature engineering, chronological splitting, and manifest export."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import tracemalloc

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import (
    MASTER_BEHAVIORAL_PATH,
    METRICS_DIR,
    PROCESSED_DATA_DIR,
    RANDOM_SEED,
)
from backend.app.data.loader import load_dataset
from backend.app.data.preprocessing import chronological_split, clean_behavioral_data
from backend.app.features.feature_engineering import (
    APPROVED_MODEL_FEATURES,
    EXCLUDED_COLUMNS_RATIONALE,
    engineer_behavioral_features,
    get_feature_manifest,
)


def main() -> None:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    tracemalloc.start()
    t0 = time.perf_counter()

    raw_df = load_dataset(MASTER_BEHAVIORAL_PATH)
    cleaned_df, cleaning_summary = clean_behavioral_data(raw_df)
    del raw_df

    cleaned_path = PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet"
    cleaned_df.to_parquet(cleaned_path, index=False)

    features_df = engineer_behavioral_features(cleaned_df)
    del cleaned_df

    features_path = PROCESSED_DATA_DIR / "engineered_features.parquet"
    features_df.to_parquet(features_path, index=False)

    train_df, val_df, test_df, split_manifest = chronological_split(features_df)
    del features_df

    train_df.to_parquet(PROCESSED_DATA_DIR / "train.parquet", index=False)
    val_df.to_parquet(PROCESSED_DATA_DIR / "validation.parquet", index=False)
    test_df.to_parquet(PROCESSED_DATA_DIR / "test.parquet", index=False)

    elapsed_sec = round(time.perf_counter() - t0, 3)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    split_manifest["approved_model_features"] = APPROVED_MODEL_FEATURES
    split_manifest["random_seed"] = RANDOM_SEED

    feature_manifest = {
        "approved_features": get_feature_manifest(),
        "excluded_columns": EXCLUDED_COLUMNS_RATIONALE,
    }

    timing_info = {
        "pipeline_elapsed_seconds": elapsed_sec,
        "peak_traced_memory_mb": round(peak_bytes / (1024 * 1024), 2),
    }

    (METRICS_DIR / "cleaning_summary.json").write_text(
        json.dumps(cleaning_summary.to_dict(), indent=2), encoding="utf-8"
    )
    (METRICS_DIR / "feature_manifest.json").write_text(
        json.dumps(feature_manifest, indent=2), encoding="utf-8"
    )
    (METRICS_DIR / "split_manifest.json").write_text(
        json.dumps(split_manifest, indent=2), encoding="utf-8"
    )
    (METRICS_DIR / "pipeline_timing.json").write_text(
        json.dumps(timing_info, indent=2), encoding="utf-8"
    )

    print(f"Phase 1 pipeline completed in {elapsed_sec}s (peak traced mem: {timing_info['peak_traced_memory_mb']} MB)")
    print(f"Splits: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
    print(f"Approved model features ({len(APPROVED_MODEL_FEATURES)}): {APPROVED_MODEL_FEATURES}")


if __name__ == "__main__":
    main()

