import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { Dialog } from "./Dialog";
import { useHub } from "./HubContext";
import type { SkillRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
const SECRET_MASK = "••••••••";
type SkillType = "builtin" | "api" | "mcp" | "custom";
interface ToolInfo {
  name: string;
  description?: string;
}
interface McpServer {
  skill_id: number;
  connected: boolean;
  error?: string;
  available: string[];
  tools: string[];
}
interface SkillDraft {
  id?: number;
  name: string;
  description: string;
  type: SkillType;
  config: Record<string, unknown>;
  enabled: boolean;
}
interface ConnectionResult {
  ok: boolean;
  error?: string;
  note?: string;
  status_code?: number;
  elapsed_ms?: number;
  tools?: ToolInfo[];
}

export function SkillsPage() {
  const { language } = useLanguage();
  const vi = language === "vi";
  const tooltip = useTooltipText();
  const { skills, refreshSkills, toast, confirm } = useHub();
  const [servers, setServers] = useState<McpServer[]>([]);
  const [registry, setRegistry] = useState<ToolInfo[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | SkillType>("all");
  const [draft, setDraft] = useState<SkillDraft | null>(null);
  const [step, setStep] = useState(1);
  const refreshToolSources = async () => {
    const [status, tools] = await Promise.all([
      apiClient.get<{ servers: McpServer[] }>("/tools/mcp/status").catch(() => ({ servers: [] })),
      apiClient.get<{ tools: ToolInfo[] }>("/tools/").catch(() => ({ tools: [] })),
    ]);
    setServers(status.servers || []);
    setRegistry(tools.tools || []);
  };
  useEffect(() => {
    void refreshToolSources();
  }, []);
  const visible = useMemo(
    () =>
      skills.filter(
        (skill) =>
          (filter === "all" || skill.type === filter) &&
          (!query ||
            `${skill.name || ""} ${skill.description || ""}`.toLowerCase().includes(query.toLowerCase())),
      ),
    [filter, query, skills],
  );
  const open = (skill?: SkillRecord) => {
    setStep(1);
    setDraft(
      skill
        ? {
            id: skill.id,
            name: skill.name || "",
            description: skill.description || "",
            type: normalizeType(skill.type),
            config: structuredClone(skill.config || {}),
            enabled: skill.enabled !== 0 && skill.enabled !== false,
          }
        : { name: "", description: "", type: "builtin", config: {}, enabled: true },
    );
  };
  const save = async () => {
    if (!draft?.name.trim()) return toast(vi ? "Tên kỹ năng là bắt buộc" : "Skill name is required", "error");
    const body = {
      name: draft.name.trim(),
      description: draft.description.trim(),
      type: draft.type,
      config: draft.config,
      enabled: draft.enabled ? 1 : 0,
    };
    try {
      if (draft.id) await apiClient.patch(`/skills/${draft.id}`, body);
      else await apiClient.post("/skills/", body);
      await refreshSkills();
      await refreshToolSources();
      setDraft(null);
      toast(vi ? "Đã lưu kỹ năng" : "Skill saved", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    }
  };
  const remove = async () => {
    if (!draft?.id || !(await confirm(vi ? "Xoá kỹ năng này?" : "Delete this skill?"))) return;
    await apiClient.delete(`/skills/${draft.id}`);
    await refreshSkills();
    setDraft(null);
  };
  const types: Array<["all" | SkillType, string]> = [
    ["all", vi ? "Tất cả" : "All"],
    ["builtin", vi ? "Có sẵn" : "Built-in"],
    ["api", "API"],
    ["mcp", "MCP"],
    ["custom", "Custom"],
  ];
  return (
    <div className={c("page")}>
      <header className={c("pageHeader")}>
        <div>
          <h1>{vi ? "Kỹ năng" : "Skills"}</h1>
          <p>{vi ? "Công cụ nhân viên AI có thể sử dụng" : "Tools available to AI employees"}</p>
        </div>
        <Tooltip label={tooltip("tooltip.skills.create_open")}>
          <button data-testid="new-skill" className={c("primaryButton")} onClick={() => open()}>
            <Icon name="puzzle" />
            {vi ? "Thêm kỹ năng" : "Add skill"}
          </button>
        </Tooltip>
      </header>
      <div className={c("toolbar")}>
        <input
          className={c("input")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={vi ? "Tìm kỹ năng…" : "Search skills…"}
        />
        <div className={c("filterBar")}>
          {types.map(([key, label]) => (
            <Tooltip key={key} label={tooltip("tooltip.skills.filter", label)}>
              <button
                className={filter === key ? c("activePill") : c("pill")}
                onClick={() => setFilter(key)}
              >
                {label} ({key === "all" ? skills.length : skills.filter((skill) => skill.type === key).length})
              </button>
            </Tooltip>
          ))}
        </div>
      </div>
      <section className={c("cardGrid")}>
        {visible.map((skill) => {
          const server = servers.find((item) => item.skill_id === skill.id);
          return (
            <Tooltip key={skill.id} label={tooltip("tooltip.skills.open", skill.name || "")}>
              <button className={c("entityCard")} onClick={() => open(skill)}>
                <span className={c("entityIcon")}>
                  <Icon name={skill.type === "mcp" ? "plug" : skill.type === "api" ? "api" : "bolt"} />
                </span>
                <div>
                  <h2>{skill.name}</h2>
                  <p>{skill.description || (vi ? "Chưa có mô tả" : "No description")}</p>
                  {skill.type === "mcp" ? (
                    <small>
                      {server?.connected
                        ? `${server.available.length} tool`
                        : server?.error || (vi ? "Đang kết nối…" : "Connecting…")}
                    </small>
                  ) : (
                    <small>{skill.type}</small>
                  )}
                </div>
                <span className={skill.enabled === 0 || skill.enabled === false ? c("offBadge") : c("onBadge")}>
                  {skill.enabled === 0 || skill.enabled === false ? "OFF" : "ON"}
                </span>
              </button>
            </Tooltip>
          );
        })}
      </section>
      {draft ? (
        <Dialog
          title={draft.id ? (vi ? "Chỉnh sửa kỹ năng" : "Edit skill") : vi ? "Thêm kỹ năng" : "Add skill"}
          onClose={() => setDraft(null)}
          wide
        >
          <SkillWizard
            draft={draft}
            setDraft={setDraft}
            step={step}
            setStep={setStep}
            registry={registry}
            servers={servers}
            vi={vi}
            refreshStatus={refreshToolSources}
            toast={toast}
            onSave={save}
            onDelete={remove}
          />
        </Dialog>
      ) : null}
    </div>
  );
}

function SkillWizard({
  draft,
  setDraft,
  step,
  setStep,
  registry,
  servers,
  vi,
  refreshStatus,
  toast,
  onSave,
  onDelete,
}: {
  draft: SkillDraft;
  setDraft: (draft: SkillDraft) => void;
  step: number;
  setStep: (step: number) => void;
  registry: ToolInfo[];
  servers: McpServer[];
  vi: boolean;
  refreshStatus: () => Promise<void>;
  toast: (message: string, kind?: "success" | "error" | "info") => void;
  onSave: () => void;
  onDelete: () => void;
}) {
  const tooltip = useTooltipText();
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionResult | null>(null);
  const [discovered, setDiscovered] = useState<string[]>(
    () => servers.find((server) => server.skill_id === draft.id)?.available || [],
  );
  const set = <K extends keyof SkillDraft>(key: K, value: SkillDraft[K]) =>
    setDraft({ ...draft, [key]: value });
  const setConfig = (key: string, value: unknown) => set("config", { ...draft.config, [key]: value });
  const setType = (type: SkillType) => {
    setDraft({ ...draft, type, config: {} });
    setResult(null);
    setDiscovered([]);
  };
  const testConnection = async () => {
    if (draft.type !== "api" && draft.type !== "mcp") return;
    setTesting(true);
    try {
      const tested = await apiClient.post<ConnectionResult>("/skills/test-connection", {
        type: draft.type,
        config: draft.config,
        skill_id: draft.id || null,
      });
      setResult(tested);
      if (draft.type === "mcp") {
        await refreshStatus();
        const status = await apiClient.get<{ servers: McpServer[] }>("/tools/mcp/status");
        const namesFromStatus =
          status.servers.find((server) => server.skill_id === draft.id)?.available || [];
        // Persisted skills always use exact names from /tools/mcp/status. A new,
        // unsaved connection has no status row yet, so its test result is shown
        // read-only until the first save.
        setDiscovered(namesFromStatus);
      }
    } catch (error) {
      setResult({ ok: false, error: error instanceof Error ? error.message : "Connection failed" });
    } finally {
      setTesting(false);
    }
  };
  const selectedTools = Array.isArray(draft.config.tools) ? (draft.config.tools as string[]) : discovered;
  const extraConfig = Object.fromEntries(
    Object.entries(draft.config).filter(
      ([key]) =>
        !["tool_name", "endpoint", "method", "api_key", "target", "transport", "token", "tools"].includes(
          key,
        ),
    ),
  );
  const updateExtra = (raw: string) => {
    try {
      const extra = JSON.parse(raw) as Record<string, unknown>;
      set("config", {
        ...extra,
        ...Object.fromEntries(
          Object.entries(draft.config).filter(([key]) =>
            ["tool_name", "endpoint", "method", "api_key", "target", "transport", "token", "tools"].includes(
              key,
            ),
          ),
        ),
      });
    } catch {
      toast(vi ? "JSON không hợp lệ" : "Invalid JSON", "error");
    }
  };
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (step < 3) {
          if (step === 1 && !draft.name.trim()) return;
          setStep(step + 1);
        } else onSave();
      }}
    >
      <div className={c("wizardTabs")}>
        {[vi ? "Thông tin" : "Details", vi ? "Kết nối" : "Connection", vi ? "Xem lại" : "Review"].map(
          (label, index) => (
            <Tooltip
              key={label}
              label={tooltip(draft.id ? "tooltip.skills.wizard_step" : "tooltip.skills.wizard_step_locked", label)}
            >
              <button
                data-testid={`skill-step-${index + 1}`}
                type="button"
                className={step === index + 1 ? c("wizardActive") : step > index + 1 ? c("wizardDone") : ""}
                onClick={() => draft.id && setStep(index + 1)}
              >
                <span>{step > index + 1 ? "✓" : index + 1}</span>
                {label}
              </button>
            </Tooltip>
          ),
        )}
      </div>
      {step === 1 ? (
        <div className={c("formStack")}>
          <Field label={vi ? "Tên kỹ năng" : "Skill name"}>
            <input
              data-testid="skill-name"
              className={c("input")}
              value={draft.name}
              onChange={(event) => set("name", event.target.value)}
            />
          </Field>
          <Field label={vi ? "Mô tả" : "Description"}>
            <textarea
              data-testid="skill-description"
              className={c("textarea")}
              rows={4}
              value={draft.description}
              onChange={(event) => set("description", event.target.value)}
            />
          </Field>
          <label className={c("checkLabel")}>
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => set("enabled", event.target.checked)}
            />
            {vi ? "Đang bật" : "Enabled"}
          </label>
        </div>
      ) : null}
      {step === 2 ? (
        <div className={c("formStack")}>
          <div className={c("typeChoices")}>
            {(["builtin", "api", "mcp", "custom"] as SkillType[]).map((type) => (
              <Tooltip key={type} label={tooltip("tooltip.skills.type", type)}>
                <button
                  type="button"
                  className={draft.type === type ? c("typeSelected") : ""}
                  onClick={() => setType(type)}
                >
                  <Icon
                    name={
                      type === "mcp" ? "plug" : type === "api" ? "api" : type === "custom" ? "code" : "bolt"
                    }
                  />
                  <strong>{type}</strong>
                </button>
              </Tooltip>
            ))}
          </div>
          <SkillConfig
            draft={draft}
            setConfig={setConfig}
            setWholeConfig={(config) => set("config", config)}
            registry={registry}
            discovered={discovered}
            selectedTools={selectedTools}
            setSelectedTools={(tools) => setConfig("tools", tools)}
            extraConfig={extraConfig}
            updateExtra={updateExtra}
            vi={vi}
          />
          {draft.type === "api" || draft.type === "mcp" ? (
            <>
              <Tooltip label={tooltip(testing ? "tooltip.skills.test_running" : "tooltip.skills.test")}>
                <button
                  data-testid="test-skill-connection"
                  type="button"
                  className={c("buttonGhost")}
                  disabled={testing}
                  onClick={() => void testConnection()}
                >
                  <Icon name="plug" />
                  {testing ? (vi ? "Đang thử…" : "Testing…") : vi ? "Kiểm tra kết nối" : "Test connection"}
                </button>
              </Tooltip>
              {result ? (
                <div className={result.ok ? c("connectionOk") : c("connectionFail")}>
                  <strong>
                    {result.ok
                      ? vi
                        ? "Kết nối được"
                        : "Connected"
                      : vi
                        ? "Không kết nối được"
                        : "Connection failed"}
                  </strong>
                  <span>{result.note || result.error || ""}</span>
                  {draft.type === "mcp" && draft.id && result.ok && !discovered.length ? (
                    <small>
                      {vi
                        ? "Status chưa trả tool nào; tên tool không được tự sinh ở trình duyệt."
                        : "Status returned no tools; browser-generated names are not allowed."}
                    </small>
                  ) : null}
                  {draft.type === "mcp" && !draft.id && result.tools?.length ? (
                    <small>
                      {vi
                        ? `Server báo ${result.tools.length} tool. Lưu rồi mở lại để chọn theo /api/tools/mcp/status.`
                        : `Server reported ${result.tools.length} tools. Save and reopen to select from /api/tools/mcp/status.`}
                    </small>
                  ) : null}
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}
      {step === 3 ? (
        <div className={c("reviewGrid")}>
          <Review label={vi ? "Tên" : "Name"} value={draft.name} />
          <Review label={vi ? "Mô tả" : "Description"} value={draft.description || "—"} />
          <Review label={vi ? "Loại" : "Type"} value={draft.type} />
          <Review label={vi ? "Cấu hình" : "Configuration"} value={safeReviewConfig(draft.config)} />
        </div>
      ) : null}
      <footer className={c("formActions")}>
        {draft.id ? (
          <Tooltip label={tooltip("tooltip.skills.delete", draft.name || "")}>
            <button data-testid="delete-skill" type="button" className={c("dangerLink")} onClick={onDelete}>
              {vi ? "Xoá kỹ năng" : "Delete skill"}
            </button>
          </Tooltip>
        ) : (
          <span />
        )}
        <div>
          {step > 1 ? (
            <Tooltip label={tooltip("tooltip.skills.back")}>
              <button type="button" className={c("buttonGhost")} onClick={() => setStep(step - 1)}>
                {vi ? "Quay lại" : "Back"}
              </button>
            </Tooltip>
          ) : null}
          <Tooltip
            label={tooltip(
              step === 3
                ? "tooltip.skills.save"
                : step === 1 && !draft.name.trim()
                  ? "tooltip.skills.continue_name_required"
                  : "tooltip.skills.continue",
              draft.name,
            )}
          >
            <button data-testid="skill-next-save" type="submit" className={c("primaryButton")}>
              {step === 3 ? (vi ? "Lưu" : "Save") : vi ? "Tiếp tục" : "Continue"}
            </button>
          </Tooltip>
        </div>
      </footer>
    </form>
  );
}

function SkillConfig({
  draft,
  setConfig,
  setWholeConfig,
  registry,
  discovered,
  selectedTools,
  setSelectedTools,
  extraConfig,
  updateExtra,
  vi,
}: {
  draft: SkillDraft;
  setConfig: (key: string, value: unknown) => void;
  setWholeConfig: (config: Record<string, unknown>) => void;
  registry: ToolInfo[];
  discovered: string[];
  selectedTools: string[];
  setSelectedTools: (tools: string[]) => void;
  extraConfig: Record<string, unknown>;
  updateExtra: (raw: string) => void;
  vi: boolean;
}) {
  if (draft.type === "builtin")
    return (
      <Field label={vi ? "Công cụ hệ thống" : "System tool"}>
        <select
          className={c("select")}
          value={String(draft.config.tool_name || "")}
          onChange={(event) => setConfig("tool_name", event.target.value)}
        >
          <option value="">—</option>
          {registry.map((tool) => (
            <option key={tool.name} value={tool.name}>
              {tool.name} — {tool.description}
            </option>
          ))}
        </select>
      </Field>
    );
  if (draft.type === "api")
    return (
      <>
        <div className={c("formGrid")}>
          <Field label="Endpoint URL">
            <input
              className={c("input")}
              value={String(draft.config.endpoint || "")}
              onChange={(event) => setConfig("endpoint", event.target.value)}
            />
          </Field>
          <Field label="Method">
            <select
              className={c("select")}
              value={String(draft.config.method || "GET")}
              onChange={(event) => setConfig("method", event.target.value)}
            >
              {["GET", "POST", "PUT", "PATCH", "DELETE"].map((method) => (
                <option key={method}>{method}</option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="API key / token">
          <input
            data-testid="skill-secret"
            className={c("input")}
            type="password"
            value={String(draft.config.api_key || "")}
            placeholder={SECRET_MASK}
            onChange={(event) => setConfig("api_key", event.target.value)}
          />
        </Field>
        <JsonExtra value={extraConfig} onCommit={updateExtra} vi={vi} />
      </>
    );
  if (draft.type === "mcp")
    return (
      <>
        <div className={c("formGrid")}>
          <Field label={vi ? "Địa chỉ / lệnh MCP" : "MCP target / command"}>
            <input
              className={c("input")}
              value={String(draft.config.target || "")}
              onChange={(event) => setConfig("target", event.target.value)}
            />
          </Field>
          <Field label="Transport">
            <select
              className={c("select")}
              value={String(draft.config.transport || "stdio")}
              onChange={(event) => setConfig("transport", event.target.value)}
            >
              {["stdio", "http", "sse"].map((transport) => (
                <option key={transport}>{transport}</option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Token">
          <input
            data-testid="skill-secret"
            className={c("input")}
            type="password"
            value={String(draft.config.token || "")}
            placeholder={SECRET_MASK}
            onChange={(event) => setConfig("token", event.target.value)}
          />
        </Field>
        {discovered.length ? (
          <Field
            label={vi ? "Tool do /api/tools/mcp/status trả về" : "Tools returned by /api/tools/mcp/status"}
          >
            <div className={c("toolChecklist")}>
              {discovered.map((toolName) => (
                <label key={toolName}>
                  <input
                    type="checkbox"
                    checked={selectedTools.includes(toolName)}
                    onChange={(event) =>
                      setSelectedTools(
                        event.target.checked
                          ? [...selectedTools, toolName]
                          : selectedTools.filter((name) => name !== toolName),
                      )
                    }
                  />
                  <code>{toolName}</code>
                </label>
              ))}
            </div>
          </Field>
        ) : null}
        <JsonExtra value={extraConfig} onCommit={updateExtra} vi={vi} />
      </>
    );
  return (
    <JsonExtra
      value={draft.config}
      onCommit={(raw) => {
        try {
          setWholeConfig(JSON.parse(raw) as Record<string, unknown>);
        } catch {
          /* keep the last valid object */
        }
      }}
      vi={vi}
    />
  );
}

function JsonExtra({
  value,
  onCommit,
  vi,
}: {
  value: Record<string, unknown>;
  onCommit: (raw: string) => void;
  vi: boolean;
}) {
  const [raw, setRaw] = useState(() => JSON.stringify(value, null, 2));
  useEffect(() => setRaw(JSON.stringify(value, null, 2)), [value]);
  return (
    <Field label={vi ? "Tuỳ chọn nâng cao (JSON)" : "Advanced options (JSON)"}>
      <textarea
        className={c("codeArea")}
        rows={5}
        value={raw}
        onChange={(event) => setRaw(event.target.value)}
        onBlur={() => onCommit(raw)}
      />
    </Field>
  );
}
function normalizeType(value?: string): SkillType {
  return value === "api" || value === "mcp" || value === "custom" ? value : "builtin";
}
function safeReviewConfig(config: Record<string, unknown>): string {
  const copy = { ...config };
  for (const key of ["api_key", "token"]) if (copy[key]) copy[key] = SECRET_MASK;
  return JSON.stringify(copy, null, 2);
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className={c("field")}>
      <span>{label}</span>
      {children}
    </label>
  );
}
function Review({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <small>{label}</small>
      <p>{value}</p>
    </div>
  );
}
