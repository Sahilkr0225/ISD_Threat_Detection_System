import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingSkeleton } from "./components/common/FeedbackStates";
import { ToastProvider } from "./components/common/ToastContext";
import { AppShell } from "./components/layout/AppShell";
import { AuthProvider } from "./context/AuthContext";

const Login = lazy(() => import("./pages/Login"));
const Overview = lazy(() => import("./pages/Overview"));
const Employees = lazy(() => import("./pages/Employees"));
const EmployeeDetail = lazy(() => import("./pages/EmployeeDetail"));
const AlertCenter = lazy(() => import("./pages/AlertCenter"));
const AlertDetail = lazy(() => import("./pages/AlertDetail"));
const Investigations = lazy(() => import("./pages/Investigations"));
const ModelEvaluation = lazy(() => import("./pages/ModelEvaluation"));
const DatasetSystem = lazy(() => import("./pages/DatasetSystem"));
const UserManagement = lazy(() => import("./pages/UserManagement"));
const AuditLogs = lazy(() => import("./pages/AuditLogs"));
const NotFound = lazy(() => import("./pages/NotFound"));

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<LoadingSkeleton rows={7} />}>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                  path="/*"
                  element={
                    <ProtectedRoute>
                      <AppShell>
                        <Routes>
                          <Route path="/" element={<Overview />} />
                          <Route path="/employees" element={<Employees />} />
                          <Route path="/employees/:employeeId" element={<EmployeeDetail />} />
                          <Route path="/alerts" element={<AlertCenter />} />
                          <Route path="/alerts/:alertId" element={<AlertDetail />} />
                          <Route path="/investigations" element={<Investigations />} />
                          <Route
                            path="/model"
                            element={
                              <ProtectedRoute allowedRoles={["ADMINISTRATOR", "AUDITOR"]}>
                                <ModelEvaluation />
                              </ProtectedRoute>
                            }
                          />
                          <Route
                            path="/system"
                            element={
                              <ProtectedRoute allowedRoles={["ADMINISTRATOR", "AUDITOR"]}>
                                <DatasetSystem />
                              </ProtectedRoute>
                            }
                          />
                          <Route
                            path="/users"
                            element={
                              <ProtectedRoute allowedRoles={["ADMINISTRATOR"]}>
                                <UserManagement />
                              </ProtectedRoute>
                            }
                          />
                          <Route
                            path="/audit-logs"
                            element={
                              <ProtectedRoute allowedRoles={["ADMINISTRATOR", "AUDITOR"]}>
                                <AuditLogs />
                              </ProtectedRoute>
                            }
                          />
                          <Route path="*" element={<NotFound />} />
                        </Routes>
                      </AppShell>
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
