import { useCallback, useEffect, useState } from "react";
import { Database, ShieldCheck } from "lucide-react";
import { fetchDataSummary } from "../api/data";
import { fetchHealth } from "../api/dashboard";
import { fetchModelInfo } from "../api/model";
import { extractApiErrorMessage } from "../api/client";
import { ErrorState, LoadingSkeleton } from "../components/common/FeedbackStates";
import type { DataSummaryResponse, HealthResponse, ModelInfoResponse } from "../types/api";
import { formatDateStr, formatNumber } from "../utils/formatters";

export default function DatasetSystem() {
  const [dataSummary, setDataSummary] = useState<DataSummaryResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    Promise.all([fetchDataSummary(signal), fetchModelInfo(signal), fetchHealth(signal)])
      .then(([d, m, h]) => {
        setDataSummary(d);
        setModelInfo(m);
        setHealth(h);
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

  if (loading) return <LoadingSkeleton rows={6} />;
  if (error || !dataSummary || !modelInfo || !health) {
    return <ErrorState message={error ?? "Unable to load system info."} onRetry={() => loadData()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold text-[#E2E8F0]">
          <Database className="h-5 w-5 text-[#38BDF8]" /> Dataset & System Provenance
        </h1>
        <p className="text-xs text-[#94A3B8]">{dataSummary.note}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-3">
          <h2 className="text-sm font-semibold text-[#E2E8F0]">Imported Dataset Coverage</h2>
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Source Partition</div>
              <div className="font-mono text-[#E2E8F0]">{dataSummary.source_partition}</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Imported Employees</div>
              <div className="font-mono text-[#E2E8F0]">{formatNumber(dataSummary.unique_employees)}</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Imported Observations</div>
              <div className="font-mono text-[#E2E8F0]">{formatNumber(dataSummary.observation_count)}</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Coverage Period</div>
              <div className="font-mono text-[#E2E8F0]">
                {formatDateStr(dataSummary.date_min)} to {formatDateStr(dataSummary.date_max)} ({dataSummary.unique_dates} days)
              </div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Persisted Alerts</div>
              <div className="font-mono text-[#E2E8F0]">{formatNumber(dataSummary.alert_count)}</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Persisted Explanations</div>
              <div className="font-mono text-[#E2E8F0]">{formatNumber(dataSummary.explanation_count)}</div>
            </div>
          </div>
          <div className="text-xs text-[#94A3B8] space-y-1 pt-1">
            <p><strong className="text-[#E2E8F0]">Provenance:</strong> Derived from simulated CERT Insider Threat Dataset r4.2 (DOI: 10.1184/R1/12841247.v1) via Zenodo Record 19435851.</p>
            <p><strong className="text-[#E2E8F0]">Chronological Partitions (Full 330,452 rows):</strong> Train (208,167) · Validation (60,812) · Held-Out Test (61,473).</p>
          </div>
        </div>

        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-[#E2E8F0]">
            <ShieldCheck className="h-4 w-4 text-emerald-400" /> System & Governance Limitations
          </h2>
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Backend Status</div>
              <div className="text-emerald-300 font-medium">{health.status.toUpperCase()} (Phase {health.phase})</div>
            </div>
            <div className="rounded bg-[#0B1120] p-2.5">
              <div className="text-[#94A3B8]">Active Model</div>
              <div className="font-mono text-[#38BDF8]">{modelInfo.model_version}</div>
            </div>
          </div>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-[#94A3B8]">
            <li>This is a historical analysis prototype using simulated CERT r4.2 data—not connected to live employee monitoring.</li>
            <li>Anomaly percentiles prioritize analyst review; they are not probabilities of malicious intent.</li>
            <li>Behavioural explanations require human review and contextual verification.</li>
            <li>Authentication and Role-Based Access Control (RBAC) are not yet implemented; bound to localhost for academic demonstration.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

