import { apiClient } from "./client";
import type { DataSummaryResponse } from "../types/api";

export async function fetchDataSummary(signal?: AbortSignal): Promise<DataSummaryResponse> {
  const { data } = await apiClient.get<DataSummaryResponse>("/data/summary", { signal });
  return data;
}

