import { memo, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar } from "react-chartjs-2";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";

import { apiClient } from "../../api/client";
import { Icon, type IconName } from "../../components/Icon";
import { Tooltip as UiTooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { useTheme } from "../../store/theme";
import { avatarColor } from "./avatarColors";
import { shapePath } from "./avatarShapes";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import { notificationBody } from "./notifications";
import type { AgentRecord, CostReport, HubRecord } from "./types";
import styles from "./HubPage.module.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);
const c = (name: string) => styles[name] ?? name;

interface WorkflowRun extends HubRecord {
  task_name?: string;
  started_at?: string;
}

interface RecentRoom {
  meeting_name?: string;
  last_sender?: string;
  last_content?: string;
  last_created_at?: string;
  message_count?: number;
}

interface CostOverview {
  today?: { totals?: Record<string, number> };
}

function isoLocal(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function parseDate(value?: string): Date | null {
  if (!value) return null;
  const parsed = new Date(
    /[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value.replace(" ", "T")}Z`,
  );
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatMoney(totals: Record<string, number> = {}): string {
  const values = Object.entries(totals);
  return values.length
    ? values
        .map(
          ([currency, value]) =>
            `${Number(value).toLocaleString("vi-VN", { maximumFractionDigits: 4 })} ${currency}`,
        )
        .join(" · ")
    : "0";
}

function formatRelative(value: string | undefined, vi: boolean): string {
  const date = parseDate(value);
  if (!date) return "—";
  const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60_000));
  if (minutes < 1) return vi ? "Vừa xong" : "Just now";
  if (minutes < 60) return vi ? `${minutes} phút trước` : `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return vi ? `${hours} giờ trước` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return vi ? `${days} ngày trước` : `${days}d ago`;
}

export function OverviewPage() {
  const { language } = useLanguage();
  const { theme } = useTheme();
  const { agents, skills, meetings, notifications, openNotification } = useHub();
  const vi = language === "vi";
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [rooms, setRooms] = useState<RecentRoom[]>([]);
  const [overview, setOverview] = useState<CostOverview | null>(null);
  const [costReport, setCostReport] = useState<CostReport | null>(null);

  useEffect(() => {
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 6);
    void Promise.all([
      apiClient
        .get<{ runs: WorkflowRun[] }>("/workflow/runs?limit=20")
        .catch(() => ({ runs: [] })),
      apiClient
        .get<{ rooms: RecentRoom[] }>("/meetings/messages/recent?limit=8")
        .catch(() => ({ rooms: [] })),
      apiClient.get<CostOverview>("/model-pool/cost/overview").catch(() => null),
      apiClient
        .get<CostReport>(
          `/model-pool/cost/report?period=day&date_from=${isoLocal(start)}&date_to=${isoLocal(end)}`,
        )
        .catch(() => null),
    ]).then(([runData, roomData, costOverview, report]) => {
      setRuns(runData.runs || []);
      setRooms(roomData.rooms || []);
      setOverview(costOverview);
      setCostReport(report);
    });
  }, []);

  const today = isoLocal(new Date());
  const todayRuns = runs.filter((run) => {
    const date = parseDate(run.started_at || run.created_at);
    return date && isoLocal(date) === today;
  });
  const finished = todayRuns.filter(
    (run) => run.status === "completed" || run.status === "failed",
  );
  const completed = finished.filter((run) => run.status === "completed").length;
  const running = runs.filter((run) => run.status === "running");
  const alerts = notifications.filter((notification) => notification.status !== "resolved");

  const chartData = useMemo(() => {
    const byDate: Record<string, number> = {};
    for (const row of costReport?.rows || []) {
      byDate[row.bucket_from] =
        (byDate[row.bucket_from] || 0) + Number(row.estimated_cost || 0);
    }
    const labels: string[] = [];
    const values: number[] = [];
    const cursor = new Date();
    cursor.setDate(cursor.getDate() - 6);
    for (let index = 0; index < 7; index += 1) {
      const iso = isoLocal(cursor);
      labels.push(
        cursor.toLocaleDateString(vi ? "vi-VN" : "en-US", {
          weekday: "short",
          day: "2-digit",
        }),
      );
      values.push(Number((byDate[iso] || 0).toFixed(4)));
      cursor.setDate(cursor.getDate() + 1);
    }
    return {
      labels,
      datasets: [
        {
          label: hubText(language, "overview.cost_trend"),
          data: values,
          backgroundColor: theme === "dark" ? "#52d6a0" : "#3f9a73",
          hoverBackgroundColor: theme === "dark" ? "#6be1b0" : "#327f5e",
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 34,
        },
      ],
    };
  }, [costReport, language, theme, vi]);

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 280 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: theme === "dark" ? "#172723" : "#173b30",
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: theme === "dark" ? "#9daea8" : "#5f6d67", font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: theme === "dark" ? "rgba(157,174,168,.12)" : "rgba(62,84,75,.1)" },
          ticks: { color: theme === "dark" ? "#9daea8" : "#5f6d67", font: { size: 10 } },
        },
      },
    }),
    [theme],
  );

  return (
    <div className={`${c("page")} ${c("overviewPage")}`}>
      <header className={c("overviewHeader")}>
        <LiveClock language={language} />
      </header>

      <section className={c("overviewStats")} aria-label={vi ? "Chỉ số tổng quan" : "Overview metrics"}>
        <Stat
          icon="people"
          label={hubText(language, "overview.agents")}
          value={String(agents.length)}
          detail={`${agents.filter((agent) => agent.enabled !== 0 && agent.enabled !== false).length} ${vi ? "đang hoạt động" : "active"}`}
          tone="mint"
        />
        <Stat
          icon="sync"
          label={hubText(language, "overview.running")}
          value={String(running.length)}
          detail={`${todayRuns.length} ${vi ? "lượt hôm nay" : "runs today"}`}
          tone="blue"
        />
        <Stat
          icon="check"
          label={vi ? "Hoàn thành" : "Completed"}
          value={finished.length ? `${Math.round((completed / finished.length) * 100)}%` : "—"}
          detail={`${completed}/${finished.length} ${vi ? "lượt kết thúc" : "finished"}`}
          tone="violet"
        />
        <Stat
          icon="cost"
          label={hubText(language, "overview.today_cost")}
          value={formatMoney(overview?.today?.totals)}
          detail={`${skills.length} ${vi ? "kỹ năng" : "skills"} · ${meetings.length} ${vi ? "cuộc họp" : "meetings"}`}
          tone="amber"
        />
      </section>

      <section className={c("overviewMiddle")}>
        <article className={`${c("overviewPanel")} ${c("performancePanel")}`}>
          <PanelHeader
            icon="chart"
            title={vi ? "Hiệu suất 7 ngày" : "Seven-day performance"}
            subtitle={hubText(language, "overview.cost_trend")}
          />
          <div className={c("overviewChart")}>
            <Bar data={chartData} options={chartOptions} />
          </div>
        </article>

        <article className={`${c("overviewPanel")} ${c("agentPanel")}`}>
          <PanelHeader
            icon="people"
            title={hubText(language, "overview.agents")}
            action={{ label: vi ? "Xem tất cả" : "View all", to: "/hub/agents" }}
          />
          {agents.length ? (
            <div className={c("agentOverviewList")}>
              {agents.slice(0, 5).map((agent) => (
                <AgentRow key={agent.id} agent={agent} vi={vi} />
              ))}
            </div>
          ) : (
            <Empty title={vi ? "Chưa có nhân viên AI" : "No AI employees yet"} />
          )}
        </article>
      </section>

      <section className={c("overviewBottom")}>
        <article className={c("overviewPanel")}>
          <PanelHeader
            icon="sync"
            title={hubText(language, "overview.recent")}
            action={{ label: vi ? "Xem tất cả" : "View all", to: "/hub/company-runner" }}
          />
          {runs.length ? (
            <div className={c("overviewList")}>
              {runs.slice(0, 3).map((run) => (
                <div key={run.id} className={c("overviewListRow")}>
                  <span className={`${c("activityMarker")} ${c(run.status || "pending")}`}>
                    <Icon name={run.status === "completed" ? "check" : "sync"} />
                  </span>
                  <div>
                    <strong>{run.task_name || run.name || (vi ? "Quy trình" : "Workflow")}</strong>
                    <small>{run.status || "pending"}</small>
                  </div>
                  <time>{formatRelative(run.started_at || run.created_at, vi)}</time>
                </div>
              ))}
            </div>
          ) : (
            <Empty title={hubText(language, "overview.no_runs")} />
          )}
        </article>

        <article className={c("overviewPanel")}>
          <PanelHeader
            icon="chat"
            title={hubText(language, "overview.conversations")}
            action={{ label: vi ? "Xem tất cả" : "View all", to: "/hub/meeting" }}
          />
          {rooms.length ? (
            <div className={c("overviewList")}>
              {rooms.slice(0, 3).map((room, index) => (
                <div key={`${room.meeting_name}-${index}`} className={c("overviewListRow")}>
                  <span className={`${c("activityMarker")} ${c("conversationMarker")}`}>
                    <Icon name="chat" />
                  </span>
                  <div>
                    <strong>{room.meeting_name || (vi ? "Phòng họp" : "Meeting")}</strong>
                    <small>
                      {room.last_sender || "System"}: {(room.last_content || "").replace(/\s+/g, " ").slice(0, 52)}
                    </small>
                  </div>
                  <time>{formatRelative(room.last_created_at, vi)}</time>
                </div>
              ))}
            </div>
          ) : (
            <Empty title={vi ? "Chưa có hội thoại" : "No conversations yet"} />
          )}
        </article>

        <article className={`${c("overviewPanel")} ${alerts.length ? c("attentionPanel") : ""}`}>
          <PanelHeader
            icon="warning"
            title={hubText(language, "overview.alerts")}
          />
          {alerts.length ? (
            <div className={c("overviewList")}>
              {alerts.slice(0, 3).map((alert) => (
                <button
                  key={alert.id}
                  type="button"
                  className={`${c("overviewListRow")} ${c("overviewNotificationRow")}`}
                  onClick={() => openNotification(alert)}
                >
                  <span className={`${c("activityMarker")} ${c(alert.severity === "error" ? "warningMarker" : "conversationMarker")}`}>
                    <Icon name={alert.severity === "error" ? "warning" : "bell"} />
                  </span>
                  <div>
                    <strong>{alert.title || (vi ? "Công việc" : "Task")}</strong>
                    <small>{notificationBody(alert, language) || (vi ? "Cần chú ý" : "Needs attention")}</small>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <Empty
              icon="check"
              title={vi ? "Mọi thứ đang ổn" : "Everything looks good"}
              detail={vi ? "Chưa có cảnh báo nào." : "There are no open alerts."}
              positive
            />
          )}
        </article>
      </section>
    </div>
  );
}

const LiveClock = memo(function LiveClock({ language }: { language: "vi" | "en" }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className={c("liveClock")} aria-label={language === "vi" ? "Giờ hiện tại GMT cộng 7" : "Current time GMT plus 7"}>
      <time dateTime={now.toISOString()}>
        {now.toLocaleTimeString("en-GB", {
          timeZone: "Asia/Ho_Chi_Minh",
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </time>
      <span><i />GMT+7</span>
    </div>
  );
});

function Stat({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: "people" | "sync" | "check" | "cost";
  label: string;
  value: string;
  detail: string;
  tone: "mint" | "blue" | "violet" | "amber";
}) {
  return (
    <article className={`${c("overviewStat")} ${c(`statTone-${tone}`)}`}>
      <span className={c("overviewStatIcon")}><Icon name={icon} /></span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        <span>{detail}</span>
      </div>
    </article>
  );
}

function PanelHeader({
  icon,
  title,
  subtitle,
  action,
}: {
  icon: IconName;
  title: string;
  subtitle?: string;
  action?: { label: string; to: string };
}) {
  const navigate = useNavigate();
  const tooltip = useTooltipText();

  return (
    <header className={c("overviewPanelHeader")}>
      <span className={c("panelTitleIcon")}><Icon name={icon} /></span>
      <div>
        <h2>{title}</h2>
        {subtitle ? <small>{subtitle}</small> : null}
      </div>
      {action ? (
        <UiTooltip label={tooltip("tooltip.overview.open_section", title)}>
          <button className={c("overviewPanelAction")} type="button" onClick={() => navigate(action.to)}>
            {action.label}<Icon name="arrowRight" />
          </button>
        </UiTooltip>
      ) : null}
    </header>
  );
}

function AgentRow({ agent, vi }: { agent: AgentRecord; vi: boolean }) {
  const enabled = agent.enabled !== 0 && agent.enabled !== false;
  return (
    <div className={c("agentOverviewRow")}>
      {/* Cùng bảng màu và cùng bộ hình với thẻ ở tab Nhân sự — trước đây chỗ này
          chỉ hiện chữ cái đầu và chỉ hiểu 4 màu, nên một nhân viên trông khác
          nhau ở hai trang. */}
      <span
        className={c("overviewAvatar")}
        style={{
          background: avatarColor(agent.avatar_color).bg,
          color: avatarColor(agent.avatar_color).ink,
        }}
        title={agent.name}
      >
        <svg
          viewBox="0 0 24 24"
          width={18}
          height={18}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          dangerouslySetInnerHTML={{ __html: shapePath(agent.avatar_icon) }}
        />
      </span>
      <div className={c("agentIdentity")}>
        <strong>{agent.name || "AI Agent"}</strong>
        <small>{agent.role || (vi ? "Trợ lý AI" : "AI assistant")}</small>
      </div>
      <div className={c("readiness")}>
        <span><i className={enabled ? c("ready") : c("paused")} />{enabled ? (vi ? "Sẵn sàng" : "Ready") : (vi ? "Tạm dừng" : "Paused")}</span>
        <div><i style={{ width: enabled ? "100%" : "0%" }} /></div>
      </div>
    </div>
  );
}

function Empty({
  icon = "info",
  title,
  detail,
  positive = false,
}: {
  icon?: IconName;
  title: string;
  detail?: string;
  positive?: boolean;
}) {
  return (
    <div className={`${c("overviewEmpty")} ${positive ? c("positiveEmpty") : ""}`}>
      <span><Icon name={icon} /></span>
      <div><strong>{title}</strong>{detail ? <small>{detail}</small> : null}</div>
    </div>
  );
}
