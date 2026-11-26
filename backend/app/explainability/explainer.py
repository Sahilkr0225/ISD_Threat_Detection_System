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

# Evaluate only the 6 primary non-redundant observable activity dimensions
EXPLAINABLE_ACTIVITIES: Tuple[Tuple[str, str, str], ...] = (
    (
        "login_count",
        "Daily Logon Activity",
        "Verify whether the employee had scheduled system maintenance, travel, or credential resets.",
    ),
    (
        "after_hours_login_count",
        "After-Hours Logon Activity",
        "Check if after-hours work was authorized for an active project deadline or on-call shift.",
    ),
    (
        "http_activity_count",
        "Web / HTTP Activity",
        "Review proxy or web-access logs for unusual browsing volume or automated tool traffic.",
    ),
    (
        "email_activity_count",
        "Email Activity",
        "Review email volume trends and verify whether bulk communications were business-related.",
    ),
    (
        "file_activity_count",
        "File Access Activity",
        "Check accessed directories and confirm whether elevated file activity aligns with job duties.",
    ),
    (
        "usb_activity_count",
        "USB / Removable Device Activity",
        "Unusual removable-device usage; verify business justification and endpoint device policy.",
    ),
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


def generate_behavioural_explanations(
    current_observation: Mapping[str, float],
    prior_observations: Sequence[Mapping[str, float]],
    top_n: int = 3,
) -> List[BehaviouralExplanation]:
    """Generate top-N causal behavioural explanations without fabricating missing history.

    Args:
        current_observation: Current employee-day observable counts (and optional after_hours_ratio).
        prior_observations: Preceding observations for the same employee, ordered chronologically
            (strictly excluding the current observation). Up to the most recent 14 are used.
        top_n: Maximum number of explanations to return, ranked by |stabilized_deviation|.
    """
    window_history = list(prior_observations[-MAX_HISTORY_WINDOW:])
    hist_count = len(window_history)

    explanations: List[BehaviouralExplanation] = []
    ah_ratio = current_observation.get("after_hours_ratio")

    for feat_name, label, recommendation in EXPLAINABLE_ACTIVITIES:
        curr_val = float(current_observation[feat_name])

        if hist_count < MIN_HISTORY_OBS:
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
                    evidence_description=(
                        f"{label} observed at {curr_val:.0f}. Insufficient prior history "
                        f"({hist_count} of {MIN_HISTORY_OBS} required prior observations) "
                        f"to establish a personal baseline."
                    ),
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
            dir_text = "above"
        elif dev < -0.25:
            direction = "below_baseline"
            dir_text = "below"
        else:
            direction = "near_baseline"
            dir_text = "near"

        extra_context = ""
        if feat_name == "after_hours_login_count" and ah_ratio is not None:
            extra_context = f" (after-hours ratio: {float(ah_ratio):.1%})"

        evidence = (
            f"{label} count ({curr_val:.0f}){extra_context} is {abs(dev):.2f} stabilized historical deviation "
            f"{dir_text} the employee's {hist_count}-observation baseline "
            f"(mean {hist_mean:.2f}, std {hist_std:.2f})."
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

    # Sort strongest deviations first; if insufficient history, preserve primary activity order
    explanations.sort(
        key=lambda e: abs(e.stabilized_deviation) if e.stabilized_deviation is not None else -1.0,
        reverse=True,
    )
    return explanations[: max(1, top_n)]

