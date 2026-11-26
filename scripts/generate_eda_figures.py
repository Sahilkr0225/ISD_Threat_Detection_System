"""Generate reproducible EDA figures from cleaned behavioural data."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import FIGURES_DIR, MASTER_BEHAVIORAL_PATH, PROCESSED_DATA_DIR


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    cleaned_path = PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet"
    df = pd.read_parquet(cleaned_path)

    # 1. Activity distributions (histograms on log1p scale for skewed counts)
    activity_cols = [
        ("login_count", "Daily Login Count"),
        ("after_hours_login_count", "After-Hours Login Count"),
        ("http_activity_count", "HTTP Activity Count"),
        ("email_activity_count", "Email Activity Count"),
        ("file_activity_count", "File Activity Count"),
        ("usb_activity_count", "USB Activity Count"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    for ax, (col, title) in zip(axes.flat, activity_cols):
        vals = df[col].to_numpy(dtype=float)
        if col in ("http_activity_count", "file_activity_count", "usb_activity_count"):
            ax.hist(np.log1p(vals), bins=35, color="#2b5c8f", edgecolor="white", alpha=0.88)
            ax.set_xlabel(f"log1p({col})")
        else:
            ax.hist(vals, bins=30, color="#2b5c8f", edgecolor="white", alpha=0.88)
            ax.set_xlabel(col)
        ax.set_title(title)
        ax.set_ylabel("Employee-Days")
    fig.suptitle("Observable Employee-Day Activity Distributions (N = 330,452)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_activity_distributions.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 2. Daily activity trend over time (daily mean across employees)
    daily_trend = (
        df.groupby("activity_date")[
            ["login_count", "after_hours_login_count", "file_activity_count", "usb_activity_count"]
        ]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(daily_trend["activity_date"], daily_trend["login_count"], label="Mean Logins", linewidth=1.3)
    ax.plot(daily_trend["activity_date"], daily_trend["after_hours_login_count"], label="Mean After-Hours Logins", linewidth=1.3)
    ax.plot(daily_trend["activity_date"], daily_trend["file_activity_count"], label="Mean File Events", linewidth=1.3)
    ax.plot(daily_trend["activity_date"], daily_trend["usb_activity_count"], label="Mean USB Events", linewidth=1.3)
    ax.set_title("Mean Daily Observable Activity Over Time (2010-01-02 to 2011-05-17)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mean Events per Active Employee")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_daily_activity_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 3. Correlation heatmap of observable activity features
    corr_cols = [c for c, _ in activity_cols]
    corr = df[corr_cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True, ax=ax)
    ax.set_title("Correlation Matrix of Observable Activity Features")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_feature_correlation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 4. Outlier / tail boxplot (50,000 deterministic sample for fast plotting)
    sample_df = df[corr_cols].sample(n=min(50000, len(df)), random_state=42)
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.boxplot(data=np.log1p(sample_df), orient="h", ax=ax, color="#4c84b8")
    ax.set_title("Log-Scaled Activity Distributions & Upper-Tail Outliers (n = 50,000 Sample)")
    ax.set_xlabel("log1p(count)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_outlier_boxplots.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 5. Missing values in raw master_behavioral_matrix.parquet
    raw_meta = pd.read_parquet(MASTER_BEHAVIORAL_PATH, columns=["role", "department", "functional_unit", "total_logon_activity"])
    miss_pct = (raw_meta.isna().mean() * 100.0).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    miss_pct.plot(kind="bar", color="#c0504d", ax=ax)
    ax.set_title("Missing Value Percentage in Raw master_behavioral_matrix.parquet")
    ax.set_ylabel("Missing (%)")
    ax.set_xlabel("Column (All Other 13 Columns Have 0% Missing)")
    plt.xticks(rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_missing_values_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Generated 5 EDA figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()

