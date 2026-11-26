import { Link } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function AccessDenied() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-red-500/30 bg-red-500/10">
        <ShieldOff className="h-7 w-7 text-red-400" />
      </div>
      <h1 className="text-xl font-semibold text-[#E2E8F0]">Access Restricted</h1>
      <p className="mt-2 max-w-md text-sm text-[#94A3B8]">
        Your current role ({user?.role ?? "Unknown"}) does not have permission to view this page.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg border border-[#263244] bg-[#151E2E] px-4 py-2 text-xs font-medium text-[#E2E8F0] hover:border-[#38BDF8]/50 hover:text-[#38BDF8]"
      >
        Return to Security Overview
      </Link>
    </div>
  );
}

