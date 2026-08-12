import { apiClient } from "../api/client";
import type { CurrentUser, LoginRequest, LoginResponse } from "../api/types";

export const sessionApi = {
  login: (credentials: LoginRequest) => apiClient.post<LoginResponse>("/auth/login", credentials),
  current: () => apiClient.get<CurrentUser>("/auth/me"),
  logout: () => apiClient.post<{ ok: true }>("/auth/logout"),
};
