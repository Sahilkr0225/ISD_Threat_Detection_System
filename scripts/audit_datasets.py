"""Memory-efficient independent audit of raw Parquet datasets."""

from __future__ import annotations

import gc
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import (
    FEATURE_MATRIX_V1_PATH,
    MASTER_BEHAVIORAL_PATH,
    METRICS_DIR,
)


def _find_candidate_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    for c in columns:
        cl = c.lower()
        if any(cand.lower() in cl for cand in candidates):
            return c
    return None


def audit_parquet_file(path: Path) -> Dict[str, Any]:
    """Audit a single Parquet file without retaining the DataFrame in memory."""
    if not path.exists():
        raise FileNotFoundError(f"Missing Parquet file: {path}")

    file_size_bytes = path.stat().st_size
    parquet_meta = pq.read_metadata(path)
    arrow_schema = pq.read_schema(path)

    df = pd.read_parquet(path)
    row_count, col_count = df.shape
    memory_bytes = int(df.memory_usage(deep=True).sum())

    emp_col = _find_candidate_column(list(df.columns), ["employee_id", "user_id", "user", "emp_id"])
    date_col = _find_candidate_column(list(df.columns), ["activity_date", "date", "day", "timestamp"])

    unique_employees = int(df[emp_col].nunique(dropna=True)) if emp_col else None
    date_info: Dict[str, Any] = {}
    emp_day_counts: Dict[str, Any] = {}

    if date_col:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        valid_dates = parsed_dates.dropna()
        date_info = {
            "column": date_col,
            "unique_dates": int(valid_dates.dt.date.nunique()),
            "min_date": str(valid_dates.min().date()) if not valid_dates.empty else None,
            "max_date": str(valid_dates.max().date()) if not valid_dates.empty else None,
            "unparseable_dates": int(parsed_dates.isna().sum() - df[date_col].isna().sum()),
        }

    dup_rows = int(df.duplicated().sum())
    dup_emp_date = None
    if emp_col and date_col:
        dup_emp_date = int(df.duplicated(subset=[emp_col, date_col]).sum())
        counts_per_emp = df.groupby(emp_col).size()
        emp_day_counts = {
            "min_obs_per_emp": int(counts_per_emp.min()),
            "median_obs_per_emp": float(counts_per_emp.median()),
            "mean_obs_per_emp": round(float(counts_per_emp.mean()), 2),
            "max_obs_per_emp": int(counts_per_emp.max()),
        }

    missing_summary = {
        col: int(cnt) for col, cnt in df.isna().sum().items() if int(cnt) > 0
    }

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    inf_summary: Dict[str, int] = {}
    negative_summary: Dict[str, int] = {}
    numeric_stats: Dict[str, Dict[str, float]] = {}

    for col in numeric_cols:
        series = df[col]
        inf_cnt = int(np.isinf(series.to_numpy(dtype=float, na_value=np.nan)).sum())
        if inf_cnt > 0:
            inf_summary[col] = inf_cnt

        neg_cnt = int((series < 0).sum())
        if neg_cnt > 0:
            negative_summary[col] = neg_cnt

        clean = series.replace([np.inf, -np.inf], np.nan).dropna()
        if not clean.empty:
            numeric_stats[col] = {
                "min": round(float(clean.min()), 4),
                "p25": round(float(clean.quantile(0.25)), 4),
                "median": round(float(clean.median()), 4),
                "mean": round(float(clean.mean()), 4),
                "p75": round(float(clean.quantile(0.75)), 4),
                "p99": round(float(clean.quantile(0.99)), 4),
                "max": round(float(clean.max()), 4),
                "std": round(float(clean.std()), 4),
            }

    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    near_constant_cols: Dict[str, float] = {}
    for c in df.columns:
        if c in constant_cols:
            continue
        top_freq = float(df[c].value_counts(normalize=True, dropna=False).iloc[0])
        if top_freq >= 0.999:
            near_constant_cols[c] = round(top_freq, 6)

    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]
    categorical_cardinality = {
        c: {
            "nunique": int(df[c].nunique(dropna=True)),
            "top_values": {str(k): int(v) for k, v in df[c].value_counts(dropna=False).head(5).items()},
        }
        for c in non_numeric_cols
    }

    label_keywords = ("label", "target", "threat", "insider", "malicious", "anomaly", "scenario", "is_mal", "attack")
    potential_label_cols = [
        c for c in df.columns if any(kw in c.lower() for kw in label_keywords) or c.lower() in ("y", "class")
    ]
    label_distributions = {
        c: {str(k): int(v) for k, v in df[c].value_counts(dropna=False).items()}
        for c in potential_label_cols
    }

    psych_keywords = ("ocean", "openness", "conscientious", "extraversion", "agreeable", "neurotic", "psych", "sentiment")
    potential_psych_cols = [c for c in df.columns if any(kw in c.lower() for kw in psych_keywords)]

    report = {
        "file_name": path.name,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 3),
        "parquet_num_row_groups": parquet_meta.num_row_groups,
        "row_count": int(row_count),
        "column_count": int(col_count),
        "memory_usage_mb": round(memory_bytes / (1024 * 1024), 3),
        "columns": list(df.columns),
        "pandas_dtypes": {c: str(dt) for c, dt in df.dtypes.items()},
        "arrow_schema": [f"{field.name}: {field.type}" for field in arrow_schema],
        "employee_column": emp_col,
        "unique_employees": unique_employees,
        "date_info": date_info,
        "employee_day_counts": emp_day_counts,
        "duplicate_rows": dup_rows,
        "duplicate_employee_date_rows": dup_emp_date,
        "missing_values": missing_summary,
        "infinite_values": inf_summary,
        "negative_values": negative_summary,
        "constant_columns": constant_cols,
        "near_constant_columns": near_constant_cols,
        "categorical_cardinality": categorical_cardinality,
        "potential_label_columns": potential_label_cols,
        "label_distributions": label_distributions,
        "potential_psychometric_or_sentiment_columns": potential_psych_cols,
        "numeric_stats": numeric_stats,
    }

    del df
    gc.collect()
    return report


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    master_report = audit_parquet_file(MASTER_BEHAVIORAL_PATH)
    v1_report = audit_parquet_file(FEATURE_MATRIX_V1_PATH)

    master_cols = set(master_report["columns"])
    v1_cols = set(v1_report["columns"])
    comparison = {
        "shared_columns": sorted(master_cols & v1_cols),
        "only_in_master": sorted(master_cols - v1_cols),
        "only_in_feature_matrix_v1": sorted(v1_cols - master_cols),
    }

    full_report = {
        "master_behavioral_matrix": master_report,
        "feature_matrix_v1": v1_report,
        "comparison": comparison,
    }

    out_path = METRICS_DIR / "dataset_audit_report.json"
    out_path.write_text(json.dumps(full_report, indent=2), encoding="utf-8")

    print(f"Audit report saved to: {out_path}")
    for key in ("master_behavioral_matrix", "feature_matrix_v1"):
        r = full_report[key]
        print(f"\n=== {r['file_name']} ===")
        print(f"Size: {r['file_size_mb']} MB | Rows: {r['row_count']} | Cols: {r['column_count']} | Mem: {r['memory_usage_mb']} MB")
        print(f"Emp col: {r['employee_column']} (unique: {r['unique_employees']}) | Date info: {r['date_info']}")
        print(f"Duplicates: rows={r['duplicate_rows']}, emp-date={r['duplicate_employee_date_rows']}")
        print(f"Missing cols: {len(r['missing_values'])} | Inf cols: {len(r['infinite_values'])} | Neg cols: {len(r['negative_values'])}")
        print(f"Potential labels: {r['potential_label_columns']} -> {r['label_distributions']}")
        print(f"Columns ({len(r['columns'])}): {r['columns']}")


if __name__ == "__main__":
    main()

