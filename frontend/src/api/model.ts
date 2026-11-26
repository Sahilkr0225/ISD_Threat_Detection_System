import { apiClient } from "./client";
import type { ModelInfoResponse, ModelMetricsResponse } from "../types/api";

export async function fetchModelInfo(signal?: AbortSignal): Promise<ModelInfoResponse> {
  const { data } = await apiClient.get<ModelInfoResponse>("/model/info", { signal });
  return data;
}

export async function fetchModelMetrics(signal?: AbortSignal): Promise<ModelMetricsResponse> {
  const { data } = await apiClient.get<ModelMetricsResponse>("/model/metrics", { signal });
  return data;
}

