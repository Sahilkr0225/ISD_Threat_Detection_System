import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { fetchAuditLogs } from "../api/audit";
import { extractApiErrorMessage } from "../api/client";
import { EmptyState, ErrorState, LoadingSkeleton } from "../components/common/FeedbackStates";
import type { SecurityAuditLogItem } from "../types/api";
import { formatTimestamp } from "../utils/formatters";

export default function AuditLogs() {
  const [items, setItems] = useState<SecurityAuditLogItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      fetchAuditLogs(
        {
          action: actionFilter || undefined,
          outcome: outcomeFilter || undefined,
          page,
          page_size: 25,
        },
        signal
      )
        .then((res) => {
          setItems(res.items);
          setTotalPages(res.pagination.total_pages);
          setTotal(res.pagination.total);
        })
        .catch((err) => {
          if ((err as { name?: string }).name === "CanceledError") return;
          setError(extractApiErrorMessage(err));
        })
        .finally(() => setLoading(false));
    },
    [actionFilter, outcomeFilter, page]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadLogs(controller.signal);
    return () => controller.abort();
  }, [loadLogs]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#E2E8F0]">Security Audit Logs</h1>
          <p className="text-xs text-[#94A3B8]">
            Immutable record of authentication events, access denials, user changes, and alert triage actions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadLogs()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#263244] bg-[#151E2E] px-3 py-1.5 text-xs text-[#E2E8F0] hover:border-[#38BDF8]/50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-1.5 text-xs text-[#E2E8F0]"
        >
          <option value="">All Actions</option>
          <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
          <option value="LOGIN_FAILURE">LOGIN_FAILURE</option>
          <option value="LOGOUT">LOGOUT</option>
          <option value="ACCESS_DENIED">ACCESS_DENIED</option>
          <option value="CSRF_REJECTED">CSRF_REJECTED</option>
          <option value="USER_CREATED">USER_CREATED</option>
          <option value="USER_UPDATED">USER_UPDATED</option>
          <option value="PASSWORD_RESET">PASSWORD_RESET</option>
          <option value="PASSWORD_CHANGED">PASSWORD_CHANGED</option>
          <option value="INVESTIGATION_STATUS_CHANGED">INVESTIGATION_STATUS_CHANGED</option>
        </select>

        <select
          value={outcomeFilter}
          onChange={(e) => {
            setOutcomeFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-1.5 text-xs text-[#E2E8F0]"
        >
          <option value="">All Outcomes</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="FAILURE">FAILURE</option>
          <option value="DENIED">DENIED</option>
        </select>

        <span className="ml-auto text-xs text-[#94A3B8]">{total} total events</span>
      </div>

      {loading ? (
        <LoadingSkeleton rows={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadLogs()} />
      ) : items.length === 0 ? (
        <EmptyState title="No audit events found" description="Try adjusting the action or outcome filter." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[#263244] bg-[#151E2E]">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#263244] bg-[#0B1120]/60 text-[11px] uppercase text-[#94A3B8]">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Outcome</th>
                <th className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#263244]">
              {items.map((item) => (
                <tr key={item.audit_id} className="hover:bg-[#0B1120]/40">
                  <td className="whitespace-nowrap px-4 py-3 text-[#94A3B8]">
                    {formatTimestamp(item.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-[#E2E8F0]">
                    {item.actor_username ? (
                      <span>
                        {item.actor_display_name ?? item.actor_username}{" "}
                        <span className="text-[#64748B]">({item.actor_username})</span>
                      </span>
                    ) : (
                      <span className="text-[#64748B]">System / Anonymous</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-[#38BDF8]">{item.action}</td>
                  <td className="px-4 py-3 text-[#94A3B8]">
                    {item.resource_type}
                    {item.resource_id ? ` #${item.resource_id}` : ""}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        item.outcome === "SUCCESS"
                          ? "bg-emerald-500/15 text-emerald-300"
                          : item.outcome === "DENIED"
                          ? "bg-amber-500/15 text-amber-300"
                          : "bg-red-500/15 text-red-300"
                      }`}
                    >
                      {item.outcome}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-[#94A3B8]" title={item.details ?? ""}>
                    {item.details ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs text-[#94A3B8]">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="inline-flex items-center gap-1 rounded border border-[#263244] bg-[#151E2E] px-2.5 py-1 disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Prev
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="inline-flex items-center gap-1 rounded border border-[#263244] bg-[#151E2E] px-2.5 py-1 disabled:opacity-40"
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

