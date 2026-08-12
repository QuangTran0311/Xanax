import { useEffect, useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from "chart.js";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { useLanguage } from "../../store/language";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import type { CostReport, HubRecord } from "./types";
import styles from "./HubPage.module.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);
const c = (name: string) => styles[name] ?? name;

interface WorkflowRun extends HubRecord { task_name?: string; started_at?: string; }
interface RecentRoom { meeting_name?: string; last_sender?: string; last_content?: string; last_created_at?: string; message_count?: number; }
interface Alert { id?: number; title?: string; reason?: string; status?: string; created_at?: string; }
interface CostOverview { today?: { totals?: Record<string, number> }; }

function isoLocal(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function parseDate(value?: string): Date | null {
  if (!value) return null;
  const parsed = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : value.replace(" ", "T") + "Z");
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatMoney(totals: Record<string, number> = {}): string {
  const values = Object.entries(totals);
  return values.length ? values.map(([currency, value]) => `${Number(value).toLocaleString("vi-VN", { maximumFractionDigits: 4 })} ${currency}`).join(" · ") : "0";
}

export function OverviewPage() {
  const { language } = useLanguage();
  const { agents, skills, meetings } = useHub();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [rooms, setRooms] = useState<RecentRoom[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [overview, setOverview] = useState<CostOverview | null>(null);
  const [costReport, setCostReport] = useState<CostReport | null>(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const end = new Date(); const start = new Date(end); start.setDate(start.getDate() - 6);
    void Promise.all([
      apiClient.get<{ runs: WorkflowRun[] }>("/workflow/runs?limit=20").catch(() => ({ runs: [] })),
      apiClient.get<{ rooms: RecentRoom[] }>("/meetings/messages/recent?limit=8").catch(() => ({ rooms: [] })),
      apiClient.get<{ alerts: Alert[] }>("/projects/items/alerts").catch(() => ({ alerts: [] })),
      apiClient.get<CostOverview>("/model-pool/cost/overview").catch(() => null),
      apiClient.get<CostReport>(`/model-pool/cost/report?period=day&date_from=${isoLocal(start)}&date_to=${isoLocal(end)}`).catch(() => null),
    ]).then(([runData, roomData, alertData, costOverview, report]) => {
      setRuns(runData.runs || []); setRooms(roomData.rooms || []);
      setAlerts((alertData.alerts || []).filter((item) => !item.status || item.status === "open"));
      setOverview(costOverview); setCostReport(report);
    });
  }, []);

  const today = isoLocal(now);
  const todayRuns = runs.filter((run) => { const date = parseDate(run.started_at || run.created_at); return date && isoLocal(date) === today; });
  const finished = todayRuns.filter((run) => run.status === "completed" || run.status === "failed");
  const completed = finished.filter((run) => run.status === "completed").length;
  const running = runs.filter((run) => run.status === "running");

  const chartData = useMemo(() => {
    const byDate: Record<string, number> = {};
    for (const row of costReport?.rows || []) byDate[row.bucket_from] = (byDate[row.bucket_from] || 0) + Number(row.estimated_cost || 0);
    const labels: string[] = []; const values: number[] = [];
    const cursor = new Date(); cursor.setDate(cursor.getDate() - 6);
    for (let index = 0; index < 7; index += 1) {
      const iso = isoLocal(cursor); labels.push(cursor.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { weekday: "short", day: "2-digit" }));
      values.push(Number((byDate[iso] || 0).toFixed(4))); cursor.setDate(cursor.getDate() + 1);
    }
    return { labels, datasets: [{ label: hubText(language, "overview.cost_trend"), data: values, backgroundColor: "#5b8f7f", borderRadius: 7 }] };
  }, [costReport, language]);

  return <div className={c("page")}>
    <header className={c("pageHeader")}><div><h1>{hubText(language, "overview.title")}</h1><p>{hubText(language, "overview.subtitle")}</p></div><time>{now.toLocaleString(language === "vi" ? "vi-VN" : "en-US", { timeZone: "Asia/Ho_Chi_Minh" })}</time></header>
    <section className={c("statGrid")}>
      <Stat icon="people" label={hubText(language, "overview.agents")} value={String(agents.length)} detail={`${agents.filter((agent) => agent.enabled !== 0 && agent.enabled !== false).length} active`} />
      <Stat icon="sync" label={hubText(language, "overview.running")} value={String(running.length)} detail={`${todayRuns.length} today`} />
      <Stat icon="check" label={hubText(language, "overview.success")} value={finished.length ? `${Math.round(completed / finished.length * 100)}%` : "—"} detail={`${completed}/${finished.length}`} />
      <Stat icon="cost" label={hubText(language, "overview.today_cost")} value={formatMoney(overview?.today?.totals)} detail={`${skills.length} skills · ${meetings.length} meetings`} />
    </section>
    <section className={c("dashboardGrid")}>
      <article className={`${c("panel")} ${c("widePanel")}`}><h2><Icon name="chart" />{hubText(language, "overview.cost_trend")}</h2><div className={c("chartBox")}><Bar data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }} /></div></article>
      <article className={c("panel")}><h2><Icon name="sync" />{hubText(language, "overview.recent")}</h2>{runs.length ? <div className={c("compactList")}>{runs.slice(0, 6).map((run) => <div key={run.id} className={c("listRow")}><span className={`${c("statusDot")} ${c(run.status || "pending")}`} /><div><strong>{run.task_name || run.name || "Workflow"}</strong><small>{run.status} · {parseDate(run.started_at || run.created_at)?.toLocaleString() || "—"}</small></div></div>)}</div> : <Empty text={hubText(language, "overview.no_runs")} />}</article>
      <article className={c("panel")}><h2><Icon name="meeting" />{hubText(language, "overview.conversations")}</h2>{rooms.length ? <div className={c("compactList")}>{rooms.slice(0, 6).map((room, index) => <div key={`${room.meeting_name}-${index}`} className={c("listRow")}><Icon name="chat" /><div><strong>{room.meeting_name || "Meeting"}</strong><small>{room.last_sender || "System"}: {(room.last_content || "").replace(/\s+/g, " ").slice(0, 70)}</small></div><span>{room.message_count || 0}</span></div>)}</div> : <Empty text={hubText(language, "common.empty")} />}</article>
      <article className={`${c("panel")} ${alerts.length ? c("alertPanel") : ""}`}><h2><Icon name="warning" />{hubText(language, "overview.alerts")}</h2>{alerts.length ? <div className={c("compactList")}>{alerts.map((alert, index) => <div key={alert.id || index} className={c("listRow")}><Icon name="warning" /><div><strong>{alert.title || "Task"}</strong><small>{alert.reason || "Needs attention"}</small></div></div>)}</div> : <Empty text={hubText(language, "overview.no_alerts")} />}</article>
    </section>
  </div>;
}

function Stat({ icon, label, value, detail }: { icon: "people" | "sync" | "check" | "cost"; label: string; value: string; detail: string }) {
  return <article className={c("statCard")}><span className={c("statIcon")}><Icon name={icon} /></span><div><small>{label}</small><strong>{value}</strong><span>{detail}</span></div></article>;
}
function Empty({ text }: { text: string }) { return <div className={c("empty")}><Icon name="info" /><span>{text}</span></div>; }
