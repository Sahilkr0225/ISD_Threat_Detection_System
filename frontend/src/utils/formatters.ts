export function formatNumber(val: number | null | undefined, decimals = 0): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return val.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatScore(val: number | null | undefined, decimals = 4): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return val.toFixed(decimals);
}

export function formatPercentile(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return `${val.toFixed(2)}%`;
}

export function formatPctFromRatio(val: number | null | undefined, decimals = 2): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}

/** Preserve YYYY-MM-DD historical dates without timezone shifting. */
export function formatDateStr(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return dateStr.slice(0, 10);
}

export function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

