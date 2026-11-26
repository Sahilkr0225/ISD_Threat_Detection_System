import { apiClient } from "./client";
import type {
  EmployeeDetailResponse,
  EmployeeHistoryResponse,
  EmployeeListResponse,
} from "../types/api";

export async function fetchEmployees(
  params: {
    department?: string;
    search?: string;
    page?: number;
    page_size?: number;
  },
  signal?: AbortSignal
): Promise<EmployeeListResponse> {
  const { data } = await apiClient.get<EmployeeListResponse>("/employees", {
    params,
    signal,
  });
  return data;
}

export async function fetchEmployeeDetail(
  employeeId: string,
  signal?: AbortSignal
): Promise<EmployeeDetailResponse> {
  const { data } = await apiClient.get<EmployeeDetailResponse>(
    `/employees/${encodeURIComponent(employeeId)}`,
    { signal }
  );
  return data;
}

export async function fetchEmployeeHistory(
  employeeId: string,
  params: { page?: number; page_size?: number },
  signal?: AbortSignal
): Promise<EmployeeHistoryResponse> {
  const { data } = await apiClient.get<EmployeeHistoryResponse>(
    `/employees/${encodeURIComponent(employeeId)}/history`,
    { params, signal }
  );
  return data;
}

