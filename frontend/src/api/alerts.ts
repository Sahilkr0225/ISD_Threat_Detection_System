import { apiClient } from "./client";
import type {
  AlertDetailResponse,
  AlertHistoryResponse,
  AlertListResponse,
  AlertStatus,
  AlertStatusUpdateRequest,
  PriorityLevel,
} from "../types/api";

export interface AlertsQueryParams {
  priority?: PriorityLevel | "";
  status?: AlertStatus | "";
  employee_id?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: "anomaly_score" | "activity_date";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export async function fetchAlerts(
  params: AlertsQueryParams,
  signal?: AbortSignal
): Promise<AlertListResponse> {
  const cleanParams: Record<string, string | number> = {};
  if (params.priority) cleanParams.priority = params.priority;
  if (params.status) cleanParams.status = params.status;
  if (params.employee_id?.trim()) cleanParams.employee_id = params.employee_id.trim();
  if (params.date_from) cleanParams.date_from = params.date_from;
  if (params.date_to) cleanParams.date_to = params.date_to;
  if (params.sort_by) cleanParams.sort_by = params.sort_by;
  if (params.sort_order) cleanParams.sort_order = params.sort_order;
  if (params.page) cleanParams.page = params.page;
  if (params.page_size) cleanParams.page_size = params.page_size;

  const { data } = await apiClient.get<AlertListResponse>("/alerts", {
    params: cleanParams,
    signal,
  });
  return data;
}

export async function fetchAlertDetail(
  alertId: number,
  signal?: AbortSignal
): Promise<AlertDetailResponse> {
  const { data } = await apiClient.get<AlertDetailResponse>(`/alerts/${alertId}`, {
    signal,
  });
  return data;
}

export async function fetchAlertHistory(
  alertId: number,
  signal?: AbortSignal
): Promise<AlertHistoryResponse> {
  const { data } = await apiClient.get<AlertHistoryResponse>(`/alerts/${alertId}/history`, {
    signal,
  });
  return data;
}

export async function updateAlertStatus(
  alertId: number,
  payload: AlertStatusUpdateRequest
): Promise<AlertDetailResponse> {
  const { data } = await apiClient.patch<AlertDetailResponse>(
    `/alerts/${alertId}/status`,
    payload
  );
  return data;
}

