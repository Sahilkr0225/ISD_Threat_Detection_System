import { useCallback, useEffect, useState, type FormEvent } from "react";
import { KeyRound, UserPlus } from "lucide-react";
import {
  createUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
} from "../api/users";
import { extractApiErrorMessage } from "../api/client";
import { ErrorState, LoadingSkeleton } from "../components/common/FeedbackStates";
import { useToast } from "../components/common/ToastContext";
import { useAuth } from "../context/AuthContext";
import type { UserPublic, UserRole } from "../types/api";
import { formatTimestamp } from "../utils/formatters";

const ROLE_OPTIONS: UserRole[] = ["ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR"];

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const { addToast } = useToast();
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create user form state
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("SECURITY_ANALYST");
  const [creating, setCreating] = useState(false);

  // Password reset modal state
  const [resetTarget, setResetTarget] = useState<UserPublic | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [resetting, setResetting] = useState(false);

  const loadUsers = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    fetchUsers(signal)
      .then((res) => setUsers(res.items))
      .catch((err) => {
        if ((err as { name?: string }).name === "CanceledError") return;
        setError(extractApiErrorMessage(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadUsers(controller.signal);
    return () => controller.abort();
  }, [loadUsers]);

  const handleCreateUser = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const created = await createUser({
        username: username.trim(),
        display_name: displayName.trim(),
        password,
        role,
      });
      setUsers((prev) => [...prev, created]);
      setUsername("");
      setDisplayName("");
      setPassword("");
      setRole("SECURITY_ANALYST");
      addToast(`Created user ${created.username}`, "success");
    } catch (err) {
      addToast(extractApiErrorMessage(err), "error");
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (target: UserPublic, newRole: UserRole) => {
    try {
      const updated = await updateUser(target.user_id, { role: newRole });
      setUsers((prev) => prev.map((u) => (u.user_id === updated.user_id ? updated : u)));
      addToast(`Updated role for ${updated.username}`, "success");
    } catch (err) {
      addToast(extractApiErrorMessage(err), "error");
    }
  };

  const handleToggleActive = async (target: UserPublic) => {
    try {
      const updated = await updateUser(target.user_id, { is_active: !target.is_active });
      setUsers((prev) => prev.map((u) => (u.user_id === updated.user_id ? updated : u)));
      addToast(
        `${updated.username} is now ${updated.is_active ? "active" : "deactivated"}`,
        "success"
      );
    } catch (err) {
      addToast(extractApiErrorMessage(err), "error");
    }
  };

  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!resetTarget) return;
    setResetting(true);
    try {
      await resetUserPassword(resetTarget.user_id, resetPasswordValue);
      addToast(`Password reset for ${resetTarget.username}`, "success");
      setResetTarget(null);
      setResetPasswordValue("");
    } catch (err) {
      addToast(extractApiErrorMessage(err), "error");
    } finally {
      setResetting(false);
    }
  };

  if (loading) return <LoadingSkeleton rows={6} />;
  if (error) return <ErrorState message={error} onRetry={() => loadUsers()} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-[#E2E8F0]">User Management</h1>
        <p className="text-xs text-[#94A3B8]">
          Provision accounts, assign RBAC roles, and manage access. Minimum password length: 12 characters.
        </p>
      </div>

      {/* Create User Form */}
      <form
        onSubmit={handleCreateUser}
        className="rounded-xl border border-[#263244] bg-[#151E2E] p-5"
      >
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[#E2E8F0]">
          <UserPlus className="h-4 w-4 text-[#38BDF8]" />
          Create New User
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <input
            type="text"
            placeholder="Username (e.g. jdoe)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-2 text-xs text-[#E2E8F0] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
          />
          <input
            type="text"
            placeholder="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-2 text-xs text-[#E2E8F0] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
          />
          <input
            type="password"
            placeholder="Password (12+ chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={12}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-2 text-xs text-[#E2E8F0] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-2 text-xs text-[#E2E8F0] focus:border-[#38BDF8] focus:outline-none"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={creating}
            className="rounded-lg bg-[#38BDF8] px-4 py-2 text-xs font-semibold text-[#0B1120] hover:bg-[#38BDF8]/90 disabled:opacity-60"
          >
            {creating ? "Creating..." : "Create User"}
          </button>
        </div>
      </form>

      {/* Users Table */}
      <div className="overflow-x-auto rounded-xl border border-[#263244] bg-[#151E2E]">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-[#263244] bg-[#0B1120]/60 text-[11px] uppercase text-[#94A3B8]">
            <tr>
              <th className="px-4 py-3">Username</th>
              <th className="px-4 py-3">Display Name</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Login</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#263244]">
            {users.map((u) => {
              const isSelf = currentUser?.user_id === u.user_id;
              return (
                <tr key={u.user_id} className="hover:bg-[#0B1120]/40">
                  <td className="px-4 py-3 font-mono font-medium text-[#E2E8F0]">
                    {u.username}
                    {isSelf && (
                      <span className="ml-2 rounded bg-[#38BDF8]/15 px-1.5 py-0.5 text-[10px] text-[#38BDF8]">
                        You
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[#E2E8F0]">{u.display_name}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      disabled={isSelf}
                      onChange={(e) => handleRoleChange(u, e.target.value as UserRole)}
                      className="rounded border border-[#263244] bg-[#0B1120] px-2 py-1 text-xs text-[#E2E8F0] disabled:opacity-60"
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        u.is_active
                          ? "bg-emerald-500/15 text-emerald-300"
                          : "bg-red-500/15 text-red-300"
                      }`}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#94A3B8]">
                    {u.last_login_at ? formatTimestamp(u.last_login_at) : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setResetTarget(u);
                          setResetPasswordValue("");
                        }}
                        className="inline-flex items-center gap-1 rounded border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[11px] text-[#E2E8F0] hover:border-[#38BDF8]/50"
                      >
                        <KeyRound className="h-3 w-3" />
                        Reset Password
                      </button>
                      <button
                        type="button"
                        disabled={isSelf}
                        onClick={() => handleToggleActive(u)}
                        className="rounded border border-[#263244] bg-[#0B1120] px-2.5 py-1 text-[11px] text-[#E2E8F0] hover:border-amber-500/50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Password Reset Modal */}
      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
          <form
            onSubmit={handleResetPassword}
            className="w-full max-w-sm rounded-xl border border-[#263244] bg-[#151E2E] p-6"
          >
            <h2 className="text-sm font-semibold text-[#E2E8F0]">
              Reset Password for {resetTarget.username}
            </h2>
            <p className="mt-1 text-xs text-[#94A3B8]">
              This will immediately revoke active sessions for this user.
            </p>
            <input
              type="password"
              placeholder="New password (12+ chars)"
              value={resetPasswordValue}
              onChange={(e) => setResetPasswordValue(e.target.value)}
              minLength={12}
              required
              className="mt-4 w-full rounded-lg border border-[#263244] bg-[#0B1120] px-3 py-2 text-xs text-[#E2E8F0] focus:border-[#38BDF8] focus:outline-none"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setResetTarget(null)}
                className="rounded-lg border border-[#263244] px-3 py-1.5 text-xs text-[#94A3B8] hover:text-[#E2E8F0]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={resetting}
                className="rounded-lg bg-[#38BDF8] px-3 py-1.5 text-xs font-semibold text-[#0B1120] hover:bg-[#38BDF8]/90 disabled:opacity-60"
              >
                {resetting ? "Saving..." : "Save Password"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
