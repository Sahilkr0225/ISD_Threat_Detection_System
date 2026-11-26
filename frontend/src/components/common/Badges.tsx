import { Info } from "lucide-react";
import type { AlertStatus, PriorityLevel } from "../../types/api";

const PRIORITY_STYLES: Record<PriorityLevel, string> = {
  Critical: "bg-red-500/15 text-red-400 border-red-500/30",
  High: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  Medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  Low: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  Informational: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};

const STATUS_STYLES: Record<AlertStatus, string> = {
  OPEN: "bg-red-500/15 text-red-300 border-red-500/30",
  UNDER_REVIEW: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  RESOLVED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  DISMISSED: "bg-slate-600/20 text-slate-300 border-slate-500/30",
};

export function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex items-center align-middle">
      <button
        type="button"
        aria-label={text}
        className="ml-1 rounded text-[#94A3B8] hover:text-[#38BDF8] focus:outline-none focus:ring-1 focus:ring-[#38BDF8]"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full left-1/2 z-40 mb-1.5 w-64 -translate-x-1/2 rounded-lg border border-[#263244] bg-[#0B1120] p-2.5 text-[11px] font-normal leading-relaxed text-[#E2E8F0] shadow-xl group-hover:visible group-focus-within:visible"
      >
        {text}
      </span>
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: PriorityLevel | string }) {
  const cls =
    PRIORITY_STYLES[priority as PriorityLevel] ??
    "bg-slate-500/15 text-slate-300 border-slate-500/30";
  return (
    <span
      title="Investigation Priority: indicates how unusual the activity is, not confirmed malicious intent."
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {priority}
    </span>
  );
}

export function StatusBadge({ status }: { status: AlertStatus | string }) {
  const cls =
    STATUS_STYLES[status as AlertStatus] ??
    "bg-slate-600/20 text-slate-300 border-slate-500/30";
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

export function RiskBar({ riskScore }: { riskScore: number }) {
  const clamped = Math.max(0, Math.min(100, riskScore));
  const barColor =
    clamped >= 99
      ? "bg-red-500"
      : clamped >= 98
      ? "bg-orange-500"
      : clamped >= 88
      ? "bg-amber-400"
      : "bg-[#38BDF8]";

  return (
    <div
      className="flex items-center gap-2"
      title="Anomaly Percentile: ranking relative to validation scores — not a probability of malicious behaviour."
    >
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#0B1120]">
        <div className={`h-full ${barColor}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="font-mono text-xs text-[#E2E8F0]">{clamped.toFixed(2)}%</span>
    </div>
  );
}
