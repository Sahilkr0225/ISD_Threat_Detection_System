import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Eye } from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchEmployeeDetail, fetchEmployeeHistory } from "../api/employees";
import { extractApiErrorMessage } from "../api/client";
import { InfoTooltip, PriorityBadge, StatusBadge } from "../components/common/Badges";
import { ErrorState, LoadingSkeleton, Pagination } from "../components/common/FeedbackStates";
import type {
  EmployeeDetailResponse,
  EmployeeObservationItem,
  PaginationMeta,
} from "../types/api";
import { formatDateStr } from "../utils/formatters";

export default function EmployeeDetail() {
  const { employeeId = "" } = useParams<{ employeeId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<EmployeeDetailResponse | null>(null);
  const [history, setHistory] = useState<EmployeeObservationItem[]>([]);
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
      Promise.all([
        fetchEmployeeDetail(employeeId, signal),
        fetchEmployeeHistory(employeeId, { page, page_size: 25 }, signal),
      ])
        .then(([empRes, histRes]) => {
          setDetail(empRes);
          setHistory(histRes.items);
          setPagination(histRes.pagination);
        })
        .catch((err) => {
          if ((err as { name?: string }).name === "CanceledError") return;
          setError(extractApiErrorMessage(err));
        })
        .finally(() => setLoading(false));
    },
    [employeeId, page]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  if (loading) return <LoadingSkeleton rows={7} />;
  if (error || !detail) {
    return <ErrorState message={error ?? "Employee not found."} onRetry={() => loadData()} />;
  }

  const chartData = [...history].reverse();

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={() => navigate("/employees")}
        className="inline-flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#E2E8F0]"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Employee Monitoring
      </button>

      {/* Profile Header */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-mono text-xl font-semibold text-[#38BDF8]">
                {detail.employee_id}
              </h1>
              <span className="rounded-md border border-[#263244] bg-[#0B1120] px-2.5 py-0.5 text-xs text-[#E2E8F0]">
                {detail.open_alert_count > 0
                  ? "Requires review"
                  : detail.alert_count > 0
                  ? "Unusual activity detected"
                  : "No alerts recorded"}
              </span>
            </div>
            <p className="mt-1 text-xs text-[#94A3B8]">
              {detail.role ?? "Unknown Role"} · {detail.department ?? "Unknown Department"} ·{" "}
              {detail.functional_unit ?? "Unknown Unit"}
            </p>
            <p className="mt-1 text-xs text-[#94A3B8]">
              Recorded Activity Period: {formatDateStr(detail.first_activity_date)} to{" "}
              {formatDateStr(detail.last_activity_date)}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
              <div className="text-[#94A3B8]">Daily Records</div>
              <div className="mt-1 text-base font-semibold text-[#E2E8F0]">
                {detail.observation_count}
              </div>
            </div>
            <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
              <div className="text-[#94A3B8]">Total Alerts</div>
              <div className="mt-1 text-base font-semibold text-[#E2E8F0]">
                {detail.alert_count}
              </div>
            </div>
            <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
              <div className="text-[#94A3B8]">Awaiting Review</div>
              <div className="mt-1 text-base font-semibold text-amber-300">
                {detail.open_alert_count}
              </div>
            </div>
            <div className="rounded-lg border border-[#263244] bg-[#0B1120] p-3">
              <div className="text-[#94A3B8]">
                Peak Unusualness
                <InfoTooltip text="Highest anomaly percentile recorded for this employee — not a probability of malicious intent." />
              </div>
              <div className="mt-1 text-base font-semibold text-[#38BDF8]">
                {detail.max_risk_score.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Activity & Unusualness Timeline */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        <h2 className="text-sm font-semibold text-[#E2E8F0]">
          Employee Activity Unusualness Over Time
        </h2>
        <p className="text-xs text-[#94A3B8]">
          Higher values indicate days that differed more strongly from typical patterns (current page of active days)
        </p>
        <div className="mt-3 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="#263244" strokeDasharray="3 3" />
              <XAxis dataKey="activity_date" tick={{ fill: "#94A3B8", fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "#94A3B8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0B1120",
                  borderColor: "#263244",
                  color: "#E2E8F0",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                type="monotone"
                dataKey="risk_score"
                name="Activity Unusualness Rank (%)"
                stroke="#38BDF8"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Observation History Table */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        <h2 className="text-sm font-semibold text-[#E2E8F0]">Recent Recorded Activity</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#263244] text-[#94A3B8]">
              <tr>
                <th className="py-2 pr-2">Date</th>
                <th className="py-2 pr-2">Logins (After-Hours)</th>
                <th className="py-2 pr-2">Web</th>
                <th className="py-2 pr-2">Email</th>
                <th className="py-2 pr-2">Files</th>
                <th className="py-2 pr-2">USB</th>
                <th className="py-2 pr-2">Investigation Priority</th>
                <th className="py-2">Alert / Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#263244]/60">
              {history.map((obs) => (
                <tr key={obs.observation_id} className="hover:bg-[#0B1120]/50">
                  <td className="py-2 pr-2 font-mono text-[#E2E8F0]">
                    {formatDateStr(obs.activity_date)}
                  </td>
                  <td className="py-2 pr-2 text-[#E2E8F0]">
                    {obs.login_count} ({obs.after_hours_login_count})
                  </td>
                  <td className="py-2 pr-2 text-[#94A3B8]">{obs.http_activity_count}</td>
                  <td className="py-2 pr-2 text-[#94A3B8]">{obs.email_activity_count}</td>
                  <td className="py-2 pr-2 text-[#94A3B8]">{obs.file_activity_count}</td>
                  <td className="py-2 pr-2 text-[#94A3B8]">{obs.usb_activity_count}</td>
                  <td className="py-2 pr-2">
                    <PriorityBadge priority={obs.priority} />
                  </td>
                  <td className="py-2">
                    {obs.alert_id ? (
                      <button
                        type="button"
                        onClick={() => navigate(`/alerts/${obs.alert_id}`)}
                        className="inline-flex items-center gap-1.5 text-[#38BDF8] hover:underline"
                      >
                        <Eye className="h-3 w-3" /> #{obs.alert_id}
                        {obs.alert_status && <StatusBadge status={obs.alert_status} />}
                      </button>
                    ) : (
                      <span className="text-[#94A3B8]">No alert</span>
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
      </div>
    </div>
  );
}
