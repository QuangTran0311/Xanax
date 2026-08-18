import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, NavLink, useLocation, useNavigate, useParams } from "react-router-dom";

import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { sessionApi } from "../../store/session";
import { useTheme } from "../../store/theme";
import { HubProvider, useHub } from "./HubContext";
import { HubOverlays } from "./HubOverlays";
import { hubText } from "./i18n";
import { hubNavigation as navigation, validHubTabs as validTabs, type HubTab } from "./navigation";
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
  const tooltip = useTooltipText();
  const { theme, toggleTheme } = useTheme();
  const {
    username,
    sidebarCompact,
    setSidebarCompact,
    animations,
    loading,
  } = useHub();
  const [serverOnline, setServerOnline] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
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

  useEffect(() => setMobileSidebarOpen(false), [location.pathname]);

  useEffect(() => {
    if (!accountMenuOpen) return;
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!accountMenuRef.current?.contains(event.target as Node)) setAccountMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccountMenuOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountMenuOpen]);

  const mountedTabs = useMemo(() => {
    const mounted = new Set(visitedTabs);
    if (validTabs.has(active)) mounted.add(active);
    return mounted;
  }, [active, visitedTabs]);

  if (!validTabs.has(active)) return <Navigate to="/hub" replace />;

  return (
    <div className={`${c("hubRoot")} ${sidebarCompact ? c("compactSidebar") : ""} ${mobileSidebarOpen ? c("mobileSidebarOpen") : ""} ${animations ? "" : c("noAnimations")}`}>
      <aside className={c("sidebar")} aria-label={language === "vi" ? "Điều hướng chính" : "Main navigation"}>
        <div className={c("brand")} title="Xanax"><span /><strong>Xanax</strong><small>AI OPERATIONS</small></div>
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
                onClick={() => setMobileSidebarOpen(false)}
              >
                <Icon name={item.icon} />
                <span>{hubText(language, item.label)}</span>
              </NavLink>
            </div>
          ))}
        </nav>
        <div className={serverOnline ? c("sidebarHealth") : `${c("sidebarHealth")} ${c("sidebarHealthOffline")}`} title={serverOnline ? (language === "vi" ? "Hệ thống ổn định" : "System healthy") : hubText(language, "common.server_down")}>
          <span><i /></span>
          <div><strong>{serverOnline ? (language === "vi" ? "Hệ thống ổn định" : "System healthy") : hubText(language, "common.server_down")}</strong><small>{serverOnline ? (language === "vi" ? "Tất cả dịch vụ hoạt động" : "All services operational") : (language === "vi" ? "Đang thử kết nối lại" : "Trying to reconnect")}</small></div>
        </div>
        <Tooltip label={tooltip(sidebarCompact ? "tooltip.hub.sidebar_expand" : "tooltip.hub.sidebar_collapse")}>
          <button
            className={c("collapseButton")}
            onClick={() => setSidebarCompact(!sidebarCompact)}
            aria-label={tooltip(sidebarCompact ? "tooltip.hub.sidebar_expand" : "tooltip.hub.sidebar_collapse")}
          >
            <Icon name={sidebarCompact ? "arrowRight" : "arrowLeft"} />
            <span>{language === "vi" ? "Thu gọn" : "Collapse"}</span>
          </button>
        </Tooltip>
      </aside>

      <Tooltip label={tooltip("tooltip.hub.navigation_close")}>
        <button
          className={c("sidebarScrim")}
          aria-label={tooltip("tooltip.hub.navigation_close")}
          onClick={() => setMobileSidebarOpen(false)}
        />
      </Tooltip>

      <div className={c("workspace")}>
        <header className={c("topbar")}>
          <div className={c("topbarLeading")}>
            <Tooltip label={tooltip(mobileSidebarOpen ? "tooltip.hub.navigation_close" : "tooltip.hub.navigation_open")}>
              <button
                className={c("mobileMenuButton")}
                onClick={() => setMobileSidebarOpen((current) => !current)}
                aria-expanded={mobileSidebarOpen}
                aria-label={tooltip(mobileSidebarOpen ? "tooltip.hub.navigation_close" : "tooltip.hub.navigation_open")}
              >
                <Icon name={mobileSidebarOpen ? "close" : "sliders"} />
              </button>
            </Tooltip>
            <span className={serverOnline ? c("online") : c("offline")}>
              <i />
              {serverOnline ? (language === "vi" ? "Hệ thống trực tuyến" : "System online") : hubText(language, "common.server_down")}
            </span>
          </div>
          <div className={c("topbarActions")}>
            <Tooltip label={tooltip(theme === "light" ? "tooltip.hub.theme_dark" : "tooltip.hub.theme_light")}>
              <button
                className={c("topbarIconButton")}
                onClick={toggleTheme}
                aria-label={tooltip(theme === "light" ? "tooltip.hub.theme_dark" : "tooltip.hub.theme_light")}
              >
                <Icon name={theme === "light" ? "moon" : "sun"} />
              </button>
            </Tooltip>
            <div className={c("accountMenu")} ref={accountMenuRef}>
              <Tooltip label={tooltip(accountMenuOpen ? "tooltip.hub.account_close" : "tooltip.hub.account_open")}>
                <button
                  className={c("accountSummary")}
                  type="button"
                  aria-haspopup="menu"
                  aria-expanded={accountMenuOpen}
                  onClick={() => setAccountMenuOpen((current) => !current)}
                >
                  <span><Icon name="user" /></span>
                  <strong>{loading ? "…" : username}</strong>
                </button>
              </Tooltip>
              {accountMenuOpen && (
                <div className={c("accountDropdown")} role="menu">
                  <Tooltip label={tooltip("tooltip.common.logout")}>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => void sessionApi.logout().finally(() => navigate("/login", { replace: true }))}
                    >
                      {hubText(language, "common.logout")}
                    </button>
                  </Tooltip>
                </div>
              )}
            </div>
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
                || item.tab === "auto-runner"
                || item.tab === "meeting";
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
