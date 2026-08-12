import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Navigate, NavLink, useLocation, useNavigate, useParams } from "react-router-dom";

import { Icon, type IconName } from "../../components/Icon";
import { useLanguage } from "../../store/language";
import { useTheme } from "../../store/theme";
import { HubProvider, useHub } from "./HubContext";
import { HubOverlays } from "./HubOverlays";
import { hubText, type HubMessageKey } from "./i18n";
import type { ProjectSubtab } from "./types";
import styles from "./HubPage.module.css";

const OverviewPage = lazy(() => import("./OverviewPage").then((module) => ({ default: module.OverviewPage })));
const AssetsPage = lazy(() => import("./AssetsPage").then((module) => ({ default: module.AssetsPage })));
const AgentsPage = lazy(() => import("./AgentsPage").then((module) => ({ default: module.AgentsPage })));
const SkillsPage = lazy(() => import("./SkillsPage").then((module) => ({ default: module.SkillsPage })));
const ProjectsPage = lazy(() => import("./ProjectsPage").then((module) => ({ default: module.ProjectsPage })));
const MeetingsPage = lazy(() => import("./MeetingsPage").then((module) => ({ default: module.MeetingsPage })));
const BrainPage = lazy(() => import("./BrainPage").then((module) => ({ default: module.BrainPage })));
const CostPage = lazy(() => import("./CostPage").then((module) => ({ default: module.CostPage })));
const SettingsPage = lazy(() => import("./SettingsPage").then((module) => ({ default: module.SettingsPage })));
const WorkspacePage = lazy(() => import("../workspace/WorkspacePage").then((module) => ({ default: module.WorkspacePage })));
const TaskrunnerPage = lazy(() => import("../taskrunner/TaskrunnerPage").then((module) => ({ default: module.TaskrunnerPage })));

const c = (name: string) => styles[name] ?? name;

type HubTab =
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

interface NavigationItem {
  tab: HubTab;
  label: HubMessageKey;
  icon: IconName;
  divider?: boolean;
}

const navigation: NavigationItem[] = [
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

const validTabs = new Set(navigation.map((item) => item.tab));

export function HubPage() {
  return (
    <HubProvider>
      <HubShell />
    </HubProvider>
  );
}

function HubShell() {
  const { tab } = useParams<{ tab?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const active = (tab || "home") as HubTab;
  const currentSubpath = location.pathname.split("/").slice(3).join("/");
  const { language } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const {
    username,
    sidebarCompact,
    setSidebarCompact,
    animations,
    loading,
  } = useHub();
  const [serverOnline, setServerOnline] = useState(true);
  const [visitedTabs, setVisitedTabs] = useState<Set<HubTab>>(() => new Set([active]));
  const [savedSubpaths, setSavedSubpaths] = useState<Partial<Record<HubTab, string>>>(() => ({
    [active]: currentSubpath,
  }));

  useEffect(() => {
    if (!validTabs.has(active)) return;
    setVisitedTabs((current) => current.has(active) ? current : new Set([...current, active]));
    setSavedSubpaths((current) => current[active] === currentSubpath
      ? current
      : { ...current, [active]: currentSubpath });
  }, [active, currentSubpath]);

  useEffect(() => {
    let activeEffect = true;
    const heartbeat = async () => {
      try {
        const response = await fetch("/api/auth/me", { cache: "no-store" });
        if (!activeEffect) return;
        setServerOnline(true);
        if (response.status === 401) navigate("/login", { replace: true });
      } catch {
        if (activeEffect) setServerOnline(false);
      }
    };
    void heartbeat();
    const timer = window.setInterval(() => void heartbeat(), 5000);
    return () => {
      activeEffect = false;
      window.clearInterval(timer);
    };
  }, [navigate]);

  const mountedTabs = useMemo(() => {
    const mounted = new Set(visitedTabs);
    if (validTabs.has(active)) mounted.add(active);
    return mounted;
  }, [active, visitedTabs]);

  if (!validTabs.has(active)) return <Navigate to="/hub" replace />;

  return (
    <div className={`${c("hubRoot")} ${sidebarCompact ? c("compactSidebar") : ""} ${animations ? "" : c("noAnimations")}`}>
      <aside className={c("sidebar")}>
        <div className={c("brand")}><span /><strong>Xanax</strong></div>
        <nav>
          {navigation.map((item) => (
            <div key={item.tab} className={item.divider ? c("navDivider") : ""}>
              <NavLink
                end={item.tab === "home"}
                to={item.tab === "home"
                  ? "/hub"
                  : `/hub/${item.tab}${savedSubpaths[item.tab] ? `/${savedSubpaths[item.tab]}` : ""}`}
                className={({ isActive }) => isActive
                  ? `${c("navItem")} ${c("navActive")}`
                  : c("navItem")}
                title={hubText(language, item.label)}
              >
                <Icon name={item.icon} />
                <span>{hubText(language, item.label)}</span>
              </NavLink>
            </div>
          ))}
        </nav>
        <button className={c("collapseButton")} onClick={() => setSidebarCompact(!sidebarCompact)}>
          <Icon name={sidebarCompact ? "arrowRight" : "arrowLeft"} />
          <span>{sidebarCompact ? "" : language === "vi" ? "Thu gọn" : "Collapse"}</span>
        </button>
      </aside>

      <div className={c("workspace")}>
        <header className={c("topbar")}>
          <span className={serverOnline ? c("online") : c("offline")}>
            <i />
            {serverOnline ? "Online" : hubText(language, "common.server_down")}
          </span>
          <div className={c("topbarActions")}>
            <button onClick={toggleTheme} title={theme === "light" ? "Dark" : "Light"}>
              <Icon name={theme === "light" ? "moon" : "sun"} />
            </button>
            <span><Icon name="user" />{loading ? "…" : username}</span>
          </div>
        </header>

        <main className={c("content")}>
          <Suspense fallback={<div className={c("routeLoading")}><Icon name="sync" /></div>}>
            {navigation.map((item) => {
              if (!mountedTabs.has(item.tab)) return null;
              const isActive = item.tab === active;
              const subpath = isActive ? currentSubpath : savedSubpaths[item.tab] || "";
              const fullHeight = item.tab === "train"
                || item.tab === "company-runner"
                || item.tab === "auto-runner";
              return (
                <section
                  key={item.tab}
                  className={`${c("tabPanel")} ${fullHeight ? c("tabPanelFull") : ""}`}
                  hidden={!isActive}
                  aria-hidden={!isActive}
                  data-hub-panel={item.tab}
                >
                  <HubTabContent tab={item.tab} subpath={subpath} />
                </section>
              );
            })}
          </Suspense>
        </main>
      </div>
      <HubOverlays />
    </div>
  );
}

function HubTabContent({ tab, subpath }: { tab: HubTab; subpath: string }) {
  const navigate = useNavigate();
  const {
    setCurrentProjectId,
    setCurrentProjectSubtab,
  } = useHub();

  const openProject = (projectId: number, projectSubtab: ProjectSubtab) => {
    setCurrentProjectId(projectId);
    setCurrentProjectSubtab(projectSubtab);
    navigate("/hub/tasks");
  };

  if (tab === "home") return <OverviewPage />;
  if (tab === "assets") return <AssetsPage />;
  if (tab === "agents") return <AgentsPage />;
  if (tab === "skills") return <SkillsPage />;
  if (tab === "tasks") return <ProjectsPage />;
  if (tab === "meeting") return <MeetingsPage />;
  if (tab === "model") return <BrainPage />;
  if (tab === "cost") return <CostPage />;
  if (tab === "settings") return <SettingsPage />;
  if (tab === "train") return <WorkspacePage embedded />;

  const taskId = Number(subpath.split("/")[0] || 0) || null;
  if (tab === "company-runner") {
    return (
      <TaskrunnerPage
        embedded
        kindOverride="company"
        taskIdOverride={taskId}
        basePath="/hub/company-runner"
        onOpenProject={openProject}
      />
    );
  }
  return (
    <TaskrunnerPage
      embedded
      kindOverride="automation"
      taskIdOverride={taskId}
      basePath="/hub/auto-runner"
      onOpenProject={openProject}
    />
  );
}
