import { useCallback, useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchModelInfo, fetchModelMetrics } from "../api/model";
import { extractApiErrorMessage } from "../api/client";
import { ErrorState, LoadingSkeleton } from "../components/common/FeedbackStates";
import type { ModelInfoResponse, ModelMetricsResponse } from "../types/api";
import { formatNumber, formatPctFromRatio, formatScore } from "../utils/formatters";

const POLICY_LABELS: Record<string, string> = {
  f1_optimal_threshold: "F1-Optimized (Default Queue)",
  sklearn_default_zero_threshold: "Scikit-Learn Zero Boundary",
  top_2pct_threshold: "Top 2% (High/Critical Tier)",
  top_1pct_threshold: "Top 1% (Critical Tier)",
};

export default function ModelEvaluation() {
  const [info, setInfo] = useState<ModelInfoResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<string>("f1_optimal_threshold");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    Promise.all([fetchModelInfo(signal), fetchModelMetrics(signal)])
      .then(([infoRes, metricsRes]) => {
        setInfo(infoRes);
        setMetrics(metricsRes);
      })
      .catch((err) => {
        if ((err as { name?: string }).name === "CanceledError") return;
        setError(extractApiErrorMessage(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  if (loading) return <LoadingSkeleton rows={8} />;
  if (error || !info || !metrics) {
    return <ErrorState message={error ?? "Unable to load model metrics."} onRetry={() => loadData()} />;
  }

  const raw6 = metrics.validation_ablation.raw_baseline_6;
  const eng20 = metrics.validation_ablation.full_engineered_20;

  const rocData = [
    { name: "Raw Baseline (6)", value: raw6?.roc_auc ?? 0, fill: "#64748b" },
    { name: "Engineered (20)", value: eng20?.roc_auc ?? 0, fill: "#38BDF8" },
  ];

  const apData = [
    { name: "Raw Baseline (6)", value: raw6?.pr_auc ?? 0, fill: "#64748b" },
    { name: "Engineered (20)", value: eng20?.pr_auc ?? 0, fill: "#38BDF8" },
  ];

  const valEval = metrics.validation_threshold_metrics[selectedPolicy];
  const testEval = metrics.held_out_test_threshold_metrics[selectedPolicy];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold text-[#E2E8F0]">
          <BarChart3 className="h-5 w-5 text-[#38BDF8]" /> AI Model Performance &amp; Ablation
        </h1>
        <p className="text-xs text-[#94A3B8]">
          Offline Phase 2 evaluation on frozen chronological splits (Research Evaluation Only — changing thresholds here does not alter operational alerts)
        </p>
      </div>

      {/* Low Precision Disclaimer */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-200">
        <strong>Scientific Interpretation:</strong> ROC-AUC measures ranking separation across thresholds—never classification accuracy. Because malicious employee-days are rare ({formatPctFromRatio(metrics.held_out_test_summary.base_positive_rate, 3)} test prevalence), unsupervised precision is low (0.37%–1.20%), requiring human analyst triage.
      </div>

      {/* Model Config & Ranking Metrics */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-3">
          <h2 className="text-sm font-semibold text-[#E2E8F0]">Selected Unsupervised Model</h2>
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Model Identifier</div>
              <div className="font-mono text-[#38BDF8]">{info.model_version}</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Algorithm</div>
              <div className="text-[#E2E8F0]">{info.algorithm} (Unscaled)</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Hyperparameters</div>
              <div className="font-mono text-[#E2E8F0]">
                trees={info.hyperparameters.n_estimators}, max_samples={info.hyperparameters.max_samples}, seed={info.hyperparameters.random_state}
              </div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Approved Features</div>
              <div className="font-mono text-[#E2E8F0]">{info.feature_count} causal features</div>
            </div>
          </div>
          <p className="text-[11px] text-[#94A3B8]">
            Fitted exclusively on train.parquet (208,167 rows) with zero ground-truth labels supplied during training.
          </p>
        </div>

        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-3">
          <h2 className="text-sm font-semibold text-[#E2E8F0]">Threshold-Independent Ranking Metrics</h2>
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Validation ROC-AUC</div>
              <div className="font-mono text-base font-semibold text-[#E2E8F0]">
                {eng20?.roc_auc.toFixed(4)}
              </div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Held-Out Test ROC-AUC</div>
              <div className="font-mono text-base font-semibold text-[#38BDF8]">
                {metrics.held_out_test_summary.roc_auc.toFixed(4)}
              </div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Test Avg Precision / PR-AUC</div>
              <div className="font-mono text-sm text-[#E2E8F0]">
                AP: {metrics.held_out_test_summary.average_precision.toFixed(4)} · Trap:{" "}
                {metrics.held_out_test_summary.trapezoidal_pr_auc?.toFixed(4) ?? "—"}
              </div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Test Prevalence</div>
              <div className="font-mono text-sm text-[#E2E8F0]">
                {metrics.held_out_test_summary.n_positives} / {formatNumber(metrics.held_out_test_summary.n_samples)} (
                {formatPctFromRatio(metrics.held_out_test_summary.base_positive_rate, 3)})
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Ablation with Separate Scales */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-4">
        <h2 className="text-sm font-semibold text-[#E2E8F0]">
          Validation Feature Ablation: Raw Baseline (6) vs. Engineered (20)
        </h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
            <h3 className="text-xs font-semibold text-[#E2E8F0]">Validation ROC-AUC (Scale: 0.75 – 0.95)</h3>
            <div className="mt-2 h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rocData} margin={{ top: 18 }}>
                  <CartesianGrid stroke="#263244" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <YAxis domain={[0.75, 0.95]} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B1120",
                      borderColor: "#263244",
                      color: "#E2E8F0",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" name="Validation ROC-AUC" radius={[4, 4, 0, 0]}>
                    {rocData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                    <LabelList dataKey="value" position="top" fill="#E2E8F0" fontSize={11} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
            <h3 className="text-xs font-semibold text-[#E2E8F0]">Validation Average Precision (Scale: 0.00 – 0.025)</h3>
            <div className="mt-2 h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={apData} margin={{ top: 18 }}>
                  <CartesianGrid stroke="#263244" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <YAxis domain={[0, 0.025]} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B1120",
                      borderColor: "#263244",
                      color: "#E2E8F0",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" name="Validation Average Precision" radius={[4, 4, 0, 0]}>
                    {apData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                    <LabelList dataKey="value" position="top" fill="#E2E8F0" fontSize={11} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Threshold Policy Comparison */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[#E2E8F0]">
              Interactive Threshold Policy Comparison (Validation vs. Held-Out Test)
            </h2>
            <p className="text-xs text-[#94A3B8]">
              Research evaluation only — does not modify operational alerts or database records
            </p>
          </div>
          <select
            aria-label="Threshold policy"
            value={selectedPolicy}
            onChange={(e) => setSelectedPolicy(e.target.value)}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-1.5 text-xs text-[#E2E8F0]"
          >
            {Object.entries(POLICY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {[
            { title: "Validation Partition (60,812 rows)", data: valEval },
            { title: "Held-Out Test Partition (61,473 rows)", data: testEval },
          ].map(({ title, data }) => (
            <div key={title} className="rounded-lg border border-[#263244] bg-[#0B1120] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-[#E2E8F0]">{title}</h3>
                <span className="font-mono text-[11px] text-[#38BDF8]">
                  Threshold: {formatScore(data?.threshold, 6)}
                </span>
              </div>
              {data && (
                <>
                  <div className="grid grid-cols-2 gap-2 text-center text-xs">
                    <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2">
                      <div className="text-[11px] text-emerald-300">True Positives (TP)</div>
                      <div className="font-mono text-base font-semibold text-[#E2E8F0]">
                        {formatNumber(data.tp)}
                      </div>
                    </div>
                    <div className="rounded border border-amber-500/30 bg-amber-500/10 p-2">
                      <div className="text-[11px] text-amber-300">False Positives (FP)</div>
                      <div className="font-mono text-base font-semibold text-[#E2E8F0]">
                        {formatNumber(data.fp)}
                      </div>
                    </div>
                    <div className="rounded border border-red-500/30 bg-red-500/10 p-2">
                      <div className="text-[11px] text-red-300">False Negatives (FN)</div>
                      <div className="font-mono text-base font-semibold text-[#E2E8F0]">
                        {formatNumber(data.fn)}
                      </div>
                    </div>
                    <div className="rounded border border-[#263244] bg-[#151E2E] p-2">
                      <div className="text-[11px] text-[#94A3B8]">True Negatives (TN)</div>
                      <div className="font-mono text-base font-semibold text-[#E2E8F0]">
                        {formatNumber(data.tn)}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>Precision: <strong className="font-mono">{formatPctFromRatio(data.precision)}</strong></div>
                    <div>Recall: <strong className="font-mono">{formatPctFromRatio(data.recall)}</strong></div>
                    <div>F1: <strong className="font-mono">{formatPctFromRatio(data.f1)}</strong></div>
                    <div>FPR: <strong className="font-mono">{formatPctFromRatio(data.fpr)}</strong></div>
                    <div>Alerts: <strong className="font-mono">{formatNumber(data.total_alerts)}</strong></div>
                    <div>Avg/Day: <strong className="font-mono">{data.avg_alerts_per_date}</strong></div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
