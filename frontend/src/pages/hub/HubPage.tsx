import { useEffect, useState } from "react";
import { Navigate, NavLink, useLocation, useNavigate, useParams } from "react-router-dom";

import { Icon, type IconName } from "../../components/Icon";
import { useLanguage } from "../../store/language";
import { useTheme } from "../../store/theme";
import { AssetsPage } from "./AssetsPage";
import { AgentsPage } from "./AgentsPage";
import { BrainPage } from "./BrainPage";
import { CostPage } from "./CostPage";
import { HubProvider, useHub } from "./HubContext";
import { HubOverlays } from "./HubOverlays";
import { hubText, type HubMessageKey } from "./i18n";
import { OverviewPage } from "./OverviewPage";
import { MeetingsPage } from "./MeetingsPage";
import { ProjectsPage } from "./ProjectsPage";
import { SettingsPage } from "./SettingsPage";
import { SkillsPage } from "./SkillsPage";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
type HubTab = "home" | "agents" | "skills" | "tasks" | "meeting" | "train" | "company-runner" | "auto-runner" | "assets" | "model" | "cost" | "settings";
interface NavigationItem { tab: HubTab; label: HubMessageKey; icon: IconName; divider?: boolean; }
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

export function HubPage() { return <HubProvider><HubShell /></HubProvider>; }

function HubShell() {
  const { tab } = useParams<{ tab?: string }>(); const location = useLocation(); const navigate = useNavigate();
  const active = (tab || "home") as HubTab; const { language } = useLanguage(); const { theme, toggleTheme } = useTheme();
  const { username, sidebarCompact, setSidebarCompact, animations, loading } = useHub(); const [serverOnline, setServerOnline] = useState(true);

  useEffect(() => {
    let activeEffect = true;
    const heartbeat = async () => {
      try { const response = await fetch("/api/auth/me", { cache: "no-store" }); if (!activeEffect) return; setServerOnline(true); if (response.status === 401) navigate("/v2/login", { replace: true }); }
      catch { if (activeEffect) setServerOnline(false); }
    };
    void heartbeat(); const timer = window.setInterval(() => void heartbeat(), 5000);
    return () => { activeEffect = false; window.clearInterval(timer); };
  }, [navigate]);

  if (!validTabs.has(active)) return <Navigate to="/v2/hub" replace />;
  const subpath = location.pathname.split("/").slice(4).join("/");
  return <div className={`${c("hubRoot")} ${sidebarCompact ? c("compactSidebar") : ""} ${animations ? "" : c("noAnimations")}`}>
    <aside className={c("sidebar")}>
      <div className={c("brand")}><span /><strong>Xanax</strong></div>
      <nav>{navigation.map((item) => <div key={item.tab} className={item.divider ? c("navDivider") : ""}><NavLink end={item.tab === "home"} to={item.tab === "home" ? "/v2/hub" : `/v2/hub/${item.tab}`} className={({ isActive }) => isActive ? `${c("navItem")} ${c("navActive")}` : c("navItem")} title={hubText(language, item.label)}><Icon name={item.icon} /><span>{hubText(language, item.label)}</span></NavLink></div>)}</nav>
      <button className={c("collapseButton")} onClick={() => setSidebarCompact(!sidebarCompact)}><Icon name={sidebarCompact ? "arrowRight" : "arrowLeft"} /><span>{sidebarCompact ? "" : language === "vi" ? "Thu gọn" : "Collapse"}</span></button>
    </aside>
    <div className={c("workspace")}>
      <header className={c("topbar")}><span className={serverOnline ? c("online") : c("offline")}><i />{serverOnline ? "Online" : hubText(language, "common.server_down")}</span><div className={c("topbarActions")}><button onClick={toggleTheme} title={theme === "light" ? "Dark" : "Light"}><Icon name={theme === "light" ? "moon" : "sun"} /></button><span><Icon name="user" />{loading ? "…" : username}</span></div></header>
      <main className={c("content")}><HubTabContent tab={active} subpath={subpath} /></main>
    </div>
    <HubOverlays />
  </div>;
}

function HubTabContent({ tab, subpath }: { tab: HubTab; subpath: string }) {
  const { language } = useLanguage();
  if (tab === "home") return <OverviewPage />;
  if (tab === "assets") return <AssetsPage />;
  if (tab === "agents") return <AgentsPage />;
  if (tab === "skills") return <SkillsPage />;
  if (tab === "tasks") return <ProjectsPage />;
  if (tab === "meeting") return <MeetingsPage />;
  if (tab === "model") return <BrainPage />;
  if (tab === "cost") return <CostPage />;
  if (tab === "settings") return <SettingsPage />;
  if (tab === "train") return <EmbeddedPage title={hubText(language, "nav.train")} src="/workspace?embed=1" />;
  if (tab === "company-runner") return <EmbeddedPage title={hubText(language, "nav.company")} src={`/taskrunner${subpath ? `/${encodeURIComponent(subpath)}` : ""}?embed=1&tab=company&ui=trigger-inspector-4`} />;
  if (tab === "auto-runner") return <EmbeddedPage title={hubText(language, "nav.automation")} src={`/taskrunner${subpath ? `/${encodeURIComponent(subpath)}` : ""}?embed=1&tab=automation&ui=trigger-inspector-4`} />;
  const item = navigation.find((entry) => entry.tab === tab)!;
  return <div className={c("page")}><header className={c("pageHeader")}><div><h1>{hubText(language, item.label)}</h1><p>{hubText(language, "placeholder.phase")}</p></div></header><div className={c("empty")}><Icon name={item.icon} /><span>{hubText(language, "placeholder.phase")}</span></div></div>;
}

function EmbeddedPage({ title, src }: { title: string; src: string }) { return <div className={c("embedded")}><iframe title={title} src={src} /></div>; }
