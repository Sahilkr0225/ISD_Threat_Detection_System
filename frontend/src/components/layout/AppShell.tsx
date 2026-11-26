import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  AlertOctagon,
  BarChart3,
  ClipboardCheck,
  Database,
  LayoutDashboard,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldAlert,
  Users,
  X,
} from "lucide-react";
import { fetchHealth } from "../../api/dashboard";
import type { HealthResponse } from "../../types/api";

const NAV_GROUPS = [
  {
    title: "Security Operations",
    items: [
      { to: "/", label: "Security Overview", icon: LayoutDashboard },
      { to: "/employees", label: "Employee Monitoring", icon: Users },
      { to: "/alerts", label: "Suspicious Activity", icon: AlertOctagon },
      { to: "/investigations", label: "Investigations", icon: ClipboardCheck },
    ],
  },
  {
    title: "Advanced & Technical",
    items: [
      { to: "/model", label: "AI Model Performance", icon: BarChart3 },
      { to: "/system", label: "Dataset & System", icon: Database },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((res) => {
        setHealth(res);
        setApiOnline(res.status === "ok" && res.model_loaded && res.database_ready);
      })
      .catch(() => {
        setApiOnline(false);
      });
    return () => controller.abort();
  }, [location.pathname]);

  const segments = location.pathname.split("/").filter(Boolean);

  return (
    <div className="flex min-h-screen bg-[#0B1120] text-[#E2E8F0]">
      {/* Desktop Sidebar */}
      <aside
        className={`hidden md:flex flex-col border-r border-[#263244] bg-[#151E2E] transition-all duration-200 ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-[#263244] px-3.5">
          {!collapsed && (
            <Link to="/" className="flex items-center gap-2 font-semibold text-sm text-[#E2E8F0]">
              <ShieldAlert className="h-5 w-5 text-[#38BDF8]" />
              <span className="truncate">ISD Threat SOC</span>
            </Link>
          )}
          {collapsed && <ShieldAlert className="mx-auto h-5 w-5 text-[#38BDF8]" />}
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            aria-label="Toggle sidebar"
            className="rounded-md p-1 text-[#94A3B8] hover:bg-[#0B1120] hover:text-[#E2E8F0]"
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>
        </div>

        <nav className="flex-1 space-y-4 p-2.5">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="space-y-1">
              {!collapsed && (
                <div className="px-3 pt-1 pb-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
                  {group.title}
                </div>
              )}
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={label}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-[#38BDF8]/15 text-[#38BDF8] border border-[#38BDF8]/30"
                        : "text-[#94A3B8] hover:bg-[#0B1120] hover:text-[#E2E8F0] border border-transparent"
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{label}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {!collapsed && (
          <div className="border-t border-[#263244] p-3 text-[11px] text-[#94A3B8]">
            <p className="font-medium text-[#E2E8F0]">Historical CERT r4.2</p>
            <p className="mt-0.5">Flags unusual patterns for human review. Not live surveillance.</p>
          </div>
        )}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div className="w-64 border-r border-[#263244] bg-[#151E2E] p-3">
            <div className="flex items-center justify-between border-b border-[#263244] pb-3">
              <span className="flex items-center gap-2 text-sm font-semibold">
                <ShieldAlert className="h-5 w-5 text-[#38BDF8]" />
                ISD Threat SOC
              </span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="text-[#94A3B8]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav className="mt-3 space-y-4">
              {NAV_GROUPS.map((group) => (
                <div key={group.title} className="space-y-1">
                  <div className="px-3 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
                    {group.title}
                  </div>
                  {group.items.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === "/"}
                      onClick={() => setMobileOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium ${
                          isActive
                            ? "bg-[#38BDF8]/15 text-[#38BDF8]"
                            : "text-[#94A3B8] hover:bg-[#0B1120]"
                        }`
                      }
                    >
                      <Icon className="h-4 w-4" />
                      <span>{label}</span>
                    </NavLink>
                  ))}
                </div>
              ))}
            </nav>
          </div>
          <div className="flex-1 bg-black/60" onClick={() => setMobileOpen(false)} />
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 items-center justify-between border-b border-[#263244] bg-[#151E2E]/80 px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-md p-1.5 text-[#94A3B8] hover:bg-[#0B1120] md:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
              <Link to="/" className="hover:text-[#E2E8F0]">
                Console
              </Link>
              {segments.map((seg, idx) => (
                <span key={idx} className="flex items-center gap-1.5">
                  <span>/</span>
                  <span className="capitalize text-[#E2E8F0]">{seg}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2.5 text-xs">
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[#94A3B8]">
              <Database className="h-3.5 w-3.5 text-[#38BDF8]" />
              Historical Dataset (CERT r4.2)
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium ${
                apiOnline === true
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : apiOnline === false
                  ? "border-red-500/30 bg-red-500/10 text-red-300"
                  : "border-[#263244] bg-[#0B1120] text-[#94A3B8]"
              }`}
            >
              <Activity className="h-3.5 w-3.5" />
              {apiOnline === true
                ? `Backend Connected (Phase ${health?.phase ?? "3"})`
                : apiOnline === false
                ? "Backend Offline"
                : "Checking API..."}
            </span>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-6 max-w-[1600px] w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
