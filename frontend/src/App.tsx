import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingSkeleton } from "./components/common/FeedbackStates";
import { ToastProvider } from "./components/common/ToastContext";
import { AppShell } from "./components/layout/AppShell";

const Overview = lazy(() => import("./pages/Overview"));
const Employees = lazy(() => import("./pages/Employees"));
const EmployeeDetail = lazy(() => import("./pages/EmployeeDetail"));
const AlertCenter = lazy(() => import("./pages/AlertCenter"));
const AlertDetail = lazy(() => import("./pages/AlertDetail"));
const Investigations = lazy(() => import("./pages/Investigations"));
const ModelEvaluation = lazy(() => import("./pages/ModelEvaluation"));
const DatasetSystem = lazy(() => import("./pages/DatasetSystem"));
const NotFound = lazy(() => import("./pages/NotFound"));

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <AppShell>
            <Suspense fallback={<LoadingSkeleton rows={7} />}>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/employees" element={<Employees />} />
                <Route path="/employees/:employeeId" element={<EmployeeDetail />} />
                <Route path="/alerts" element={<AlertCenter />} />
                <Route path="/alerts/:alertId" element={<AlertDetail />} />
                <Route path="/investigations" element={<Investigations />} />
                <Route path="/model" element={<ModelEvaluation />} />
                <Route path="/system" element={<DatasetSystem />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </AppShell>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  );
}

