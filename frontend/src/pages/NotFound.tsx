import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-3xl font-bold text-[#38BDF8]">404</h1>
      <p className="mt-2 text-sm text-[#E2E8F0]">Page not found in the SOC Console.</p>
      <Link
        to="/"
        className="mt-4 rounded-lg bg-[#38BDF8] px-4 py-2 text-xs font-semibold text-[#0B1120]"
      >
        Return to Overview
      </Link>
    </div>
  );
}

