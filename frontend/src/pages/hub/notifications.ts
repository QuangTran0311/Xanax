import type { Language } from "../../store/language";
import type { NotificationRecord } from "./types";

const REASON_TEXT: Record<string, Record<Language, string>> = {
  no_matching_agent: {
    vi: "Không tìm thấy nhân viên AI phù hợp với công việc này.",
    en: "No suitable AI employee was found for this work item.",
  },
};

export function notificationBody(notification: NotificationRecord, language: Language): string {
  const reason = typeof notification.payload.reason === "string"
    ? notification.payload.reason
    : "";
  return REASON_TEXT[reason]?.[language] || notification.body || reason.replaceAll("_", " ");
}

export function notificationKindLabel(notification: NotificationRecord, language: Language): string {
  const vi = language === "vi";
  const labels: Record<string, [string, string]> = {
    work_item_unmatched: ["Công việc cần người phù hợp", "Work item needs a match"],
    workflow_failed: ["Quy trình thất bại", "Workflow failed"],
    experiment_completed: ["Thí nghiệm hoàn tất", "Experiment completed"],
    experiment_judge_error: ["Thí nghiệm có lỗi chấm", "Experiment judge error"],
    model_pool_auth_failed: ["Model cần đăng nhập lại", "Model sign-in required"],
  };
  const pair = labels[notification.kind];
  return pair ? pair[vi ? 0 : 1] : notification.kind.replaceAll("_", " ");
}
