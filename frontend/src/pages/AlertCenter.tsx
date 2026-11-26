import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertOctagon, Eye, RefreshCw, RotateCcw } from "lucide-react";
import { fetchAlerts } from "../api/alerts";
import { extractApiErrorMessage } from "../api/client";
import { InfoTooltip, PriorityBadge, StatusBadge } from "../components/common/Badges";
import { EmptyState, ErrorState, LoadingSkeleton, Pagination } from "../components/common/FeedbackStates";
import type {
  AlertStatus,
  AlertSummaryItem,
  PaginationMeta,
  PriorityLevel,
} from "../types/api";
import { formatDateStr } from "../utils/formatters";

export default function AlertCenter() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [priority, setPriority] = useState<PriorityLevel | "">(
    (searchParams.get("priority") as PriorityLevel) || ""
  );
  const [status, setStatus] = useState<AlertStatus | "">(
    (searchParams.get("status") as AlertStatus) || ""
  );
  const [employeeId, setEmployeeId] = useState(searchParams.get("employee_id") || "");
  const [dateFrom, setDateFrom] = useState(searchParams.get("date_from") || "");
  const [dateTo, setDateTo] = useState(searchParams.get("date_to") || "");
  const [sortBy, setSortBy] = useState<"anomaly_score" | "activity_date">("anomaly_score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<AlertSummaryItem[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: 1,
    page_size: 25,
    total: 0,
    total_pages: 1,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAlerts = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      fetchAlerts(
        {
          priority,
          status,
          employee_id: employeeId,
          date_from: dateFrom,
          date_to: dateTo,
          sort_by: sortBy,
          sort_order: sortOrder,
          page,
          page_size: 25,
        },
        signal
      )
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
    [priority, status, employeeId, dateFrom, dateTo, sortBy, sortOrder, page]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadAlerts(controller.signal);
    return () => controller.abort();
  }, [loadAlerts]);

  const resetFilters = () => {
    setPriority("");
    setStatus("");
    setEmployeeId("");
    setDateFrom("");
    setDateTo("");
    setSortBy("anomaly_score");
    setSortOrder("desc");
    setPage(1);
    setSearchParams({});
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-[#E2E8F0]">
            <AlertOctagon className="h-5 w-5 text-[#38BDF8]" /> Suspicious Activity
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Prioritized investigation queue. Critical priority means highly unusual behaviour — not confirmed malicious intent.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadAlerts()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#263244] bg-[#151E2E] px-3 py-1.5 text-xs text-[#E2E8F0] hover:border-[#38BDF8]"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 gap-2.5 rounded-xl border border-[#263244] bg-[#151E2E] p-3.5 sm:grid-cols-2 lg:grid-cols-6 items-end">
        <div className="flex flex-col gap-1">
          <label htmlFor="alert-prio" className="text-[10px] font-medium uppercase tracking-wider text-[#94A3B8]">
            Investigation Priority
          </label>
          <select
            id="alert-prio"
            aria-label="Filter by priority"
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value as PriorityLevel | "");
              setPage(1);
            }}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1.5 text-xs text-[#E2E8F0]"
          >
            <option value="">All Priorities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="alert-status" className="text-[10px] font-medium uppercase tracking-wider text-[#94A3B8]">
            Investigation Status
          </label>
          <select
            id="alert-status"
            aria-label="Filter by status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as AlertStatus | "");
              setPage(1);
            }}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1.5 text-xs text-[#E2E8F0]"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="UNDER_REVIEW">UNDER REVIEW</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="DISMISSED">DISMISSED</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="alert-emp" className="text-[10px] font-medium uppercase tracking-wider text-[#94A3B8]">
            Employee ID
          </label>
          <input
            id="alert-emp"
            type="text"
            value={employeeId}
            onChange={(e) => {
              setEmployeeId(e.target.value);
              setPage(1);
            }}
            placeholder="e.g., IBB0359"
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1.5 text-xs text-[#E2E8F0] placeholder-[#94A3B8]"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="alert-date-from" className="text-[10px] font-medium uppercase tracking-wider text-[#94A3B8]">
            From Date
          </label>
          <input
            id="alert-date-from"
            type="date"
            aria-label="From Date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1.5 text-xs text-[#E2E8F0] [color-scheme:dark]"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="alert-date-to" className="text-[10px] font-medium uppercase tracking-wider text-[#94A3B8]">
            To Date
          </label>
          <input
            id="alert-date-to"
            type="date"
            aria-label="To Date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-2.5 py-1.5 text-xs text-[#E2E8F0] [color-scheme:dark]"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            aria-label="Sort by"
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(":") as ["anomaly_score" | "activity_date", "asc" | "desc"];
              setSortBy(sb);
              setSortOrder(so);
              setPage(1);
            }}
            className="flex-1 rounded-lg border border-[#263244] bg-[#0B1120] px-2 py-1.5 text-xs text-[#E2E8F0]"
          >
            <option value="anomaly_score:desc">Priority (Highest First)</option>
            <option value="anomaly_score:asc">Priority (Lowest First)</option>
            <option value="activity_date:desc">Date (Newest)</option>
            <option value="activity_date:asc">Date (Oldest)</option>
          </select>
          <button
            type="button"
            onClick={resetFilters}
            title="Reset filters"
            className="rounded-lg border border-[#263244] bg-[#0B1120] p-1.5 text-[#94A3B8] hover:text-[#E2E8F0]"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Alert Table */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        {loading ? (
          <LoadingSkeleton rows={8} />
        ) : error ? (
          <ErrorState message={error} onRetry={() => loadAlerts()} />
        ) : items.length === 0 ? (
          <EmptyState
            title="No alerts match the current filters"
            description="Adjust priority, status, employee ID, or date filters to view alerts."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263244] text-[#94A3B8]">
                  <tr>
                    <th className="py-2.5 pr-3">Alert ID</th>
                    <th className="py-2.5 pr-3">Employee ID</th>
                    <th className="py-2.5 pr-3">Activity Date</th>
                    <th className="py-2.5 pr-3">
                      Investigation Priority
                      <InfoTooltip text="Critical priority means highly unusual activity under the scoring policy; it requires human review." />
                    </th>
                    <th className="py-2.5 pr-3">Status</th>
                    <th className="py-2.5 pr-3">Unusual Activity Summary</th>
                    <th className="py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263244]/60">
                  {items.map((a) => (
                    <tr key={a.alert_id} className="hover:bg-[#0B1120]/50">
                      <td className="py-2.5 pr-3 font-mono text-[#E2E8F0]">#{a.alert_id}</td>
                      <td className="py-2.5 pr-3 font-mono text-[#38BDF8]">
                        <button
                          type="button"
                          onClick={() => navigate(`/employees/${a.employee_id}`)}
                          className="hover:underline"
                        >
                          {a.employee_id}
                        </button>
                      </td>
                      <td className="py-2.5 pr-3 text-[#94A3B8] whitespace-nowrap">
                        {formatDateStr(a.activity_date)}
                      </td>
                      <td className="py-2.5 pr-3">
                        <PriorityBadge priority={a.priority} />
                      </td>
                      <td className="py-2.5 pr-3">
                        <StatusBadge status={a.status} />
                      </td>
                      <td className="py-2.5 pr-3 text-[#E2E8F0] max-w-md">
                        <span className="line-clamp-2">
                          {a.activity_summary ?? "Review alert details for behavioural evidence."}
                        </span>
                      </td>
                      <td className="py-2.5 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => navigate(`/alerts/${a.alert_id}`)}
                          className="inline-flex items-center gap-1 rounded-md border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[11px] font-medium text-[#E2E8F0] hover:border-[#38BDF8]"
                        >
                          <Eye className="h-3 w-3" /> Review Alert
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
