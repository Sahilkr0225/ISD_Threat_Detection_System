"""Causal, evidence-based behavioural explainability engine.

Explanations are derived strictly from the employee's current observation and
preceding 14 recorded active observations (excluding the current observation)
using the same stabilized denominator floor (1.0) as feature engineering.

Note: These are observable behavioural deviation explanations, NOT exact
Isolation Forest tree-path attributions, and NEVER assertions of malicious intent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

EPSILON = 1.0
MIN_HISTORY_OBS = 3
MAX_HISTORY_WINDOW = 14

EXPLAINABLE_ACTIVITIES: Tuple[Tuple[str, str, str], ...] = (
    ("login_count", "Logon Activity", "logons"),
    ("after_hours_login_count", "After-Hours Logon Activity", "after-hours logons"),
    ("http_activity_count", "Web Activity", "web activities"),
    ("email_activity_count", "Email Activity", "email activities"),
    ("file_activity_count", "File Access Activity", "file activities"),
    ("usb_activity_count", "USB / Removable-Device Activity", "USB activities"),
)

_RECOMMENDATIONS_ABOVE: Dict[str, str] = {
    "login_count": "Verify whether the elevated logon count aligns with authorized work schedules, travel, or credential resets.",
    "after_hours_login_count": "Verify whether access outside regular working hours was authorized for an active task or on-call shift.",
    "http_activity_count": "Review available web-access logs and confirm business justification for the increased web activity.",
    "email_activity_count": "Review available communication metadata and verify business justification for the increased email volume.",
    "file_activity_count": "Review authorized file access and available file-operation records for this employee.",
    "usb_activity_count": "Review authorized removable-device usage and available endpoint device records.",
}

_RECOMMENDATIONS_BELOW: Dict[str, str] = {
    "login_count": "Verify whether the employee's schedule changed or logon records are incomplete.",
    "after_hours_login_count": "Reduced or absent after-hours activity compared to baseline; typically benign unless paired with other anomalies.",
    "http_activity_count": "Check whether the employee's work assignment changed and whether web activity logs are complete.",
    "email_activity_count": "Verify whether communication patterns changed or email activity records are incomplete.",
    "file_activity_count": "Check whether work responsibilities or file-activity recording coverage changed.",
    "usb_activity_count": "Check work-pattern changes and removable-device logging completeness.",
}

_RECOMMENDATION_NEAR_BASELINE = (
    "Activity is consistent with the employee's recent baseline; prioritize stronger deviations during review."
)
_RECOMMENDATION_INSUFFICIENT = (
    "Review alongside employee role and other available activity context, as historical baseline data is limited."
)


@dataclass
class BehaviouralExplanation:
    """Structured evidence-based deviation explanation for one activity dimension."""

    feature_name: str
    activity_label: str
    current_value: float
    historical_mean: Optional[float]
    historical_std: Optional[float]
    stabilized_deviation: Optional[float]
    direction: str
    historical_obs_count: int
    evidence_description: str
    investigation_recommendation: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def build_direction_aware_text(
    feature_name: str,
    activity_label: str,
    current_value: float,
    historical_mean: Optional[float],
    historical_std: Optional[float],
    stabilized_deviation: Optional[float],
    direction: str,
    historical_obs_count: int,
    after_hours_ratio: Optional[float] = None,
) -> Tuple[str, str]:
    """Deterministically build plain-language evidence and direction-aware recommendation."""
    unit_noun = dict((f, u) for f, _, u in EXPLAINABLE_ACTIVITIES).get(feature_name, "activities")

    if direction == "insufficient_history" or historical_mean is None or stabilized_deviation is None:
        evidence = (
            f"{activity_label} recorded at {current_value:.0f}. Insufficient prior observations "
            f"({historical_obs_count} of {MIN_HISTORY_OBS} required) to establish a personal baseline."
        )
        return evidence, _RECOMMENDATION_INSUFFICIENT

    mean_approx = f"{historical_mean:.0f}" if historical_mean >= 10 else f"{historical_mean:.2f}"
    extra_ah = ""
    if feature_name == "after_hours_login_count" and after_hours_ratio is not None:
        extra_ah = f" ({float(after_hours_ratio):.0%} of recorded logins)"

    if direction == "above_baseline":
        evidence = (
            f"{activity_label} ({current_value:.0f}){extra_ah} was higher than usual; "
            f"the employee normally records approximately {mean_approx} {unit_noun} per active observation."
        )
        rec = _RECOMMENDATIONS_ABOVE.get(feature_name, _RECOMMENDATION_INSUFFICIENT)
        return evidence, rec

    if direction == "below_baseline":
        if current_value == 0:
            evidence = (
                f"No {unit_noun} were recorded (0), although the employee normally records "
                f"approximately {mean_approx} {unit_noun} per active observation."
            )
        else:
            evidence = (
                f"{activity_label} ({current_value:.0f}) was lower than usual; "
                f"the employee normally records approximately {mean_approx} {unit_noun} per active observation."
            )
        rec = _RECOMMENDATIONS_BELOW.get(feature_name, _RECOMMENDATION_INSUFFICIENT)
        return evidence, rec

    # near_baseline
    evidence = (
        f"{activity_label} ({current_value:.0f}) remained close to the employee's usual level "
        f"(approximately {mean_approx} {unit_noun} per active observation)."
    )
    return evidence, _RECOMMENDATION_NEAR_BASELINE


def generate_behavioural_explanations(
    current_observation: Mapping[str, float],
    prior_observations: Sequence[Mapping[str, float]],
    top_n: int = 3,
) -> List[BehaviouralExplanation]:
    """Generate top-N causal behavioural explanations without fabricating missing history."""
    window_history = list(prior_observations[-MAX_HISTORY_WINDOW:])
    hist_count = len(window_history)

    explanations: List[BehaviouralExplanation] = []
    ah_ratio = current_observation.get("after_hours_ratio")

    for feat_name, label, _ in EXPLAINABLE_ACTIVITIES:
        curr_val = float(current_observation[feat_name])

        if hist_count < MIN_HISTORY_OBS:
            evidence, recommendation = build_direction_aware_text(
                feature_name=feat_name,
                activity_label=label,
                current_value=curr_val,
                historical_mean=None,
                historical_std=None,
                stabilized_deviation=None,
                direction="insufficient_history",
                historical_obs_count=hist_count,
                after_hours_ratio=float(ah_ratio) if ah_ratio is not None else None,
            )
            explanations.append(
                BehaviouralExplanation(
                    feature_name=feat_name,
                    activity_label=label,
                    current_value=curr_val,
                    historical_mean=None,
                    historical_std=None,
                    stabilized_deviation=None,
                    direction="insufficient_history",
                    historical_obs_count=hist_count,
                    evidence_description=evidence,
                    investigation_recommendation=recommendation,
                )
            )
            continue

        hist_vals = np.array([float(obs[feat_name]) for obs in window_history], dtype=np.float64)
        hist_mean = float(np.mean(hist_vals))
        hist_std = float(np.std(hist_vals, ddof=0))
        denom = max(hist_std, EPSILON)
        dev = float((curr_val - hist_mean) / denom)

        if dev > 0.25:
            direction = "above_baseline"
        elif dev < -0.25:
            direction = "below_baseline"
        else:
            direction = "near_baseline"

        evidence, recommendation = build_direction_aware_text(
            feature_name=feat_name,
            activity_label=label,
            current_value=curr_val,
            historical_mean=hist_mean,
            historical_std=hist_std,
            stabilized_deviation=dev,
            direction=direction,
            historical_obs_count=hist_count,
            after_hours_ratio=float(ah_ratio) if ah_ratio is not None else None,
        )

        explanations.append(
            BehaviouralExplanation(
                feature_name=feat_name,
                activity_label=label,
                current_value=curr_val,
                historical_mean=round(hist_mean, 4),
                historical_std=round(hist_std, 4),
                stabilized_deviation=round(dev, 4),
                direction=direction,
                historical_obs_count=hist_count,
                evidence_description=evidence,
                investigation_recommendation=recommendation,
            )
        )

    explanations.sort(
        key=lambda e: abs(e.stabilized_deviation) if e.stabilized_deviation is not None else -1.0,
        reverse=True,
    )
    return explanations[: max(1, top_n)]
