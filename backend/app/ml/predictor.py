"""Production inference service for the persisted Isolation Forest bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Union

import numpy as np
import pandas as pd

from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES
from backend.app.ml.isolation_forest import load_model_bundle, score_anomalies


class ModelInferenceError(ValueError):
    """Raised when model loading or input feature validation fails."""


class ModelPredictor:
    """Thread-safe wrapper around the persisted Isolation Forest model bundle."""

    def __init__(self, bundle_path: Union[str, Path]) -> None:
        self._bundle_path = Path(bundle_path)
        bundle = load_model_bundle(self._bundle_path)

        self.model = bundle["model"]
        self.feature_names: List[str] = list(bundle["feature_names"])
        self.metadata: Dict[str, Any] = dict(bundle.get("metadata", {}))

        if self.feature_names != list(APPROVED_MODEL_FEATURES):
            raise ModelInferenceError(
                "Model bundle feature_names do not match APPROVED_MODEL_FEATURES."
            )

        thresholds = self.metadata.get("calibrated_thresholds")
        if not isinstance(thresholds, Mapping) or not thresholds:
            raise ModelInferenceError(
                "Model bundle metadata is missing calibrated_thresholds."
            )
        self.calibrated_thresholds: Dict[str, float] = {
            str(k): float(v) for k, v in thresholds.items()
        }
        self.model_version: str = str(self.metadata.get("model_name", "isolation_forest_v1"))

    def validate_and_extract_matrix(
        self,
        records: Union[pd.DataFrame, Sequence[Mapping[str, Any]]],
    ) -> np.ndarray:
        """Validate feature names, ordering, numeric types, and finiteness."""
        if isinstance(records, pd.DataFrame):
            df = records
        else:
            if not records:
                raise ModelInferenceError("Input batch must not be empty.")
            df = pd.DataFrame(list(records))

        if df.empty:
            raise ModelInferenceError("Input DataFrame must not be empty.")

        missing = [c for c in self.feature_names if c not in df.columns]
        if missing:
            raise ModelInferenceError(f"Missing required model feature(s): {', '.join(missing)}")

        ordered_df = df[self.feature_names]
        for col in self.feature_names:
            if pd.api.types.is_bool_dtype(ordered_df[col]):
                raise ModelInferenceError(f"Feature '{col}' must be numeric, got boolean.")

        try:
            arr = ordered_df.to_numpy(dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ModelInferenceError(f"Non-numeric value encountered in features: {exc}") from exc

        if not np.isfinite(arr).all():
            raise ModelInferenceError("Input features contain NaN or infinite values.")

        return arr

    def predict_batch(
        self,
        records: Union[pd.DataFrame, Sequence[Mapping[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Run batch inference and return anomaly scores and estimator-default flags."""
        arr = self.validate_and_extract_matrix(records)
        scores = score_anomalies(self.model, arr)
        return [
            {
                "anomaly_score": float(s),
                "estimator_default_is_anomaly": bool(s >= 0.0),
            }
            for s in scores
        ]

    def predict_single(self, features: Mapping[str, Any]) -> Dict[str, Any]:
        """Run single-observation inference from a feature dictionary."""
        extra_keys = set(features.keys()) - set(self.feature_names)
        if extra_keys:
            raise ModelInferenceError(
                f"Unexpected non-model field(s) in feature vector: {sorted(extra_keys)}"
            )
        return self.predict_batch([features])[0]

