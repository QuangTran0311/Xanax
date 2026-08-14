import { useEffect, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { AVATAR_COLOR_KEYS, avatarColor } from "./avatarColors";
import { AVATAR_SHAPE_KEYS, AVATAR_SHAPE_LABEL, shapePath } from "./avatarShapes";
import { Dialog } from "./Dialog";
import { useHub } from "./HubContext";
import type { AgentRecord, ModelRecord, SkillRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
interface Department {
  id: number;
  name: string;
  description?: string;
  color?: string;
  head_agent_id?: number | null;
}
interface McpServer {
  skill_id: number;
  connected: boolean;
  error?: string;
  available: string[];
  tools: string[];
  prefix?: string;
}
interface AgentDraft {
  id?: number;
  name: string;
  role: string;
  system_prompt: string;
  avatar_color: string;
  avatar_icon: string;
  department_id: string;
  model_pool_ids: number[];
  skills: number[];
  skill_tools: Record<string, string[]>;
}
const blankAgent = (): AgentDraft => ({
  name: "",
  role: "Assistant",
  system_prompt: "",
  avatar_color: "mint",
  avatar_icon: "bot",
  department_id: "",
  model_pool_ids: [],
  skills: [],
  skill_tools: {},
});
// Danh sách hình và màu nay ở avatarShapes.ts / avatarColors.ts — nơi duy nhất,
// và mọi lựa chọn chào ra đều vẽ được thật.

export function AgentsPage() {
  const { language } = useLanguage();
  const vi = language === "vi";
  const tooltip = useTooltipText();
  const { agents, skills, modelPool, refreshAgents, toast, confirm } = useHub();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [servers, setServers] = useState<McpServer[]>([]);
  const [query, setQuery] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState(0);
  const [draft, setDraft] = useState<AgentDraft | null>(null);
  const [step, setStep] = useState(1);
  const [departmentsOpen, setDepartmentsOpen] = useState(false);
  const reloadSupporting = async () => {
    const [departmentData, statusData] = await Promise.all([
      apiClient.get<{ departments: Department[] }>("/departments/"),
      apiClient.get<{ servers: McpServer[] }>("/tools/mcp/status").catch(() => ({ servers: [] })),
    ]);
    setDepartments(departmentData.departments || []);
    setServers(statusData.servers || []);
  };
  useEffect(() => {
    void reloadSupporting();
  }, []);
  const visible = agents.filter(
    (agent) =>
      (!departmentFilter || agent.department_id === departmentFilter) &&
      (!query || `${agent.name || ""} ${agent.role || ""}`.toLowerCase().includes(query.toLowerCase())),
  );
  const openAgent = (agent?: AgentRecord) => {
    setStep(1);
    setDraft(
      agent
        ? {
            id: agent.id,
            name: agent.name || "",
            role: agent.role || "Assistant",
            system_prompt: String(agent.system_prompt || ""),
            avatar_color: agent.avatar_color || "mint",
            avatar_icon: agent.avatar_icon || "bot",
            department_id: agent.department_id ? String(agent.department_id) : "",
            model_pool_ids: agent.model_pool_ids || [],
            skills: agent.skills || [],
            skill_tools: agent.skill_tools || {},
          }
        : blankAgent(),
    );
  };
  const save = async () => {
    if (!draft?.name.trim())
      return toast(vi ? "Tên nhân viên là bắt buộc" : "Employee name is required", "error");
    const body = {
      ...draft,
      name: draft.name.trim(),
      department_id: draft.department_id ? Number(draft.department_id) : null,
    };
    delete (body as { id?: number }).id;
    try {
      if (draft.id) await apiClient.patch(`/agent-configs/${draft.id}`, body);
      else await apiClient.post("/agent-configs/", body);
      await refreshAgents();
      setDraft(null);
      toast(vi ? "Đã lưu nhân viên" : "Employee saved", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    }
  };
  const remove = async () => {
    if (!draft?.id || !(await confirm(vi ? "Xoá nhân viên này?" : "Delete this employee?"))) return;
    await apiClient.delete(`/agent-configs/${draft.id}`);
    await refreshAgents();
    setDraft(null);
  };
  return (
    <div className={c("page")}>
      <header className={c("pageHeader")}>
        <div>
          <h1>{vi ? "Nhân sự" : "People"}</h1>
          <p>
            {vi
              ? `${agents.length} nhân viên AI · tổ chức theo phòng ban`
              : `${agents.length} AI employees · organized by department`}
          </p>
        </div>
        <div className={c("headerActions")}>
          <Tooltip label={tooltip("tooltip.agents.departments_open")}>
            <button className={c("buttonGhost")} onClick={() => setDepartmentsOpen(true)}>
              <Icon name="people" />
              {vi ? "Phòng ban" : "Departments"}
            </button>
          </Tooltip>
          <Tooltip label={tooltip("tooltip.agents.create_open")}>
            <button data-testid="new-agent" className={c("primaryButton")} onClick={() => openAgent()}>
              <Icon name="bot" />
              {vi ? "Thêm nhân viên" : "Add employee"}
            </button>
          </Tooltip>
        </div>
      </header>
      <div className={c("toolbar")}>
        <input
          className={c("input")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={vi ? "Tìm nhân viên…" : "Search employees…"}
        />
        <select
          className={c("select")}
          value={departmentFilter}
          onChange={(event) => setDepartmentFilter(Number(event.target.value))}
        >
          <option value={0}>{vi ? "Tất cả phòng ban" : "All departments"}</option>
          {departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
      </div>
      <section className={c("cardGrid")}>
        {visible.map((agent) => (
          <Tooltip key={agent.id} label={tooltip("tooltip.agents.open", agent.name || "")}>
          <button className={c("entityCard")} onClick={() => openAgent(agent)}>
            <Avatar agent={agent} />
            <div>
              <h2>{agent.name}</h2>
              <p>{agent.role || "Assistant"}</p>
              <small>
                {departments.find((item) => item.id === agent.department_id)?.name ||
                  (vi ? "Chưa có phòng ban" : "No department")}{" "}
                · {(agent.skills || []).length} {vi ? "kỹ năng" : "skills"}
              </small>
            </div>
            <span className={agent.enabled === 0 || agent.enabled === false ? c("offBadge") : c("onBadge")}>
              {agent.enabled === 0 || agent.enabled === false ? "OFF" : "ON"}
            </span>
          </button>
          </Tooltip>
        ))}
      </section>
      {!visible.length ? (
        <div className={c("empty")}>
          <Icon name="bot" />
          {vi ? "Không tìm thấy nhân viên" : "No employees found"}
        </div>
      ) : null}
      {draft ? (
        <Dialog
          title={
            draft.id
              ? vi
                ? "Chỉnh sửa nhân viên"
                : "Edit employee"
              : vi
                ? "Thêm nhân viên AI"
                : "Add AI employee"
          }
          onClose={() => setDraft(null)}
          wide
        >
          <AgentWizard
            draft={draft}
            setDraft={setDraft}
            step={step}
            setStep={setStep}
            departments={departments}
            models={modelPool}
            skills={skills}
            servers={servers}
            vi={vi}
            onSave={save}
            onDelete={remove}
          />
        </Dialog>
      ) : null}
      {departmentsOpen ? (
        <DepartmentsDialog
          departments={departments}
          agents={agents}
          vi={vi}
          onClose={() => setDepartmentsOpen(false)}
          onReload={reloadSupporting}
          toast={toast}
          confirm={confirm}
        />
      ) : null}
    </div>
  );
}

/** Bộ chọn hình đại diện: xem trước + lưới hình + lưới màu.
 *
 *  Thay cho hai ô <select> chỉ hiện chữ thô ("bot", "mint"). Người dùng chọn
 *  mặt mũi cho nhân viên của mình — phải nhìn thấy nó, không phải đọc tên khoá. */
function AvatarPicker({
  name,
  shape,
  color,
  onShape,
  onColor,
  vi,
}: {
  name: string;
  shape: string;
  color: string;
  onShape: (value: string) => void;
  onColor: (value: string) => void;
  vi: boolean;
}) {
  const tooltip = useTooltipText();
  const tone = avatarColor(color);
  return (
    <div className={c("avatarPicker")}>
      <div className={c("avatarPreview")}>
        <Avatar agent={{ name, avatar_icon: shape, avatar_color: color }} size={64} />
        <div>
          <strong>{name.trim() || (vi ? "Nhân viên mới" : "New employee")}</strong>
          <span>
            {AVATAR_SHAPE_LABEL[shape] ?? shape} · {tone.label}
          </span>
        </div>
      </div>

      <div className={c("pickerGroup")}>
        <span className={c("pickerLabel")}>{vi ? "Chọn hình" : "Shape"}</span>
        <div className={c("shapeGrid")}>
          {AVATAR_SHAPE_KEYS.map((key) => (
            <Tooltip key={key} label={tooltip("tooltip.agents.shape", AVATAR_SHAPE_LABEL[key] ?? key)}>
              <button
                type="button"
                aria-label={tooltip("tooltip.agents.shape", AVATAR_SHAPE_LABEL[key] ?? key)}
                aria-pressed={key === shape}
                className={key === shape ? c("shapeOptOn") : c("shapeOpt")}
                onClick={() => onShape(key)}
              >
                <svg
                  viewBox="0 0 24 24"
                  width={20}
                  height={20}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                  dangerouslySetInnerHTML={{ __html: shapePath(key) }}
                />
              </button>
            </Tooltip>
          ))}
        </div>
      </div>

      <div className={c("pickerGroup")}>
        <span className={c("pickerLabel")}>{vi ? "Chọn màu" : "Colour"}</span>
        <div className={c("colorGrid")}>
          {AVATAR_COLOR_KEYS.map((key) => {
            const item = avatarColor(key);
            return (
              <Tooltip key={key} label={tooltip("tooltip.agents.color", item.label)}>
                <button
                  type="button"
                  aria-label={tooltip("tooltip.agents.color", item.label)}
                  aria-pressed={key === color}
                  className={key === color ? c("colorOptOn") : c("colorOpt")}
                  style={{ background: item.bg, color: item.ink }}
                  onClick={() => onColor(key)}
                >
                  <svg
                    viewBox="0 0 24 24"
                    width={16}
                    height={16}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                    dangerouslySetInnerHTML={{ __html: shapePath(shape) }}
                  />
                </button>
              </Tooltip>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/** Chip hình đại diện. Vẽ đúng hình và màu nhân viên đã chọn.
 *
 *  Trước đây hàm này bỏ qua `avatar_icon` hoàn toàn và chỉ hiện chữ cái đầu —
 *  nghĩa là cả ô "Hình đại diện" trong form không có tác dụng gì. */
function Avatar({ agent, size = 48 }: { agent: Pick<AgentRecord, "name" | "avatar_icon" | "avatar_color">; size?: number }) {
  const tone = avatarColor(agent.avatar_color);
  return (
    <span
      className={c("avatar")}
      style={{ width: size, height: size, background: tone.bg, color: tone.ink }}
      title={agent.name}
    >
      <svg
        viewBox="0 0 24 24"
        width={Math.round(size * 0.58)}
        height={Math.round(size * 0.58)}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        dangerouslySetInnerHTML={{ __html: shapePath(agent.avatar_icon) }}
      />
    </span>
  );
}

function AgentWizard({
  draft,
  setDraft,
  step,
  setStep,
  departments,
  models,
  skills,
  servers,
  vi,
  onSave,
  onDelete,
}: {
  draft: AgentDraft;
  setDraft: (draft: AgentDraft) => void;
  step: number;
  setStep: (step: number) => void;
  departments: Department[];
  models: ModelRecord[];
  skills: SkillRecord[];
  servers: McpServer[];
  vi: boolean;
  onSave: () => void;
  onDelete: () => void;
}) {
  const tooltip = useTooltipText();
  const set = <K extends keyof AgentDraft>(key: K, value: AgentDraft[K]) =>
    setDraft({ ...draft, [key]: value });
  const next = () => {
    if (step === 1 && !draft.name.trim()) return;
    setStep(Math.min(5, step + 1));
  };
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (step < 5) next();
        else onSave();
      }}
    >
      <div className={c("wizardTabs")}>
        {[
          vi ? "Danh tính" : "Identity",
          vi ? "Phòng & model" : "Team & models",
          vi ? "Chỉ dẫn" : "Instructions",
          vi ? "Kỹ năng" : "Skills",
          vi ? "Xem lại" : "Review",
        ].map((label, index) => (
          <Tooltip
            key={label}
            label={tooltip(draft.id ? "tooltip.agents.wizard_step" : "tooltip.agents.wizard_step_locked", label)}
          >
            <button
              data-testid={`agent-step-${index + 1}`}
              type="button"
              className={step === index + 1 ? c("wizardActive") : step > index + 1 ? c("wizardDone") : ""}
              onClick={() => draft.id && setStep(index + 1)}
            >
              <span>{step > index + 1 ? "✓" : index + 1}</span>
              {label}
            </button>
          </Tooltip>
        ))}
      </div>
      {step === 1 ? (
        <div className={c("formGrid")}>
          <Field label={vi ? "Tên nhân viên" : "Employee name"} required>
            <input
              data-testid="agent-name"
              className={c("input")}
              value={draft.name}
              onChange={(event) => set("name", event.target.value)}
            />
          </Field>
          <Field label={vi ? "Vai trò" : "Role"}>
            <input
              className={c("input")}
              value={draft.role}
              onChange={(event) => set("role", event.target.value)}
            />
          </Field>
        </div>
      ) : null}
      {step === 1 ? (
        <AvatarPicker
          name={draft.name}
          shape={draft.avatar_icon}
          color={draft.avatar_color}
          onShape={(value) => set("avatar_icon", value)}
          onColor={(value) => set("avatar_color", value)}
          vi={vi}
        />
      ) : null}
      {step === 2 ? (
        <div className={c("formStack")}>
          <Field label={vi ? "Phòng ban" : "Department"}>
            <select
              className={c("select")}
              value={draft.department_id}
              onChange={(event) => set("department_id", event.target.value)}
            >
              <option value="">—</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label={vi ? "Model ưu tiên (tối đa 5, theo thứ tự)" : "Preferred models (up to 5, in order)"}
          >
            <div className={c("orderedPicker")}>
              <select
                className={c("select")}
                value=""
                onChange={(event) => {
                  const id = Number(event.target.value);
                  if (id && !draft.model_pool_ids.includes(id) && draft.model_pool_ids.length < 5)
                    set("model_pool_ids", [...draft.model_pool_ids, id]);
                }}
              >
                <option value="">+ {vi ? "Thêm model" : "Add model"}</option>
                {models
                  .filter((model) => !draft.model_pool_ids.includes(model.id))
                  .map((model) => (
                    <option value={model.id} key={model.id}>
                      {model.name}
                    </option>
                  ))}
              </select>
              {draft.model_pool_ids.map((id, index) => (
                <div key={id}>
                  <b>
                    {index + 1}. {models.find((model) => model.id === id)?.name || `#${id}`}
                  </b>
                  <span>
                    <Tooltip
                      label={tooltip(
                        index ? "tooltip.agents.model_up" : "tooltip.agents.model_up_locked",
                        models.find((model) => model.id === id)?.name || `#${id}`,
                      )}
                    >
                      <button
                        type="button"
                        aria-label={tooltip(
                          index ? "tooltip.agents.model_up" : "tooltip.agents.model_up_locked",
                          models.find((model) => model.id === id)?.name || `#${id}`,
                        )}
                        onClick={() =>
                          index && set("model_pool_ids", move(draft.model_pool_ids, index, index - 1))
                        }
                      >
                        ↑
                      </button>
                    </Tooltip>
                    <Tooltip
                      label={tooltip(
                        index < draft.model_pool_ids.length - 1
                          ? "tooltip.agents.model_down"
                          : "tooltip.agents.model_down_locked",
                        models.find((model) => model.id === id)?.name || `#${id}`,
                      )}
                    >
                      <button
                        type="button"
                        aria-label={tooltip(
                          index < draft.model_pool_ids.length - 1
                            ? "tooltip.agents.model_down"
                            : "tooltip.agents.model_down_locked",
                          models.find((model) => model.id === id)?.name || `#${id}`,
                        )}
                        onClick={() =>
                          index < draft.model_pool_ids.length - 1 &&
                          set("model_pool_ids", move(draft.model_pool_ids, index, index + 1))
                        }
                      >
                        ↓
                      </button>
                    </Tooltip>
                    <Tooltip
                      label={tooltip(
                        "tooltip.agents.model_remove",
                        models.find((model) => model.id === id)?.name || `#${id}`,
                      )}
                    >
                      <button
                        type="button"
                        aria-label={tooltip(
                          "tooltip.agents.model_remove",
                          models.find((model) => model.id === id)?.name || `#${id}`,
                        )}
                        onClick={() =>
                          set(
                            "model_pool_ids",
                            draft.model_pool_ids.filter((item) => item !== id),
                          )
                        }
                      >
                        ×
                      </button>
                    </Tooltip>
                  </span>
                </div>
              ))}
            </div>
          </Field>
        </div>
      ) : null}
      {step === 3 ? (
        <Field label="System prompt">
          <textarea
            className={c("textarea")}
            rows={12}
            value={draft.system_prompt}
            onChange={(event) => set("system_prompt", event.target.value)}
          />
        </Field>
      ) : null}
      {step === 4 ? (
        <div className={c("skillPicker")}>
          {skills.map((skill) => {
            const selected = draft.skills.includes(skill.id);
            const server = servers.find((item) => item.skill_id === skill.id);
            const available = server?.available || [];
            return (
              <article key={skill.id} className={selected ? c("skillPicked") : ""}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() =>
                      set(
                        "skills",
                        selected ? draft.skills.filter((id) => id !== skill.id) : [...draft.skills, skill.id],
                      )
                    }
                  />
                  <strong>{skill.name}</strong>
                  <span>{skill.type}</span>
                </label>
                {selected && skill.type === "mcp" ? (
                  <div className={c("toolPicker")}>
                    {available.length ? (
                      available.map((toolName) => {
                        const explicit = draft.skill_tools[String(skill.id)];
                        const checked = !explicit || explicit.includes(toolName);
                        return (
                          <label key={toolName}>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) => {
                                const current = explicit || [...available];
                                const nextTools = event.target.checked
                                  ? [...new Set([...current, toolName])]
                                  : current.filter((name) => name !== toolName);
                                const nextMap = { ...draft.skill_tools };
                                if (nextTools.length === available.length) delete nextMap[String(skill.id)];
                                else nextMap[String(skill.id)] = nextTools;
                                set("skill_tools", nextMap);
                              }}
                            />
                            <code>{toolName}</code>
                          </label>
                        );
                      })
                    ) : (
                      <small>
                        {server?.error || (vi ? "MCP chưa phơi ra tool" : "No MCP tools available")}
                      </small>
                    )}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}
      {step === 5 ? (
        <div className={c("reviewGrid")}>
          <Review label={vi ? "Tên" : "Name"} value={draft.name} />
          <Review label={vi ? "Vai trò" : "Role"} value={draft.role} />
          <Review
            label={vi ? "Phòng ban" : "Department"}
            value={departments.find((item) => String(item.id) === draft.department_id)?.name || "—"}
          />
          <Review
            label="Models"
            value={
              draft.model_pool_ids
                .map((id) => models.find((model) => model.id === id)?.name)
                .filter(Boolean)
                .join(", ") || "—"
            }
          />
          <Review
            label={vi ? "Kỹ năng" : "Skills"}
            value={
              draft.skills
                .map((id) => skills.find((skill) => skill.id === id)?.name)
                .filter(Boolean)
                .join(", ") || "—"
            }
          />
          <Review label="System prompt" value={draft.system_prompt || "—"} />
        </div>
      ) : null}
      <footer className={c("formActions")}>
        {draft.id ? (
          <Tooltip label={tooltip("tooltip.agents.delete", draft.name)}>
            <button data-testid="delete-agent" type="button" className={c("dangerLink")} onClick={onDelete}>
              {vi ? "Xoá nhân viên" : "Delete employee"}
            </button>
          </Tooltip>
        ) : (
          <span />
        )}
        <div>
          {step > 1 ? (
            <Tooltip label={tooltip("tooltip.agents.back")}>
              <button type="button" className={c("buttonGhost")} onClick={() => setStep(step - 1)}>
                {vi ? "Quay lại" : "Back"}
              </button>
            </Tooltip>
          ) : null}
          <Tooltip
            label={tooltip(step === 5 ? "tooltip.agents.save" : "tooltip.agents.continue", draft.name)}
          >
            <button data-testid="agent-next-save" type="submit" className={c("primaryButton")}>
              {step === 5 ? (vi ? "Lưu" : "Save") : vi ? "Tiếp tục" : "Continue"}
            </button>
          </Tooltip>
        </div>
      </footer>
    </form>
  );
}

function DepartmentsDialog({
  departments,
  agents,
  vi,
  onClose,
  onReload,
  toast,
  confirm,
}: {
  departments: Department[];
  agents: AgentRecord[];
  vi: boolean;
  onClose: () => void;
  onReload: () => Promise<void>;
  toast: (message: string, kind?: "success" | "error" | "info") => void;
  confirm: (message: string) => Promise<boolean>;
}) {
  const tooltip = useTooltipText();
  const [editing, setEditing] = useState<Partial<Department> | null>(null);
  const save = async () => {
    if (!editing?.name?.trim()) return;
    const body = {
      name: editing.name.trim(),
      description: editing.description || "",
      color: editing.color || "#9366ff",
      head_agent_id: editing.head_agent_id || null,
    };
    if (editing.id) await apiClient.patch(`/departments/${editing.id}`, body);
    else await apiClient.post("/departments/", body);
    setEditing(null);
    await onReload();
    toast(vi ? "Đã lưu phòng ban" : "Department saved", "success");
  };
  const remove = async (department: Department) => {
    if (!(await confirm(vi ? "Xoá phòng ban này?" : "Delete this department?"))) return;
    await apiClient.delete(`/departments/${department.id}`);
    await onReload();
  };
  return (
    <Dialog title={vi ? "Phòng ban" : "Departments"} onClose={onClose}>
      <Tooltip label={tooltip("tooltip.agents.department_create")}>
        <button
          className={c("primaryButton")}
          onClick={() => setEditing({ name: "", description: "", color: "#9366ff" })}
        >
          + {vi ? "Thêm phòng" : "Add department"}
        </button>
      </Tooltip>
      <div className={c("managementList")}>
        {departments.map((department) => (
          <div key={department.id}>
            <i style={{ background: department.color }} />
            <span>
              <strong>{department.name}</strong>
              <small>
                {agents.find((agent) => agent.id === department.head_agent_id)?.name ||
                  (vi ? "Chưa có trưởng phòng" : "No department head")}
              </small>
            </span>
            <Tooltip label={tooltip("tooltip.agents.department_edit", department.name)}>
              <button
                aria-label={tooltip("tooltip.agents.department_edit", department.name)}
                onClick={() => setEditing(department)}
              >
                <Icon name="edit" />
              </button>
            </Tooltip>
            <Tooltip label={tooltip("tooltip.agents.department_delete", department.name)}>
              <button
                aria-label={tooltip("tooltip.agents.department_delete", department.name)}
                onClick={() => void remove(department)}
              >
                <Icon name="trash" />
              </button>
            </Tooltip>
          </div>
        ))}
      </div>
      {editing ? (
        <div className={c("nestedForm")}>
          <Field label={vi ? "Tên phòng" : "Department name"}>
            <input
              className={c("input")}
              value={editing.name || ""}
              onChange={(event) => setEditing({ ...editing, name: event.target.value })}
            />
          </Field>
          <Field label={vi ? "Mô tả" : "Description"}>
            <textarea
              className={c("textarea")}
              value={editing.description || ""}
              onChange={(event) => setEditing({ ...editing, description: event.target.value })}
            />
          </Field>
          <Field label={vi ? "Trưởng phòng" : "Department head"}>
            <select
              className={c("select")}
              value={editing.head_agent_id || ""}
              onChange={(event) =>
                setEditing({ ...editing, head_agent_id: Number(event.target.value) || null })
              }
            >
              <option value="">—</option>
              {agents.map((agent) => (
                <option value={agent.id} key={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
          <div className={c("formActions")}>
            <Tooltip label={tooltip("tooltip.agents.department_cancel")}>
              <button className={c("buttonGhost")} onClick={() => setEditing(null)}>
                {vi ? "Huỷ" : "Cancel"}
              </button>
            </Tooltip>
            <Tooltip label={tooltip("tooltip.agents.department_save", editing.name || "")}>
              <button className={c("primaryButton")} onClick={() => void save()}>
                {vi ? "Lưu" : "Save"}
              </button>
            </Tooltip>
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}

function move<T>(values: T[], from: number, to: number): T[] {
  const next = [...values];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
function Field({
  label,
  children,
  required,
}: {
  label: string;
  children: React.ReactNode;
  required?: boolean;
}) {
  return (
    <label className={c("field")}>
      <span>
        {label}
        {required ? " *" : ""}
      </span>
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
