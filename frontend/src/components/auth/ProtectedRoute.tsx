import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { LoadingSkeleton } from "../common/FeedbackStates";
import { useAuth } from "../../context/AuthContext";
import type { UserRole } from "../../types/api";
import AccessDenied from "../../pages/AccessDenied";

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: UserRole[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B1120] p-6">
        <LoadingSkeleton rows={6} />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}

