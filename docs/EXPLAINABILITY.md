# Causal Behavioural Explainability

**Implementation:** `backend/app/explainability/explainer.py`

## Methodology
1. **Non-Redundant Primary Activities:** Evaluates the 6 primary observable activity counts (`login_count`, `after_hours_login_count`, `http_activity_count`, `email_activity_count`, `file_activity_count`, `usb_activity_count`) to avoid duplicate explanations for correlated/log-transformed features.
2. **Causal 14-Observation Baseline:** Uses up to the preceding `14` active employee observations (`prior_observations[-14:]`), strictly excluding the current observation.
3. **Stabilized Deviation:** For each activity with at least `3` prior observations:
   $$\text{deviation} = \frac{x_t - \mu_{\text{past}}}{\max(\sigma_{\text{past}}, 1.0)}$$
4. **Insufficient History Handling:** When fewer than `3` prior observations exist, `historical_mean`, `historical_std`, and `stabilized_deviation` are returned as `null`, and `direction` is `"insufficient_history"`. Historical statistics are never fabricated.
5. **Non-Accusatory Evidence:** Explanations describe statistical deviations (e.g., unusual removable-device usage) and investigation recommendations. They are **not** exact Isolation Forest tree-path attributions and **never** assert malicious intent or confirmed data theft.

