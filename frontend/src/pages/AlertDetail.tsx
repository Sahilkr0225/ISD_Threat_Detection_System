import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Info,
  Play,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchAlertDetail, fetchAlertHistory, updateAlertStatus } from "../api/alerts";
import { extractApiErrorMessage } from "../api/client";
import { InfoTooltip, PriorityBadge, StatusBadge } from "../components/common/Badges";
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from "../components/common/FeedbackStates";
import { useToast } from "../components/common/ToastContext";
import { useAuth } from "../context/AuthContext";
import type {
  AlertDetailResponse,
  AlertStatus,
  InvestigationHistoryItem,
} from "../types/api";
import {
  formatDateStr,
  formatPctFromRatio,
  formatScore,
  formatTimestamp,
} from "../utils/formatters";

function buildDynamicPlainSummary(detail: AlertDetailResponse): string {
  const parts: string[] = [];
  const dayNote = detail.is_weekend ? " on a weekend" : "";

  if (detail.after_hours_login_count > 0) {
    parts.push(
      `The employee recorded ${detail.login_count} logon(s), including ${detail.after_hours_login_count} outside regular working hours${dayNote}.`
    );
  } else {
    parts.push(
      `The employee recorded ${detail.login_count} logon(s) during regular hours${dayNote}.`
    );
  }

  const above = detail.explanations.filter((e) => e.direction === "above_baseline");
  const absent = detail.explanations.filter(
    (e) => e.direction === "below_baseline" && e.current_value === 0
  );
  const reduced = detail.explanations.filter(
    (e) => e.direction === "below_baseline" && e.current_value > 0
  );
  const insufficient = detail.explanations.some((e) => e.direction === "insufficient_history");

  if (above.length > 0) {
    const names = above.map((e) => e.activity_label.toLowerCase()).join(", ");
    parts.push(`Higher-than-usual activity was recorded in ${names}.`);
  }
  if (absent.length > 0) {
    const names = absent.map((e) => e.activity_label.toLowerCase()).join(", ");
    parts.push(
      `No ${names} was recorded, despite these activities normally appearing in the employee's recent active observations.`
    );
  }
  if (reduced.length > 0) {
    const names = reduced.map((e) => e.activity_label.toLowerCase()).join(", ");
    parts.push(`Lower-than-usual volume was recorded in ${names}.`);
  }
  if (insufficient && above.length === 0 && absent.length === 0 && reduced.length === 0) {
    parts.push(
      "Personal historical baseline data is limited (fewer than 3 prior active observations), so activity is flagged relative to broader patterns."
    );
  }

  return parts.join(" ");
}

function directionLabel(direction: string, current: number): string {
  if (direction === "above_baseline") return "Higher than usual";
  if (direction === "below_baseline") return current === 0 ? "Absent (0 recorded)" : "Lower than usual";
  if (direction === "near_baseline") return "Near usual level";
  return "Insufficient history";
}

export default function AlertDetail() {
  const { hasRole } = useAuth();
  const canModifyStatus = hasRole("ADMINISTRATOR", "SECURITY_ANALYST");
  const { alertId } = useParams<{ alertId: string }>();
  const numericId = Number(alertId);
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [detail, setDetail] = useState<AlertDetailResponse | null>(null);
  const [history, setHistory] = useState<InvestigationHistoryItem[]>([]);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutating, setMutating] = useState(false);
  const [pendingAction, setPendingAction] = useState<AlertStatus | null>(null);
  const [showTechnical, setShowTechnical] = useState(false);

  const loadAlert = useCallback(
    (signal?: AbortSignal) => {
      if (!Number.isFinite(numericId) || numericId <= 0) {
        setError("Invalid Alert ID.");
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      Promise.all([fetchAlertDetail(numericId, signal), fetchAlertHistory(numericId, signal)])
        .then(([detRes, histRes]) => {
          setDetail(detRes);
          setHistory(histRes.items);
        })
        .catch((err) => {
          if ((err as { name?: string }).name === "CanceledError") return;
          setError(extractApiErrorMessage(err));
        })
        .finally(() => setLoading(false));
    },
    [numericId]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadAlert(controller.signal);
    return () => controller.abort();
  }, [loadAlert]);

  const executeStatusChange = async (newStatus: AlertStatus) => {
    if (!detail) return;
    setMutating(true);
    try {
      const updated = await updateAlertStatus(detail.alert_id, {
        new_status: newStatus,
        analyst_note: note.trim() || null,
      });
      const histRes = await fetchAlertHistory(detail.alert_id);
      setDetail(updated);
      setHistory(histRes.items);
      setNote("");
      addToast(`Alert #${detail.alert_id} updated to ${newStatus.replace("_", " ")}.`, "success");
    } catch (err) {
      addToast(extractApiErrorMessage(err), "error");
    } finally {
      setMutating(false);
      setPendingAction(null);
    }
  };

  if (loading) return <LoadingSkeleton rows={8} />;
  if (error || !detail) {
    return <ErrorState message={error ?? "Alert not found."} onRetry={() => loadAlert()} />;
  }

  const plainSummary = buildDynamicPlainSummary(detail);

  const comparisonData = detail.explanations
    .filter((e) => e.historical_mean !== null)
    .map((e) => ({
      activity: e.activity_label.replace(" Activity", ""),
      "Today's Activity": e.current_value,
      "Usual Activity": Number((e.historical_mean ?? 0).toFixed(2)),
    }));

  // Deduplicated recommended analyst steps based on actual evidence
  const recommendedSteps: string[] = [];
  if (detail.after_hours_login_count > 0) {
    recommendedSteps.push(
      "Verify whether access outside regular working hours was authorized for an active task or maintenance window."
    );
  }
  for (const exp of detail.explanations) {
    if (!recommendedSteps.includes(exp.investigation_recommendation)) {
      recommendedSteps.push(exp.investigation_recommendation);
    }
  }

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={() => navigate("/alerts")}
        className="inline-flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#E2E8F0]"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Suspicious Activity
      </button>

      {/* A. Employee and Alert Summary */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl font-semibold text-[#E2E8F0]">Alert #{detail.alert_id}</h1>
              <span className="inline-flex items-center text-xs text-[#94A3B8]">
                Investigation Priority:
                <InfoTooltip text="Investigation Priority ranks how unusual the activity is under the scoring policy. It is not proof of malicious intent." />
              </span>
              <PriorityBadge priority={detail.priority} />
              <StatusBadge status={detail.status} />
            </div>
            <p className="mt-2 text-xs text-[#94A3B8]">
              Employee:{" "}
              <button
                type="button"
                onClick={() => navigate(`/employees/${detail.employee_id}`)}
                className="font-mono font-medium text-[#38BDF8] hover:underline"
              >
                {detail.employee_id}
              </button>{" "}
              · Role: <strong className="text-[#E2E8F0]">{detail.role ?? "Unknown"}</strong> · Department:{" "}
              <strong className="text-[#E2E8F0]">{detail.department ?? "Unknown"}</strong> · Historical Date:{" "}
              <span className="font-mono text-[#E2E8F0]">{formatDateStr(detail.activity_date)}</span>
            </p>
          </div>
        </div>

        {/* Recorded Activity Counts */}
        <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-7 text-xs">
          {[
            ["Logons", detail.login_count],
            ["After-Hours", `${detail.after_hours_login_count} (${formatPctFromRatio(detail.after_hours_ratio, 0)})`],
            ["Web Activity", detail.http_activity_count],
            ["Emails", detail.email_activity_count],
            ["Files", detail.file_activity_count],
            ["USB", detail.usb_activity_count],
            ["Day Type", detail.is_weekend ? "Weekend" : "Weekday"],
          ].map(([k, v]) => (
            <div key={String(k)} className="rounded-lg border border-[#263244] bg-[#0B1120] p-2.5">
              <div className="text-[11px] text-[#94A3B8]">{k}</div>
              <div className="mt-0.5 font-mono font-semibold text-[#E2E8F0]">{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* B. Why This Alert Requires Attention */}
      <div className="rounded-xl border border-[#38BDF8]/30 bg-[#38BDF8]/10 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-[#E2E8F0]">
          <Info className="h-4 w-4 text-[#38BDF8]" /> Why This Alert Requires Attention
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-[#E2E8F0]">{plainSummary}</p>
        <p className="mt-1.5 text-[11px] text-[#94A3B8]">
          Note: Unusual activity is a statistical prompt for review—it does not establish unauthorized access, data deletion, or malicious intent.
        </p>
      </div>

      {/* C. Unusual Activity Detected & D/E Right Column */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <div>
            <h2 className="text-sm font-semibold text-[#E2E8F0]">Unusual Activity Detected</h2>
            <p className="text-xs text-[#94A3B8]">
              Each card compares today&apos;s recorded count against the employee&apos;s usual average across their previous active observations (excluding inactive calendar days).
            </p>
          </div>

          {detail.explanations.map((exp) => (
            <div
              key={exp.explanation_id}
              className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-[#E2E8F0]">{exp.activity_label}</span>
                <span
                  className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                    exp.direction === "above_baseline"
                      ? "border-amber-500/30 bg-amber-500/15 text-amber-300"
                      : exp.direction === "below_baseline"
                      ? "border-sky-500/30 bg-sky-500/15 text-sky-300"
                      : "border-slate-500/30 bg-slate-500/15 text-slate-300"
                  }`}
                >
                  {directionLabel(exp.direction, exp.current_value)}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2.5 text-xs">
                <div className="rounded bg-[#0B1120] p-2.5">
                  <div className="text-[11px] text-[#94A3B8]">Recorded Activity</div>
                  <div className="mt-0.5 font-mono text-base font-semibold text-[#E2E8F0]">
                    {exp.current_value}
                  </div>
                </div>
                <div className="rounded bg-[#0B1120] p-2.5">
                  <div className="text-[11px] text-[#94A3B8]">
                    Usual Activity ({exp.historical_obs_count} active obs.)
                  </div>
                  <div className="mt-0.5 font-mono text-base font-semibold text-[#E2E8F0]">
                    {exp.historical_mean !== null
                      ? `~${exp.historical_mean >= 10 ? exp.historical_mean.toFixed(0) : exp.historical_mean.toFixed(2)}`
                      : "Baseline unavailable"}
                  </div>
                </div>
                <div className="rounded bg-[#0B1120] p-2.5">
                  <div className="text-[11px] text-[#94A3B8]">Normal Variation (±)</div>
                  <div className="mt-0.5 font-mono text-base font-semibold text-[#E2E8F0]">
                    {exp.historical_std !== null ? exp.historical_std.toFixed(2) : "Unavailable"}
                  </div>
                </div>
              </div>

              <p className="text-xs leading-relaxed text-[#E2E8F0]">
                <strong className="text-[#94A3B8]">Interpretation:</strong> {exp.evidence_description}
              </p>
              <p className="text-xs leading-relaxed text-[#94A3B8]">
                <strong className="text-[#38BDF8]">Recommended Action:</strong> {exp.investigation_recommendation}
              </p>
            </div>
          ))}
        </div>

        {/* Right Column: Chart, D. Recommended Steps, E. Investigation Actions */}
        <div className="space-y-4">
          {comparisonData.length > 0 && (
            <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
              <h3 className="text-sm font-semibold text-[#E2E8F0]">Today vs. Usual Activity</h3>
              <div className="mt-3 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData}>
                    <CartesianGrid stroke="#263244" strokeDasharray="3 3" />
                    <XAxis dataKey="activity" tick={{ fill: "#94A3B8", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0B1120",
                        borderColor: "#263244",
                        color: "#E2E8F0",
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Today's Activity" fill="#38BDF8" />
                    <Bar dataKey="Usual Activity" fill="#64748b" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* D. Recommended Investigation Steps */}
          <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-2">
            <h3 className="text-sm font-semibold text-[#E2E8F0]">Recommended Investigation Steps</h3>
            <p className="text-[11px] text-[#94A3B8]">
              Suggested external analyst checks (these logs are not automatically verified by the prototype):
            </p>
            <ul className="list-disc pl-4 space-y-1.5 text-xs text-[#E2E8F0]">
              {recommendedSteps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ul>
          </div>

          {/* E. Investigation Actions */}
          <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-3">
            <h3 className="text-sm font-semibold text-[#E2E8F0]">Investigation Actions</h3>
            {!canModifyStatus ? (
              <p className="rounded-lg border border-[#263244] bg-[#0B1120] p-3 text-xs text-[#94A3B8]">
                Read-only access ({""}
                <span className="font-semibold text-[#E2E8F0]">AUDITOR</span>): only Administrators and Security Analysts can transition investigation statuses or add notes.
              </p>
            ) : (
              <>
                <textarea
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add analyst investigation note (optional)..."
                  className="w-full rounded-lg border border-[#263244] bg-[#0B1120] p-2.5 text-xs text-[#E2E8F0] placeholder-[#94A3B8] focus:border-[#38BDF8] focus:outline-none"
                />
                <div className="flex flex-wrap gap-2">
                  {(detail.status === "OPEN" || detail.status === "RESOLVED" || detail.status === "DISMISSED") && (
                    <button
                      type="button"
                      disabled={mutating}
                      onClick={() => executeStatusChange("UNDER_REVIEW")}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 border border-amber-500/40 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-amber-500/30 disabled:opacity-50"
                    >
                      <Play className="h-3.5 w-3.5" />
                      {detail.status === "OPEN" ? "Start Investigation" : "Reopen for Review"}
                    </button>
                  )}
                  {(detail.status === "OPEN" || detail.status === "UNDER_REVIEW") && (
                    <>
                      <button
                        type="button"
                        disabled={mutating}
                        onClick={() => setPendingAction("RESOLVED")}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 px-3 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Complete Investigation
                      </button>
                      <button
                        type="button"
                        disabled={mutating}
                        onClick={() => setPendingAction("DISMISSED")}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-slate-600/30 border border-slate-500/40 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-600/50 disabled:opacity-50"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Dismiss Alert
                      </button>
                    </>
                  )}
                </div>
                <p className="text-[11px] text-[#94A3B8]">
                  Completing or dismissing an investigation records an administrative triage decision and does not establish confirmed malicious activity.
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Investigation History Timeline */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-[#E2E8F0]">
          <Clock className="h-4 w-4 text-[#38BDF8]" /> Investigation History
        </h2>
        <div className="mt-3">
          {history.length === 0 ? (
            <EmptyState
              title="No status transitions yet"
              description="Use Investigation Actions above to start, complete, or dismiss this alert."
            />
          ) : (
            <div className="divide-y divide-[#263244]/60 text-xs">
              {history.map((h) => (
                <div key={h.history_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={h.previous_status} />
                    <span className="text-[#94A3B8]">→</span>
                    <StatusBadge status={h.new_status} />
                    <span className="text-[#94A3B8]">
                      by{" "}
                      <span className="text-[#E2E8F0]">
                        {h.actor_display_name ?? h.actor_username ?? "Legacy / Unauthenticated"}
                      </span>
                    </span>
                    {h.analyst_note && <span className="text-[#E2E8F0]">“{h.analyst_note}”</span>}
                  </div>
                  <span className="text-[#94A3B8]">{formatTimestamp(h.changed_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* F. Advanced Technical Details (Collapsed by Default) */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E]">
        <button
          type="button"
          onClick={() => setShowTechnical((s) => !s)}
          aria-expanded={showTechnical}
          className="flex w-full items-center justify-between px-4 py-3 text-left text-xs font-semibold text-[#94A3B8] hover:text-[#E2E8F0]"
        >
          <span>Advanced Technical Details (Historical Behavioural Deviation Analysis)</span>
          {showTechnical ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>

        {showTechnical && (
          <div className="border-t border-[#263244] p-4 space-y-4 text-xs">
            <p className="text-[11px] text-[#94A3B8]">
              These statistical metrics provide contextual evidence from historical behavioural deviation analysis—not exact Isolation Forest tree attribution or proof of causation. Anomaly percentile is a ranking relative to validation scores, not a probability of malicious behaviour.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded bg-[#0B1120] p-3">
                <div className="text-[#94A3B8]">Raw Anomaly Score (-decision_function)</div>
                <div className="mt-1 font-mono text-sm text-[#E2E8F0]">{formatScore(detail.anomaly_score, 6)}</div>
              </div>
              <div className="rounded bg-[#0B1120] p-3">
                <div className="text-[#94A3B8]">Validation Anomaly Percentile</div>
                <div className="mt-1 font-mono text-sm text-[#38BDF8]">{detail.risk_score.toFixed(2)}%</div>
              </div>
              <div className="rounded bg-[#0B1120] p-3">
                <div className="text-[#94A3B8]">Model Version</div>
                <div className="mt-1 font-mono text-sm text-[#E2E8F0]">{detail.model_version}</div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263244] text-[#94A3B8]">
                  <tr>
                    <th className="py-2 pr-3">Feature</th>
                    <th className="py-2 pr-3">Current</th>
                    <th className="py-2 pr-3">Hist Mean</th>
                    <th className="py-2 pr-3">Hist Std</th>
                    <th className="py-2 pr-3">Stabilized Dev</th>
                    <th className="py-2">Prior Active Obs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263244]/60 font-mono">
                  {detail.explanations.map((e) => (
                    <tr key={e.explanation_id}>
                      <td className="py-2 pr-3 text-[#38BDF8]">{e.feature_name}</td>
                      <td className="py-2 pr-3">{e.current_value}</td>
                      <td className="py-2 pr-3">{e.historical_mean !== null ? e.historical_mean.toFixed(4) : "null"}</td>
                      <td className="py-2 pr-3">{e.historical_std !== null ? e.historical_std.toFixed(4) : "null"}</td>
                      <td className="py-2 pr-3">{e.deviation !== null ? e.deviation.toFixed(4) : "null"}</td>
                      <td className="py-2">{e.historical_obs_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={pendingAction !== null}
        title={`Confirm ${pendingAction === "RESOLVED" ? "Complete Investigation" : "Dismiss Alert"}`}
        message={`Mark Alert #${detail.alert_id} as ${pendingAction}? This appends an entry to the investigation history and does not assert confirmed malicious activity.`}
        confirmLabel={pendingAction === "RESOLVED" ? "Complete Investigation" : "Dismiss Alert"}
        busy={mutating}
        onCancel={() => setPendingAction(null)}
        onConfirm={() => pendingAction && executeStatusChange(pendingAction)}
      />
    </div>
  );
}
