import axios, { AxiosError } from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

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

