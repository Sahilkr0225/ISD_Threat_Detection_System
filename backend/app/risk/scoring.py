"""Validation-reference percentile risk scoring and priority classification."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple, Union

import numpy as np

PRIORITY_LEVELS: Tuple[str, ...] = (
    "Critical",
    "High",
    "Medium",
    "Low",
    "Informational",
)


class RiskScorer:
    """Maps raw Isolation Forest anomaly scores to 0-100 prioritization percentiles.

    Uses a frozen, sorted validation anomaly score distribution so that
    scores are deterministic, monotonic, bounded in [0, 100], and independent
    of test data or incoming request batch size.

    Note: The output `risk_score` is an anomaly prioritization percentile,
    NOT a probability of malicious intent.
    """

    def __init__(self, reference_scores: Union[np.ndarray, Sequence[float]]) -> None:
        arr = np.asarray(reference_scores, dtype=np.float64)
        if arr.ndim != 1 or arr.size == 0:
            raise ValueError("Reference anomaly score distribution must be a non-empty 1D array.")
        if not np.isfinite(arr).all():
            raise ValueError("Reference anomaly score distribution contains NaN or infinite values.")
        self._sorted_ref = np.sort(arr)
        self._n = int(self._sorted_ref.size)

    @classmethod
    def from_npy(cls, path: Union[str, Path]) -> "RiskScorer":
        """Load frozen validation reference scores from a .npy file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Validation score reference file not found: {p}")
        return cls(np.load(p))

    @property
    def reference_size(self) -> int:
        return self._n

    def score_to_risk(self, anomaly_score: float) -> float:
        """Compute exact 0-100 percentile risk score for a single anomaly score."""
        if not np.isfinite(anomaly_score):
            raise ValueError("anomaly_score must be finite.")
        rank = int(np.searchsorted(self._sorted_ref, anomaly_score, side="right"))
        return float(100.0 * (rank / self._n))

    def scores_to_risk(self, anomaly_scores: Union[np.ndarray, Sequence[float]]) -> np.ndarray:
        """Vectorized 0-100 percentile risk scoring for a batch of anomaly scores."""
        arr = np.asarray(anomaly_scores, dtype=np.float64)
        if not np.isfinite(arr).all():
            raise ValueError("anomaly_scores contain NaN or infinite values.")
        ranks = np.searchsorted(self._sorted_ref, arr, side="right")
        return 100.0 * (ranks / self._n)


class PriorityClassifier:
    """Classifies raw anomaly scores into investigation priority tiers."""

    def __init__(self, thresholds: Mapping[str, float]) -> None:
        required = (
            "top_1pct_threshold",
            "top_2pct_threshold",
            "sklearn_default_zero_threshold",
            "f1_optimal_threshold",
        )
        missing = [k for k in required if k not in thresholds]
        if missing:
            raise ValueError(f"Missing required threshold(s): {', '.join(missing)}")

        self.critical_thr = float(thresholds["top_1pct_threshold"])
        self.high_thr = float(thresholds["top_2pct_threshold"])
        self.medium_thr = float(thresholds["sklearn_default_zero_threshold"])
        self.low_thr = float(thresholds["f1_optimal_threshold"])

        if not (self.critical_thr >= self.high_thr >= self.medium_thr >= self.low_thr):
            raise ValueError(
                "Thresholds must be ordered: "
                "top_1pct >= top_2pct >= sklearn_default_zero >= f1_optimal."
            )

    def classify(self, anomaly_score: float) -> str:
        """Classify a single raw anomaly score into an investigation priority tier."""
        if not np.isfinite(anomaly_score):
            raise ValueError("anomaly_score must be finite.")
        if anomaly_score >= self.critical_thr:
            return "Critical"
        if anomaly_score >= self.high_thr:
            return "High"
        if anomaly_score >= self.medium_thr:
            return "Medium"
        if anomaly_score >= self.low_thr:
            return "Low"
        return "Informational"

    def is_alert(self, priority: str) -> bool:
        """Return True if the priority falls inside the F1-optimized investigation queue."""
        return priority in ("Critical", "High", "Medium", "Low")

    def as_dict(self) -> Dict[str, float]:
        """Return exact threshold policy boundaries."""
        return {
            "Critical": self.critical_thr,
            "High": self.high_thr,
            "Medium": self.medium_thr,
            "Low": self.low_thr,
        }

