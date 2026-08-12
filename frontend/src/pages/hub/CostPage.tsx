import { useCallback, useEffect, useMemo, useState } from "react";
import { ArcElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from "chart.js";
import { Doughnut, Line } from "react-chartjs-2";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { useLanguage } from "../../store/language";
import { useTheme } from "../../store/theme";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import type { CostReport, CostRow } from "./types";
import styles from "./HubPage.module.css";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Tooltip, Legend);
const c = (name: string) => styles[name] ?? name;
type Period = "day" | "week" | "month";
interface CostOverview { today: { totals: Record<string, number>; date: string }; this_week: { totals: Record<string, number> }; this_month: { totals: Record<string, number> }; all_time: Record<string, number>; }
interface CostCall { called_at: string; name: string; currency: string; tokens_input: number; tokens_cache: number; tokens_output: number; estimated_cost: number; }

function formatNumber(value: number): string { return Number(value || 0).toLocaleString("vi-VN"); }
function formatDate(value: string): string { const [year, month, day] = value.split("-"); return day && month && year ? `${day}-${month}-${year}` : value; }
function money(totals: Record<string, number> = {}): string { const entries = Object.entries(totals); return entries.length ? entries.map(([currency, value]) => `${Number(value).toFixed(4)} ${currency}`).join(" · ") : "0"; }

export function CostPage() {
  const { language } = useLanguage(); const { theme } = useTheme(); const { toast } = useHub();
  const [period, setPeriod] = useState<Period>("day"); const [report, setReport] = useState<CostReport | null>(null);
  const [overview, setOverview] = useState<CostOverview | null>(null); const [loading, setLoading] = useState(true);
  const [showTokens, setShowTokens] = useState(false); const [expanded, setExpanded] = useState<string | null>(null);
  const [calls, setCalls] = useState<Record<string, CostCall[]>>({});
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextReport, nextOverview] = await Promise.all([
        apiClient.get<CostReport>(`/model-pool/cost/report?period=${period}`),
        apiClient.get<CostOverview>("/model-pool/cost/overview"),
      ]);
      setReport(nextReport);
      setOverview(nextOverview);
    } catch (error) {
      const fallback = language === "vi" ? "Không tải được báo cáo" : "Could not load report";
      toast(error instanceof Error ? error.message : fallback, "error");
    } finally {
      setLoading(false);
    }
  }, [language, period, toast]);
  useEffect(() => { void load(); }, [load]);

  const buckets = useMemo(() => {
    const result = new Map<string, { from: string; to: string; rows: CostRow[]; requestCount: number; cost: number; currency: string }>();
    for (const row of report?.rows || []) { const item = result.get(row.bucket) || { from: row.bucket_from, to: row.bucket_to, rows: [], requestCount: 0, cost: 0, currency: row.currency }; item.rows.push(row); item.requestCount += row.request_count; item.cost += Number(row.estimated_cost || 0); result.set(row.bucket, item); }
    return Array.from(result.entries());
  }, [report]);
  const byModel = useMemo(() => { const result: Record<string, number> = {}; for (const row of report?.rows || []) result[row.name] = (result[row.name] || 0) + Number(row.estimated_cost || 0); return result; }, [report]);
  // Chart.js vẽ lên canvas nên không đọc được CSS var(); đổi token màu trong theme.css thì phải đổi các bản sao này cùng lúc.
  const chartColors = theme === "dark"
    ? ["#52d6a0", "#a78bfa", "#d7a95e", "#5b9df0", "#e27b6f", "#6fe6b5"]
    : ["#2c8462", "#7c5cd6", "#ad7628", "#2f6fb8", "#bd5048", "#237454"];
  const trendData = { labels: buckets.map(([, item]) => item.from === item.to ? formatDate(item.from) : `${formatDate(item.from)} → ${formatDate(item.to)}`), datasets: [{ label: hubText(language, "cost.trend"), data: buckets.map(([, item]) => Number(item.cost.toFixed(4))), borderColor: chartColors[0], backgroundColor: theme === "dark" ? "rgba(82,214,160,.18)" : "rgba(44,132,98,.18)", tension: .35, fill: true }] };
  const modelData = { labels: Object.keys(byModel), datasets: [{ data: Object.values(byModel), backgroundColor: chartColors, borderColor: theme === "dark" ? "#111d1a" : "#fffefa", borderWidth: 2 }] };
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
  const toggleBucket = async (key: string, date: string) => {
    if (expanded === key) { setExpanded(null); return; }
    setExpanded(key); if (period !== "day" || calls[date]) return;
    try {
      const data = await apiClient.get<{ calls: CostCall[] }>(`/model-pool/cost/report-calls?date=${date}`);
      setCalls((current) => ({ ...current, [date]: data.calls || [] }));
    } catch (error) {
      const fallback = language === "vi" ? "Không tải được chi tiết" : "Could not load details";
      toast(error instanceof Error ? error.message : fallback, "error");
    }
  };
  const periods: Array<[Period, string]> = [["day", hubText(language, "cost.day")], ["week", hubText(language, "cost.week")], ["month", hubText(language, "cost.month")]];
  return <div className={c("page")}>
    <header className={c("pageHeader")}><div><h1>{hubText(language, "cost.title")}</h1><p>{hubText(language, "cost.subtitle")}</p></div><a className={c("primaryButton")} href={`/api/model-pool/cost/export.xlsx?period=${period}`} download><Icon name="download" />{hubText(language, "cost.export")}</a></header>
    <div className={c("toolbar")}><div className={c("segmented")}>{periods.map(([key, label]) => <button key={key} className={period === key ? c("selected") : ""} onClick={() => { setPeriod(key); setExpanded(null); }}>{label}</button>)}</div><label className={c("checkLabel")}><input type="checkbox" checked={showTokens} onChange={(event) => setShowTokens(event.target.checked)} />{hubText(language, "cost.show_tokens")}</label><span className={c("range")}>{report ? `${formatDate(report.date_from)} → ${formatDate(report.date_to)}` : ""}</span></div>
    {loading ? <div className={c("loading")}><Icon name="sync" />{hubText(language, "common.loading")}</div> : <>
      <section className={c("costSummary")}><Summary label={language === "vi" ? "Hôm nay" : "Today"} value={money(overview?.today.totals)} /><Summary label={language === "vi" ? "Tuần này" : "This week"} value={money(overview?.this_week.totals)} /><Summary label={language === "vi" ? "Tháng này" : "This month"} value={money(overview?.this_month.totals)} /><Summary label={language === "vi" ? "Từ trước đến giờ" : "All time"} value={money(overview?.all_time)} /></section>
      <section className={c("chartGrid")}><article className={c("panel")}><h2>{hubText(language, "cost.trend")}</h2><div className={c("chartBox")}><Line data={trendData} options={chartOptions} /></div></article><article className={c("panel")}><h2>{hubText(language, "cost.by_model")}</h2><div className={c("chartBox")}><Doughnut data={modelData} options={chartOptions} /></div></article></section>
      <article className={c("panel")}><h2>{hubText(language, "cost.details")}</h2><div className={c("tableScroll")}><table className={c("dataTable")}><thead><tr><th>{language === "vi" ? "Kỳ" : "Period"}</th><th>{language === "vi" ? "Lượt gọi" : "Calls"}</th>{showTokens ? <><th>Input</th><th>Cache</th><th>Output</th></> : null}<th>{language === "vi" ? "Chi phí" : "Cost"}</th></tr></thead><tbody>{buckets.length ? buckets.map(([key, item]) => <CostBucket key={key} bucketKey={key} item={item} open={expanded === key} period={period} calls={calls[item.from]} showTokens={showTokens} onToggle={() => void toggleBucket(key, item.from)} />) : <tr><td colSpan={showTokens ? 6 : 3}>{hubText(language, "common.empty")}</td></tr>}</tbody></table></div></article>
    </>}
  </div>;
}

function Summary({ label, value }: { label: string; value: string }) { return <article className={c("summaryCard")}><strong>{value}</strong><span>{label}</span></article>; }
function CostBucket({ bucketKey, item, open, period, calls, showTokens, onToggle }: { bucketKey: string; item: { from: string; to: string; rows: CostRow[]; requestCount: number; cost: number; currency: string }; open: boolean; period: Period; calls?: CostCall[]; showTokens: boolean; onToggle: () => void }) {
  const input = item.rows.reduce((sum, row) => sum + row.tokens_input, 0), cache = item.rows.reduce((sum, row) => sum + row.tokens_cache, 0), output = item.rows.reduce((sum, row) => sum + row.tokens_output, 0);
  const details = period === "day" ? calls : item.rows;
  return <><tr className={c("clickableRow")} onClick={onToggle} data-bucket={bucketKey}><td>{open ? "▾" : "▸"} {item.from === item.to ? formatDate(item.from) : `${formatDate(item.from)} → ${formatDate(item.to)}`}</td><td>{item.requestCount}</td>{showTokens ? <><td>{formatNumber(input)}</td><td>{formatNumber(cache)}</td><td>{formatNumber(output)}</td></> : null}<td>{item.cost.toFixed(4)} {item.currency}</td></tr>{open ? details ? details.length ? details.map((detail, index) => {
    const row = detail as CostCall & CostRow; const label = period === "day" ? `${(row.called_at || "").split(" ")[1] || "—"} · ${row.name}` : row.name;
    return <tr className={c("detailRow")} key={`${label}-${index}`}><td>{label}</td><td>{period === "day" ? "" : row.request_count}</td>{showTokens ? <><td>{formatNumber(row.tokens_input)}</td><td>{formatNumber(row.tokens_cache)}</td><td>{formatNumber(row.tokens_output)}</td></> : null}<td>{Number(row.estimated_cost || 0).toFixed(4)} {row.currency}</td></tr>;
  }) : <tr className={c("detailRow")}><td colSpan={showTokens ? 6 : 3}>—</td></tr> : <tr className={c("detailRow")}><td colSpan={showTokens ? 6 : 3}>…</td></tr> : null}</>;
}
