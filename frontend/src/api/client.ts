import axios, { AxiosError } from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

apiClient.interceptors.request.use((config) => {
  const method = (config.method ?? "GET").toUpperCase();
  if (UNSAFE_METHODS.has(method)) {
    const csrfToken = readCookie("isd_csrf");
    if (csrfToken) {
      config.headers = config.headers ?? {};
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }
  return config;
});

type UnauthorizedHandler = () => void;
let onUnauthorizedHandler: UnauthorizedHandler | null = null;

export function registerUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorizedHandler = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const reqUrl = error.config?.url ?? "";
    if (
      status === 401 &&
      !reqUrl.includes("/auth/login") &&
      !reqUrl.includes("/auth/me") &&
      onUnauthorizedHandler
    ) {
      onUnauthorizedHandler();
    }
    return Promise.reject(error);
  }
);

export function extractApiErrorMessage(err: unknown): string {
  if (axios.isCancel(err)) {
    return "Request cancelled.";
  }
  const axiosErr = err as AxiosError<{ detail?: string }>;
  if (axiosErr.response) {
    const detail = axiosErr.response.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    return `Backend returned HTTP ${axiosErr.response.status}.`;
  }
  if (axiosErr.request) {
    return "Unable to reach the backend API. Verify the FastAPI server is running on 127.0.0.1:8000.";
  }
  return "An unexpected client error occurred.";
}
