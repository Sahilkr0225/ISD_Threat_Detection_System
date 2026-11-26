# Causal Behavioural Explainability

**Implementation:** `backend/app/explainability/explainer.py`

## Methodology
1. **Non-Redundant Primary Activities:** Evaluates the 6 primary observable activity counts (`login_count`, `after_hours_login_count`, `http_activity_count`, `email_activity_count`, `file_activity_count`, `usb_activity_count`).
2. **Causal 14-Observation Baseline:** Uses up to the preceding `14` active employee observations (`prior_observations[-14:]`), strictly excluding the current observation and inactive calendar days.
3. **Stabilized Deviation:**
   $$\text{deviation} = \frac{x_t - \mu_{\text{past}}}{\max(\sigma_{\text{past}}, 1.0)}$$
4. **Direction-Aware Deterministic Templates (`build_direction_aware_text`):**
   - **Increased (`dev > 0.25`):** Reports higher-than-usual volume and recommends verifying business justification / authorization.
   - **Decreased or Zero (`dev < -0.25`):** Explicitly distinguishes `0` recorded activity from reduced activity and recommends checking work-pattern changes or logging completeness (never assuming deleted/stolen data).
   - **Near Baseline (`-0.25 <= dev <= 0.25`):** Notes consistency with recent baseline.
   - **Insufficient History (`< 3` prior active observations):** Returns `historical_mean=None`, `historical_std=None`, `direction="insufficient_history"`, and communicates baseline unavailability.
5. **Non-Accusatory Evidence:** Explanations are contextual deviations—**not** exact Isolation Forest tree attributions and **never** assertions of malicious intent.
