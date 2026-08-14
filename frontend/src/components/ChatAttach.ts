import { apiClient } from "../api/client";

export interface ChatAttachment {
  id?: number;
  name: string;
  abs_path?: string;
  download_url?: string;
  mime?: string;
  uploading?: boolean;
  error?: string;
  preview_url?: string;
}

interface UploadResponse {
  id: number;
  abs_path: string;
  download_url: string;
  mime_type: string;
}

/** Keep this string contract character-for-character compatible with chat-attach.js. */
export function buildAttachmentBlock(attachments: ChatAttachment[]): string {
  const done = (attachments || []).filter((attachment) => attachment && !attachment.uploading && attachment.abs_path);
  if (!done.length) return "";
  const paths = done.map((attachment) => `- ${attachment.name} → ${attachment.abs_path}`).join("\n");
  const visible = done.map((attachment) => (attachment.mime || "").startsWith("image/")
    ? `![${attachment.name}](${attachment.download_url})`
    : `[📎 ${attachment.name}](${attachment.download_url})`).join("\n");
  return `\n\n<!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:\n${paths}\n-->\n\n${visible}`;
}

export async function uploadAttachment(file: File): Promise<ChatAttachment> {
  const form = new FormData();
  form.append("file", file);
  form.append("note", "Đính kèm trong khung chat");
  const uploaded = await apiClient.postForm<UploadResponse>("/assets/upload", form);
  return {
    id: uploaded.id,
    name: file.name,
    abs_path: uploaded.abs_path,
    download_url: uploaded.download_url,
    mime: uploaded.mime_type || file.type,
  };
}
