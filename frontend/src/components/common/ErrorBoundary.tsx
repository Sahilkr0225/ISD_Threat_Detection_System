import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Intentionally suppressed from UI to avoid exposing internal details
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-[#0B1120] p-6 text-center">
          <AlertTriangle className="h-10 w-10 text-red-400" />
          <h1 className="mt-3 text-lg font-semibold text-[#E2E8F0]">
            Unexpected Application Error
          </h1>
          <p className="mt-1 text-xs text-[#94A3B8]">
            Please reload the page or verify backend connectivity.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-[#38BDF8] px-4 py-2 text-xs font-semibold text-[#0B1120]"
          >
            Reload Application
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

