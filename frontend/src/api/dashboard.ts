import { apiClient } from "./client";
import type {
  DashboardSummaryResponse,
  DashboardTrendsResponse,
  HealthResponse,
} from "../types/api";

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health", { signal });
  return data;
}

export async function fetchDashboardSummary(
  signal?: AbortSignal
): Promise<DashboardSummaryResponse> {
  const { data } = await apiClient.get<DashboardSummaryResponse>("/dashboard/summary", {
    signal,
  });
  return data;
}

export async function fetchDashboardTrends(
  params?: { date_from?: string; date_to?: string },
  signal?: AbortSignal
): Promise<DashboardTrendsResponse> {
  const { data } = await apiClient.get<DashboardTrendsResponse>("/dashboard/trends", {
    params,
    signal,
  });
  return data;
}

