import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClipboardCheck, Eye } from "lucide-react";
import { fetchAlerts } from "../api/alerts";
import { extractApiErrorMessage } from "../api/client";
import { PriorityBadge, RiskBar, StatusBadge } from "../components/common/Badges";
import { EmptyState, ErrorState, LoadingSkeleton, Pagination } from "../components/common/FeedbackStates";
import type { AlertStatus, AlertSummaryItem, PaginationMeta } from "../types/api";
import { formatDateStr, formatTimestamp } from "../utils/formatters";

export default function Investigations() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<AlertStatus>("UNDER_REVIEW");
  const [items, setItems] = useState<AlertSummaryItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: 1,
    page_size: 25,
    total: 0,
    total_pages: 1,
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      fetchAlerts({ status: statusFilter, page, page_size: 25 }, signal)
        .then((res) => {
          setItems(res.items);
          setPagination(res.pagination);
        })
        .catch((err) => {
          if ((err as { name?: string }).name === "CanceledError") return;
          setError(extractApiErrorMessage(err));
        })
        .finally(() => setLoading(false));
    },
    [statusFilter, page]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-[#E2E8F0]">
            <ClipboardCheck className="h-5 w-5 text-[#38BDF8]" /> Investigations Workspace
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Track alerts currently under analyst review, resolved, or dismissed
          </p>
        </div>

        <div className="flex gap-2">
          {(["UNDER_REVIEW", "RESOLVED", "DISMISSED"] as AlertStatus[]).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                statusFilter === st
                  ? "border-[#38BDF8] bg-[#38BDF8]/15 text-[#38BDF8]"
                  : "border-[#263244] bg-[#151E2E] text-[#94A3B8] hover:text-[#E2E8F0]"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        {loading ? (
          <LoadingSkeleton rows={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={() => loadData()} />
        ) : items.length === 0 ? (
          <EmptyState
            title={`No ${statusFilter.replace("_", " ")} alerts`}
            description="Select an alert from the Alert Center to start an investigation."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263244] text-[#94A3B8]">
                  <tr>
                    <th className="py-2.5 pr-3">Alert ID</th>
                    <th className="py-2.5 pr-3">Employee</th>
                    <th className="py-2.5 pr-3">Activity Date</th>
                    <th className="py-2.5 pr-3">Priority</th>
                    <th className="py-2.5 pr-3">Risk</th>
                    <th className="py-2.5 pr-3">Status</th>
                    <th className="py-2.5 pr-3">Last Updated</th>
                    <th className="py-2.5 text-right">Open</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263244]/60">
                  {items.map((a) => (
                    <tr key={a.alert_id} className="hover:bg-[#0B1120]/50">
                      <td className="py-2.5 pr-3 font-mono text-[#E2E8F0]">#{a.alert_id}</td>
                      <td className="py-2.5 pr-3 font-mono text-[#38BDF8]">{a.employee_id}</td>
                      <td className="py-2.5 pr-3 text-[#94A3B8]">{formatDateStr(a.activity_date)}</td>
                      <td className="py-2.5 pr-3"><PriorityBadge priority={a.priority} /></td>
                      <td className="py-2.5 pr-3"><RiskBar riskScore={a.risk_score} /></td>
                      <td className="py-2.5 pr-3"><StatusBadge status={a.status} /></td>
                      <td className="py-2.5 pr-3 text-[#94A3B8]">{formatTimestamp(a.updated_at)}</td>
                      <td className="py-2.5 text-right">
                        <button
                          type="button"
                          onClick={() => navigate(`/alerts/${a.alert_id}`)}
                          className="inline-flex items-center gap-1 rounded-md border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[11px] text-[#E2E8F0] hover:border-[#38BDF8]"
                        >
                          <Eye className="h-3 w-3" /> Open
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Pagination pagination={pagination} onPageChange={setPage} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

