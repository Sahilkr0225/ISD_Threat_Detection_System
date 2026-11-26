import { apiClient } from "./client";
import type {
  CreateUserPayload,
  UpdateUserPayload,
  UserListResponse,
  UserPublic,
} from "../types/api";

export async function fetchUsers(signal?: AbortSignal): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>("/users", { signal });
  return data;
}

export async function createUser(payload: CreateUserPayload): Promise<UserPublic> {
  const { data } = await apiClient.post<UserPublic>("/users", payload);
  return data;
}

export async function updateUser(
  userId: number,
  payload: UpdateUserPayload
): Promise<UserPublic> {
  const { data } = await apiClient.patch<UserPublic>(`/users/${userId}`, payload);
  return data;
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<void> {
  await apiClient.post(`/users/${userId}/reset-password`, {
    new_password: newPassword,
  });
}

