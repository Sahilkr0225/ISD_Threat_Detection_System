import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  ClipboardCheck,
  Eye,
  Flame,
  ShieldAlert,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchDashboardSummary, fetchDashboardTrends } from "../api/dashboard";
import { fetchAlerts } from "../api/alerts";
import { extractApiErrorMessage } from "../api/client";
import { KpiCard } from "../components/common/KpiCard";
import { InfoTooltip, PriorityBadge, RiskBar, StatusBadge } from "../components/common/Badges";
import { EmptyState, ErrorState, LoadingSkeleton } from "../components/common/FeedbackStates";
import type {
  AlertSummaryItem,
  DailyTrendPoint,
  DashboardSummaryResponse,
} from "../types/api";
import { formatDateStr, formatNumber, formatTimestamp } from "../utils/formatters";

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Medium: "#f59e0b",
  Low: "#38bdf8",
};

export default function Overview() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [trends, setTrends] = useState<DailyTrendPoint[]>([]);
  const [priorityQueue, setPriorityQueue] = useState<AlertSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchDashboardSummary(signal),
      fetchDashboardTrends(undefined, signal),
      fetchAlerts({ priority: "Critical", status: "OPEN", page: 1, page_size: 6 }, signal),
    ])
      .then(([sumRes, trendRes, queueRes]) => {
        setSummary(sumRes);
        setTrends(trendRes.items);
        setPriorityQueue(queueRes.items);
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

  if (loading) return <LoadingSkeleton rows={7} />;
  if (error || !summary) {
    return <ErrorState message={error ?? "Unable to load security overview."} onRetry={() => loadData()} />;
  }

  const totalCritical = summary.alerts_by_priority.Critical ?? 0;
  const criticalOpen = summary.critical_open_alerts ?? totalCritical;
  const completedCount = summary.resolved_alerts + summary.dismissed_alerts;

  const priorityChartData = ["Critical", "High", "Medium", "Low"].map((name) => ({
    name,
    count: summary.alerts_by_priority[name] ?? 0,
    fill: PRIORITY_COLORS[name],
  }));

  const statusChartData = [
    { name: "Awaiting Review", count: summary.open_alerts, fill: "#ef4444" },
    { name: "In Progress", count: summary.under_review_alerts, fill: "#f59e0b" },
    { name: "Resolved", count: summary.resolved_alerts, fill: "#10b981" },
    { name: "Dismissed", count: summary.dismissed_alerts, fill: "#64748b" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#E2E8F0]">Security Overview</h1>
          <p className="text-xs text-[#94A3B8]">
            Historical dataset coverage: {formatDateStr(summary.coverage_start_date)} to{" "}
            {formatDateStr(summary.coverage_end_date)} · Active Model:{" "}
            <span className="font-mono text-[#38BDF8]">{summary.model_version}</span>
          </p>
        </div>
        <div className="rounded-lg border border-[#38BDF8]/30 bg-[#38BDF8]/10 px-3 py-1.5 text-xs text-[#38BDF8]">
          Alerts highlight unusual behavioural patterns for human review — never proof of malicious intent.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          title="Employees Monitored"
          value={formatNumber(summary.unique_employees)}
          subtitle="In historical dataset"
          icon={Users}
          onClick={() => navigate("/employees")}
        />
        <KpiCard
          title="Daily Activity Records"
          value={formatNumber(summary.total_observations)}
          subtitle="Employee-day logs analyzed"
          icon={Activity}
        />
        <KpiCard
          title="Total Detected Alerts"
          value={formatNumber(summary.total_alerts)}
          subtitle="Alerts requiring review"
          icon={AlertOctagon}
          accentClass="text-amber-400"
          onClick={() => navigate("/alerts")}
        />
        <KpiCard
          title="Alerts Awaiting Review"
          value={formatNumber(summary.open_alerts)}
          subtitle="Open investigation queue"
          icon={ShieldAlert}
          accentClass="text-red-400"
          onClick={() => navigate("/alerts?status=OPEN")}
        />
        <KpiCard
          title="Critical Alerts"
          value={`${formatNumber(criticalOpen)} / ${formatNumber(totalCritical)}`}
          subtitle="Awaiting review / Total Critical"
          icon={Flame}
          accentClass="text-red-500"
          onClick={() => navigate("/alerts?priority=Critical&status=OPEN")}
        />
        <KpiCard
          title="Active / Completed"
          value={`${formatNumber(summary.under_review_alerts)} / ${formatNumber(completedCount)}`}
          subtitle="In progress / Resolved+Dismissed"
          icon={summary.under_review_alerts > 0 ? ClipboardCheck : CheckCircle2}
          accentClass="text-emerald-400"
          onClick={() => navigate("/investigations")}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold text-[#E2E8F0]">Daily Suspicious Activity Trend</h2>
          <p className="text-xs text-[#94A3B8]">
            Number of daily employee records flagged for review vs. High &amp; Critical priority
          </p>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends}>
                <CartesianGrid stroke="#263244" strokeDasharray="3 3" />
                <XAxis dataKey="activity_date" tick={{ fill: "#94A3B8", fontSize: 11 }} minTickGap={24} />
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
                <Area
                  type="monotone"
                  dataKey="flagged_count"
                  name="All Flagged Records"
                  stroke="#38BDF8"
                  fill="#38BDF8"
                  fillOpacity={0.2}
                />
                <Area
                  type="monotone"
                  dataKey="high_critical_count"
                  name="High & Critical Priority"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.25}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
            <h2 className="text-sm font-semibold text-[#E2E8F0]">
              Investigation Priority Distribution
              <InfoTooltip text="Critical priority means the activity is highly unusual under the selected scoring policy — not confirmed malicious intent." />
            </h2>
            <div className="mt-3 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityChartData} layout="vertical" margin={{ right: 48 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} width={62} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B1120",
                      borderColor: "#263244",
                      color: "#E2E8F0",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {priorityChartData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                    <LabelList dataKey="count" position="right" fill="#E2E8F0" fontSize={11} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
            <h2 className="text-sm font-semibold text-[#E2E8F0]">Investigation Status Distribution</h2>
            <div className="mt-3 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusChartData} layout="vertical" margin={{ right: 48 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} width={98} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B1120",
                      borderColor: "#263244",
                      color: "#E2E8F0",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {statusChartData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                    <LabelList dataKey="count" position="right" fill="#E2E8F0" fontSize={11} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Operational Sections */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Critical Alerts Awaiting Investigation */}
        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#E2E8F0]">Critical Alerts Awaiting Investigation</h2>
              <p className="text-xs text-[#94A3B8]">Open Critical-priority alerts ready for immediate review</p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/alerts?priority=Critical&status=OPEN")}
              className="text-xs font-medium text-[#38BDF8] hover:underline"
            >
              View all ({formatNumber(criticalOpen)})
            </button>
          </div>
          <div className="mt-3 overflow-x-auto">
            {priorityQueue.length === 0 ? (
              <EmptyState title="No open Critical alerts" description="All Critical alerts have been triaged." />
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#263244] text-[#94A3B8]">
                  <tr>
                    <th className="py-2 pr-2">Alert</th>
                    <th className="py-2 pr-2">Employee</th>
                    <th className="py-2 pr-2">Date</th>
                    <th className="py-2 pr-2">
                      Unusualness Rank
                      <InfoTooltip text="Relative ranking compared to historical validation records — not a probability of malicious intent." />
                    </th>
                    <th className="py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#263244]/60">
                  {priorityQueue.map((a) => (
                    <tr key={a.alert_id} className="hover:bg-[#0B1120]/50">
                      <td className="py-2 pr-2 font-mono text-[#E2E8F0]">#{a.alert_id}</td>
                      <td className="py-2 pr-2 font-mono text-[#38BDF8]">
                        <button type="button" onClick={() => navigate(`/employees/${a.employee_id}`)} className="hover:underline">
                          {a.employee_id}
                        </button>
                      </td>
                      <td className="py-2 pr-2 text-[#94A3B8]">{formatDateStr(a.activity_date)}</td>
                      <td className="py-2 pr-2">
                        <RiskBar riskScore={a.risk_score} />
                      </td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          onClick={() => navigate(`/alerts/${a.alert_id}`)}
                          className="inline-flex items-center gap-1 rounded-md border border-[#263244] bg-[#0B1120] px-2 py-1 text-[11px] text-[#E2E8F0] hover:border-[#38BDF8]"
                        >
                          <Eye className="h-3 w-3" /> Review Alert
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Employees with Repeated Alerts */}
        <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#E2E8F0]">Employees with Repeated Alerts</h2>
              <p className="text-xs text-[#94A3B8]">Ranked by highest recorded unusual-activity priority</p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/employees")}
              className="text-xs font-medium text-[#38BDF8] hover:underline"
            >
              Employee Directory
            </button>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#263244] text-[#94A3B8]">
                <tr>
                  <th className="py-2 pr-2">Employee</th>
                  <th className="py-2 pr-2">Department</th>
                  <th className="py-2 pr-2">Total Alerts</th>
                  <th className="py-2">Highest Unusualness</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#263244]/60">
                {summary.top_employees.slice(0, 6).map((emp) => (
                  <tr
                    key={emp.employee_id}
                    onClick={() => navigate(`/employees/${emp.employee_id}`)}
                    className="cursor-pointer hover:bg-[#0B1120]/50"
                  >
                    <td className="py-2 pr-2 font-mono text-[#38BDF8]">{emp.employee_id}</td>
                    <td className="py-2 pr-2 text-[#94A3B8] truncate max-w-[160px]">
                      {emp.department ?? "Unknown"}
                    </td>
                    <td className="py-2 pr-2 text-[#E2E8F0]">{emp.alert_count}</td>
                    <td className="py-2">
                      <RiskBar riskScore={emp.max_risk_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent Investigation Activity */}
      <div className="rounded-xl border border-[#263244] bg-[#151E2E] p-4">
        <h2 className="text-sm font-semibold text-[#E2E8F0]">Recent Investigation Activity</h2>
        <div className="mt-3">
          {summary.recent_investigations.length === 0 ? (
            <EmptyState
              title="No investigation transitions recorded yet"
              description="Open an alert in Suspicious Activity to start an investigation, add analyst notes, and complete or dismiss alerts."
            />
          ) : (
            <div className="divide-y divide-[#263244]/60 text-xs">
              {summary.recent_investigations.map((inv) => (
                <div
                  key={inv.history_id}
                  onClick={() => navigate(`/alerts/${inv.alert_id}`)}
                  className="flex flex-wrap items-center justify-between gap-2 py-2.5 cursor-pointer hover:bg-[#0B1120]/40 px-2 rounded"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <PriorityBadge priority="Critical" />
                    <span className="font-mono text-[#38BDF8]">Alert #{inv.alert_id}</span>
                    <span className="text-[#94A3B8]">({inv.employee_id})</span>
                    <StatusBadge status={inv.previous_status} />
                    <span className="text-[#94A3B8]">→</span>
                    <StatusBadge status={inv.new_status} />
                    <span className="text-[#94A3B8]">
                      by{" "}
                      <span className="text-[#E2E8F0]">
                        {inv.actor_display_name ?? inv.actor_username ?? "Legacy / Unauthenticated"}
                      </span>
                    </span>
                    {inv.analyst_note && (
                      <span className="text-[#E2E8F0] italic">“{inv.analyst_note}”</span>
                    )}
                  </div>
                  <span className="text-[#94A3B8]">{formatTimestamp(inv.changed_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
