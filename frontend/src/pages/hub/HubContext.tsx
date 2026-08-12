import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { STORAGE_KEYS } from "../../store/keys";
import type {
  AgentRecord,
  MeetingRecord,
  ModelRecord,
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
interface ToastState { id: number; message: string; kind: ToastKind; }

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
  toast: (message: string, kind?: ToastKind) => void;
  confirm: (message: string) => Promise<boolean>;
  toastState: ToastState | null;
  confirmState: ConfirmState | null;
  answerConfirm: (value: boolean) => void;
}

const HubContext = createContext<HubContextValue | null>(null);

export function HubProvider({ children }: { children: React.ReactNode }) {
  const [collections, setCollections] = useState<HubCollections>({ agents: [], skills: [], projects: [], meetings: [], modelPool: [] });
  const [username, setUsername] = useState("—");
  const [loading, setLoading] = useState(true);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);
  const [currentProjectSubtab, setCurrentProjectSubtab] = useState<ProjectSubtab>("overview");
  const [sidebarCompact, setSidebarCompactState] = useState(() => localStorage.getItem(STORAGE_KEYS.sidebarIconMode) === "1");
  const [animations, setAnimationsState] = useState(() => localStorage.getItem(STORAGE_KEYS.animations) !== "0");
  const [toastState, setToastState] = useState<ToastState | null>(null);
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null);
  const toastTimer = useRef<number | null>(null);

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

  useEffect(() => {
    let active = true;
    void Promise.all([apiClient.get<{ username: string }>("/auth/me"), refreshAll()])
      .then(([me]) => { if (active) setUsername(me.username || "—"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refreshAll]);

  useEffect(() => () => { if (toastTimer.current !== null) window.clearTimeout(toastTimer.current); }, []);

  const toast = useCallback((message: string, kind: ToastKind = "info") => {
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
    const id = Date.now();
    setToastState({ id, message, kind });
    toastTimer.current = window.setTimeout(() => setToastState((current) => current?.id === id ? null : current), 3500);
  }, []);

  const confirm = useCallback((message: string) => new Promise<boolean>((resolve) => setConfirmState({ message, resolve })), []);
  const answerConfirm = useCallback((value: boolean) => {
    setConfirmState((current) => { current?.resolve(value); return null; });
  }, []);
  const setSidebarCompact = useCallback((value: boolean) => {
    setSidebarCompactState(value); localStorage.setItem(STORAGE_KEYS.sidebarIconMode, value ? "1" : "0");
  }, []);
  const setAnimations = useCallback((value: boolean) => {
    setAnimationsState(value); localStorage.setItem(STORAGE_KEYS.animations, value ? "1" : "0");
  }, []);

  const value = useMemo<HubContextValue>(() => ({
    ...collections, username, loading, currentProjectId, setCurrentProjectId,
    currentProjectSubtab, setCurrentProjectSubtab,
    sidebarCompact, setSidebarCompact, animations, setAnimations,
    refreshAgents, refreshSkills, refreshProjects, refreshMeetings, refreshModelPool, refreshAll,
    toast, confirm, toastState, confirmState, answerConfirm,
  }), [collections, username, loading, currentProjectId, currentProjectSubtab, sidebarCompact, animations, refreshAgents, refreshSkills, refreshProjects, refreshMeetings, refreshModelPool, refreshAll, toast, confirm, toastState, confirmState, answerConfirm, setSidebarCompact, setAnimations]);

  return <HubContext.Provider value={value}>{children}</HubContext.Provider>;
}

export function useHub(): HubContextValue {
  const value = useContext(HubContext);
  if (!value) throw new Error("useHub phải nằm trong HubProvider");
  return value;
}
