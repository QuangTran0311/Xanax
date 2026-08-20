import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { enqueueToast, setToastAnimations } from "../../components/Toast";
import { STORAGE_KEYS } from "../../store/keys";
import { useWebSocket } from "../../ws/useWebSocket";
import type {
  AgentRecord,
  MeetingRecord,
  ModelRecord,
  NotificationRecord,
  ProjectRecord,
  ProjectSubtab,
  SkillRecord,
  ToastKind,
} from "./types";

interface HubCollections {
  agents: AgentRecord[];
  skills: SkillRecord[];
  projects: ProjectRecord[];
  meetings: MeetingRecord[];
  modelPool: ModelRecord[];
}

interface ConfirmState { message: string; resolve: (value: boolean) => void; }
interface HubContextValue extends HubCollections {
  username: string;
  loading: boolean;
  currentProjectId: number | null;
  setCurrentProjectId: (id: number | null) => void;
  currentProjectSubtab: ProjectSubtab;
  setCurrentProjectSubtab: (subtab: ProjectSubtab) => void;
  sidebarCompact: boolean;
  setSidebarCompact: (value: boolean) => void;
  animations: boolean;
  setAnimations: (value: boolean) => void;
  refreshAgents: () => Promise<void>;
  refreshSkills: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  refreshMeetings: () => Promise<void>;
  refreshModelPool: () => Promise<void>;
  refreshAll: () => Promise<void>;
  notifications: NotificationRecord[];
  unreadNotificationCount: number;
  selectedNotification: NotificationRecord | null;
  openNotification: (notification: NotificationRecord) => void;
  closeNotification: () => void;
  refreshNotifications: () => Promise<void>;
  markNotificationRead: (id: number) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
  resolveNotification: (id: number) => Promise<void>;
  toast: (message: string, kind?: ToastKind) => void;
  confirm: (message: string) => Promise<boolean>;
  confirmState: ConfirmState | null;
  answerConfirm: (value: boolean) => void;
}

const HubContext = createContext<HubContextValue | null>(null);

interface NotificationWsEvent {
  type: string;
  unread_count?: number;
  notification?: NotificationRecord;
}

export function HubProvider({ children }: { children: React.ReactNode }) {
  const [collections, setCollections] = useState<HubCollections>({ agents: [], skills: [], projects: [], meetings: [], modelPool: [] });
  const [username, setUsername] = useState("—");
  const [loading, setLoading] = useState(true);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);
  const [currentProjectSubtab, setCurrentProjectSubtab] = useState<ProjectSubtab>("overview");
  const [sidebarCompact, setSidebarCompactState] = useState(() => localStorage.getItem(STORAGE_KEYS.sidebarIconMode) === "1");
  const [animations, setAnimationsState] = useState(() => localStorage.getItem(STORAGE_KEYS.animations) !== "0");
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null);
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);
  const [selectedNotification, setSelectedNotification] = useState<NotificationRecord | null>(null);

  const update = useCallback(<K extends keyof HubCollections>(key: K, value: HubCollections[K]) => {
    setCollections((current) => ({ ...current, [key]: value }));
  }, []);

  const refreshAgents = useCallback(async () => update("agents", (await apiClient.get<{ agents: AgentRecord[] }>("/agent-configs/")).agents || []), [update]);
  const refreshSkills = useCallback(async () => update("skills", (await apiClient.get<{ skills: SkillRecord[] }>("/skills/")).skills || []), [update]);
  const refreshProjects = useCallback(async () => update("projects", (await apiClient.get<{ projects: ProjectRecord[] }>("/projects/")).projects || []), [update]);
  const refreshMeetings = useCallback(async () => update("meetings", (await apiClient.get<{ meetings: MeetingRecord[] }>("/meetings/")).meetings || []), [update]);
  const refreshModelPool = useCallback(async () => update("modelPool", (await apiClient.get<{ models: ModelRecord[] }>("/model-pool")).models || []), [update]);

  const refreshAll = useCallback(async () => {
    await Promise.allSettled([refreshAgents(), refreshSkills(), refreshProjects(), refreshMeetings(), refreshModelPool()]);
  }, [refreshAgents, refreshMeetings, refreshModelPool, refreshProjects, refreshSkills]);

  const refreshNotifications = useCallback(async () => {
    const [list, count] = await Promise.all([
      apiClient.get<{ notifications: NotificationRecord[] }>("/notifications?limit=30"),
      apiClient.get<{ count: number }>("/notifications/unread-count"),
    ]);
    setNotifications(list.notifications || []);
    setUnreadNotificationCount(Number(count.count || 0));
    setSelectedNotification((current) => current
      ? (list.notifications || []).find((item) => item.id === current.id) || current
      : null);
  }, []);

  const onNotificationMessage = useCallback((event: NotificationWsEvent) => {
    if (typeof event.unread_count === "number") setUnreadNotificationCount(event.unread_count);
    if (event.type === "notification.created" && event.notification) {
      enqueueToast(
        event.notification.title,
        event.notification.severity === "error" ? "error" : "info",
      );
    }
    if (event.type !== "pong") void refreshNotifications();
  }, [refreshNotifications]);

  const notificationSocket = useWebSocket<NotificationWsEvent>({
    path: "/ws/notifications",
    onMessage: onNotificationMessage,
    onOpen: () => { void refreshNotifications(); },
  });

  useEffect(() => {
    void refreshNotifications().catch(() => undefined);
  }, [refreshNotifications]);

  useEffect(() => {
    if (notificationSocket.state === "open" || notificationSocket.state === "auth-error") return;
    const timer = window.setInterval(() => {
      void refreshNotifications().catch(() => undefined);
    }, 15_000);
    return () => window.clearInterval(timer);
  }, [notificationSocket.state, refreshNotifications]);

  const markNotificationRead = useCallback(async (id: number) => {
    const updated = await apiClient.post<NotificationRecord>(`/notifications/${id}/read`);
    setNotifications((current) => current.map((item) => item.id === id ? updated : item));
    setSelectedNotification((current) => current?.id === id ? updated : current);
    setUnreadNotificationCount((current) => Math.max(0, current - 1));
  }, []);

  const markAllNotificationsRead = useCallback(async () => {
    await apiClient.post("/notifications/read-all");
    setNotifications((current) => current.map((item) => item.status === "unread"
      ? { ...item, status: "read" as const, read_at: new Date().toISOString() }
      : item));
    setSelectedNotification((current) => current?.status === "unread"
      ? { ...current, status: "read" as const, read_at: new Date().toISOString() }
      : current);
    setUnreadNotificationCount(0);
  }, []);

  const resolveNotification = useCallback(async (id: number) => {
    const updated = await apiClient.post<NotificationRecord>(`/notifications/${id}/resolve`);
    setNotifications((current) => current.map((item) => item.id === id ? updated : item));
    setSelectedNotification((current) => current?.id === id ? updated : current);
    void refreshNotifications();
  }, [refreshNotifications]);

  const openNotification = useCallback((notification: NotificationRecord) => {
    setSelectedNotification(notification);
  }, []);
  const closeNotification = useCallback(() => setSelectedNotification(null), []);

  useEffect(() => {
    let active = true;
    void Promise.all([apiClient.get<{ username: string }>("/auth/me"), refreshAll()])
      .then(([me]) => { if (active) setUsername(me.username || "—"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refreshAll]);

  const toast = useCallback((message: string, kind: ToastKind = "info") => {
    enqueueToast(message, kind);
  }, []);

  const confirm = useCallback((message: string) => new Promise<boolean>((resolve) => setConfirmState({ message, resolve })), []);
  const answerConfirm = useCallback((value: boolean) => {
    setConfirmState((current) => { current?.resolve(value); return null; });
  }, []);
  const setSidebarCompact = useCallback((value: boolean) => {
    setSidebarCompactState(value); localStorage.setItem(STORAGE_KEYS.sidebarIconMode, value ? "1" : "0");
  }, []);
  const setAnimations = useCallback((value: boolean) => {
    setAnimationsState(value);
    setToastAnimations(value);
    localStorage.setItem(STORAGE_KEYS.animations, value ? "1" : "0");
  }, []);

  useEffect(() => setToastAnimations(animations), [animations]);

  const value = useMemo<HubContextValue>(() => ({
    ...collections, username, loading, currentProjectId, setCurrentProjectId,
    currentProjectSubtab, setCurrentProjectSubtab,
    sidebarCompact, setSidebarCompact, animations, setAnimations,
    refreshAgents, refreshSkills, refreshProjects, refreshMeetings, refreshModelPool, refreshAll,
    notifications, unreadNotificationCount, selectedNotification,
    openNotification, closeNotification, refreshNotifications,
    markNotificationRead, markAllNotificationsRead, resolveNotification,
    toast, confirm, confirmState, answerConfirm,
  }), [collections, username, loading, currentProjectId, currentProjectSubtab, sidebarCompact, animations, refreshAgents, refreshSkills, refreshProjects, refreshMeetings, refreshModelPool, refreshAll, notifications, unreadNotificationCount, selectedNotification, openNotification, closeNotification, refreshNotifications, markNotificationRead, markAllNotificationsRead, resolveNotification, toast, confirm, confirmState, answerConfirm, setSidebarCompact, setAnimations]);

  return <HubContext.Provider value={value}>{children}</HubContext.Provider>;
}

export function useHub(): HubContextValue {
  const value = useContext(HubContext);
  if (!value) throw new Error("useHub phải nằm trong HubProvider");
  return value;
}
