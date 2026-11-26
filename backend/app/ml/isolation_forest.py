"""Unsupervised Isolation Forest training, scoring, and Joblib persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.app.core.config import RANDOM_SEED
from backend.app.features.feature_engineering import (
    APPROVED_MODEL_FEATURES,
    OBSERVABLE_ACTIVITY_FEATURES,
)

RAW_BASELINE_FEATURES: List[str] = list(OBSERVABLE_ACTIVITY_FEATURES)
FULL_ENGINEERED_FEATURES: List[str] = list(APPROVED_MODEL_FEATURES)


def train_isolation_forest(
    X_train: Union[pd.DataFrame, np.ndarray],
    n_estimators: int = 200,
    max_samples: Union[int, str] = 256,
    contamination: Union[float, str] = "auto",
    max_features: float = 1.0,
    random_state: int = RANDOM_SEED,
    n_jobs: int = -1,
) -> IsolationForest:
    """Fit an unscaled Isolation Forest strictly on training feature matrix X_train.

    Note:
        Isolation Forest uses random axis-aligned tree splits and does not
        require feature scaling. Ground-truth labels are never passed here.
    """
    if len(X_train) == 0:
        raise ValueError("X_train must not be empty.")

    arr = X_train.to_numpy(dtype=np.float64) if isinstance(X_train, pd.DataFrame) else np.asarray(X_train, dtype=np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("X_train contains NaN or infinite values.")

    effective_max_samples = min(max_samples, len(arr)) if isinstance(max_samples, int) else max_samples

    model = IsolationForest(
        n_estimators=n_estimators,
        max_samples=effective_max_samples,
        contamination=contamination,
        max_features=max_features,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    model.fit(arr)
    return model


def score_anomalies(
    model: IsolationForest,
    X: Union[pd.DataFrame, np.ndarray],
) -> np.ndarray:
    """Compute continuous anomaly scores where higher values indicate stronger anomalies.

    Scikit-learn's `decision_function` returns positive values for inliers and
    negative values for outliers; negating it yields an intuitive anomaly score.
    """
    arr = X.to_numpy(dtype=np.float64) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("Input feature matrix contains NaN or infinite values.")
    return -model.decision_function(arr)


def save_model_bundle(
    model: IsolationForest,
    feature_names: Sequence[str],
    metadata: Dict[str, Any],
    output_path: Union[str, Path],
) -> Path:
    """Persist trained Isolation Forest model, feature schema, and metadata via Joblib."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_names": list(feature_names),
        "metadata": dict(metadata),
    }
    joblib.dump(bundle, out, compress=3)
    return out


def load_model_bundle(model_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a persisted Isolation Forest model bundle."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model bundle not found: {path}")
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "model" not in bundle or "feature_names" not in bundle:
        raise ValueError(f"Invalid model bundle structure in: {path}")
    return bundle

