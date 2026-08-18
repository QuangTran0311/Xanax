import type { IconName } from "../../components/Icon";
import type { HubMessageKey } from "./i18n";

export type HubTab =
  | "home"
  | "agents"
  | "skills"
  | "tasks"
  | "meeting"
  | "train"
  | "company-runner"
  | "auto-runner"
  | "assets"
  | "model"
  | "cost"
  | "settings";

export interface NavigationItem {
  tab: HubTab;
  label: HubMessageKey;
  icon: IconName;
  divider?: boolean;
}

// Sidebar và tiêu đề tab trình duyệt cùng đọc bảng này để tên route không trôi lệch nhau.
export const hubNavigation: NavigationItem[] = [
  { tab: "home", label: "nav.home", icon: "home" },
  { tab: "agents", label: "nav.agents", icon: "bot", divider: true },
  { tab: "skills", label: "nav.skills", icon: "puzzle" },
  { tab: "tasks", label: "nav.tasks", icon: "briefcase", divider: true },
  { tab: "meeting", label: "nav.meeting", icon: "meeting" },
  { tab: "train", label: "nav.train", icon: "teach", divider: true },
  { tab: "company-runner", label: "nav.company", icon: "workflow" },
  { tab: "auto-runner", label: "nav.automation", icon: "bolt" },
  { tab: "assets", label: "nav.assets", icon: "assets" },
  { tab: "model", label: "nav.model", icon: "brain" },
  { tab: "cost", label: "nav.cost", icon: "cost" },
  { tab: "settings", label: "nav.settings", icon: "settings", divider: true },
];

export const validHubTabs = new Set(hubNavigation.map((item) => item.tab));
