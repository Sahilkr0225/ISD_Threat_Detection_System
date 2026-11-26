import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Users } from "lucide-react";
import { fetchEmployees } from "../api/employees";
import { extractApiErrorMessage } from "../api/client";
import { PriorityBadge } from "../components/common/Badges";
import { EmptyState, ErrorState, LoadingSkeleton, Pagination } from "../components/common/FeedbackStates";
import type { EmployeeSummary, PaginationMeta } from "../types/api";
import { formatDateStr, formatNumber } from "../utils/formatters";

export default function Employees() {
  const navigate = useNavigate();
  const [items, setItems] = useState<EmployeeSummary[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: 1,
    page_size: 25,
    total: 0,
    total_pages: 1,
  });
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadEmployees = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      fetchEmployees(
        {
          search: debouncedSearch || undefined,
          department: department || undefined,
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
    [debouncedSearch, department, page]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadEmployees(controller.signal);
    return () => controller.abort();
  }, [loadEmployees]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-semibold text-[#E2E8F0]">
          <Users className="h-5 w-5 text-[#38BDF8]" /> Employee Monitoring
        </h1>
        <p className="text-xs text-[#94A3B8]">
          Monitored employees from the historical dataset. An alert indicates unusual recorded activity requiring review — not confirmed malicious intent.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[#263244] bg-[#151E2E] p-3.5">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#94A3B8]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Employee ID (e.g., BMG0917 or AAL0706)..."
            className="w-full rounded-lg border border-[#263244] bg-[#0B1120] py-1.5 pl-9 pr-3 text-xs text-[#E2E8F0] placeholder-[#94A3B8] focus:border-[#38BDF8] focus:outline-none"
          />
        </div>
        <select
          aria-label="Filter by department"
          value={department}
          onChange={(e) => {
            setDepartment(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-1.5 text-xs text-[#E2E8F0] focus:border-[#38BDF8] focus:outline-none"
        >
          <option value="">All Departments</option>
          <option value="3 - Assembly">3 - Assembly</option>
          <option value="2 - Sales">2 - Sales</option>
          <option value="3 - FieldService">3 - FieldService</option>
          <option value="3 - Engineering">3 - Engineering</option>
          <option value="Unknown">Unknown</option>
        </select>
        {(search || department) && (
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setDepartment("");
              setPage(1);
            }}
            className="rounded-lg border border-[#263244] px-3 py-1.5 text-xs text-[#94A3B8] hover:text-[#E2E8F0]"
          >
            Reset
          </button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        {loading ? (
          <LoadingSkeleton rows={8} />
        ) : error ? (
          <ErrorState message={error} onRetry={() => loadEmployees()} />
        ) : items.length === 0 ? (
          <EmptyState
            title="No employees match your filters"
            description="Try clearing the Employee ID search or department filter."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263244] text-[#94A3B8]">
                  <tr>
                    <th className="py-2.5 pr-3">Employee ID</th>
                    <th className="py-2.5 pr-3">Role</th>
                    <th className="py-2.5 pr-3">Department</th>
                    <th className="py-2.5 pr-3">Recorded Period</th>
                    <th className="py-2.5 pr-3">Daily Records</th>
                    <th className="py-2.5 pr-3">Total Alerts</th>
                    <th className="py-2.5 pr-3">Awaiting Review</th>
                    <th className="py-2.5 pr-3">Highest Priority</th>
                    <th className="py-2.5">Monitoring Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263244]/60">
                  {items.map((emp) => (
                    <tr
                      key={emp.employee_id}
                      onClick={() => navigate(`/employees/${emp.employee_id}`)}
                      className="cursor-pointer hover:bg-[#0B1120]/50"
                    >
                      <td className="py-2.5 pr-3 font-mono font-medium text-[#38BDF8]">
                        {emp.employee_id}
                      </td>
                      <td className="py-2.5 pr-3 text-[#E2E8F0]">{emp.role ?? "Unknown"}</td>
                      <td className="py-2.5 pr-3 text-[#94A3B8]">{emp.department ?? "Unknown"}</td>
                      <td className="py-2.5 pr-3 text-[#94A3B8]">
                        {formatDateStr(emp.first_activity_date)} – {formatDateStr(emp.last_activity_date)}
                      </td>
                      <td className="py-2.5 pr-3 text-[#E2E8F0]">{formatNumber(emp.observation_count)}</td>
                      <td className="py-2.5 pr-3 text-[#E2E8F0]">{emp.alert_count}</td>
                      <td className="py-2.5 pr-3 text-[#E2E8F0]">{emp.open_alert_count}</td>
                      <td className="py-2.5 pr-3">
                        <PriorityBadge priority={emp.highest_priority ?? "Informational"} />
                      </td>
                      <td className="py-2.5">
                        {emp.open_alert_count > 0 ? (
                          <span className="text-amber-300 font-medium">Requires review</span>
                        ) : emp.alert_count > 0 ? (
                          <span className="text-[#94A3B8]">Unusual activity reviewed</span>
                        ) : (
                          <span className="text-emerald-300">No alerts recorded</span>
                        )}
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
