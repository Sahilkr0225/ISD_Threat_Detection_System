import { apiClient } from "./client";
import type { LoginResponse, SessionMeResponse } from "../types/api";

export async function fetchCsrfToken(signal?: AbortSignal): Promise<{ csrf_token: string }> {
  const { data } = await apiClient.get<{ csrf_token: string }>("/auth/csrf", { signal });
  return data;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/login", { username, password });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function fetchCurrentSession(signal?: AbortSignal): Promise<SessionMeResponse> {
  const { data } = await apiClient.get<SessionMeResponse>("/auth/me", { signal });
  return data;
}

export async function changeOwnPassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  await apiClient.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

