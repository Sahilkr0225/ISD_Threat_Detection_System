import { apiClient } from "./client";
import type { SecurityAuditLogListResponse } from "../types/api";

export interface AuditLogQuery {
  action?: string;
  outcome?: string;
  actor_user_id?: number;
  page?: number;
  page_size?: number;
}

export async function fetchAuditLogs(
  params: AuditLogQuery,
  signal?: AbortSignal
): Promise<SecurityAuditLogListResponse> {
  const { data } = await apiClient.get<SecurityAuditLogListResponse>("/audit-logs", {
    params,
    signal,
  });
  return data;
}

