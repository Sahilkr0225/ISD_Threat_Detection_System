import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Lock, ShieldAlert, User } from "lucide-react";
import { extractApiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from =
    (location.state as { from?: string } | null)?.from &&
    (location.state as { from?: string }).from !== "/login"
      ? (location.state as { from: string }).from
      : "/";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError("Please enter both username and password.");
      return;
    }
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(extractApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B1120] px-4 text-[#E2E8F0]">
      <div className="w-full max-w-md rounded-xl border border-[#263244] bg-[#151E2E] p-8 shadow-2xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#38BDF8]/30 bg-[#38BDF8]/10">
            <ShieldAlert className="h-6 w-6 text-[#38BDF8]" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#E2E8F0]">ISD Threat SOC</h1>
            <p className="text-xs text-[#94A3B8]">
              Insider Threat Detection &amp; Investigation Portal
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-username" className="mb-1.5 block text-xs font-medium text-[#94A3B8]">
              Username
            </label>
            <div className="relative">
              <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-[#64748B]" />
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full rounded-lg border border-[#263244] bg-[#0B1120] py-2 pr-3 pl-9 text-sm text-[#E2E8F0] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="login-password" className="mb-1.5 block text-xs font-medium text-[#94A3B8]">
              Password
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-[#64748B]" />
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full rounded-lg border border-[#263244] bg-[#0B1120] py-2 pr-3 pl-9 text-sm text-[#E2E8F0] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
                required
              />
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[#38BDF8] px-4 py-2.5 text-sm font-semibold text-[#0B1120] transition-colors hover:bg-[#38BDF8]/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] text-[#64748B]">
          Access is provisioned by a system administrator. All authentication events are logged.
        </p>
      </div>
    </div>
  );
}

