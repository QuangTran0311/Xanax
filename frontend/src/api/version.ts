import { apiClient } from "./client";

export interface VersionResponse {
  version: string;
  commit?: string | null;
}

export const versionApi = {
  // Phải đọc lúc chạy: quy trình deploy không luôn build lại frontend khi chỉ
  // backend đổi, nên nhúng version bằng Vite sẽ giữ lại số của bản build cũ.
  current: () => apiClient.get<VersionResponse>("/version", { cache: "no-store" }),
};
