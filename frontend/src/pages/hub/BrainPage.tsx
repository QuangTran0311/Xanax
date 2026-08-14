import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage, type Language } from "../../store/language";
import { BenchmarkPage, type Benchmark } from "./BenchmarkPage";
import { Dialog } from "./Dialog";
import { ExperimentSection } from "./ExperimentSection";
import { useHub } from "./HubContext";
import { hubText, type HubMessageKey } from "./i18n";
import type { ModelRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
const API_STYLES = [
  "openai_compat",
  "openai_native",
  "anthropic_native",
  "gemini_native",
  "claude_cli",
  "codex_cli",
] as const;
const CLI_API_STYLES = new Set<string>(["claude_cli", "codex_cli"]);
const API_STYLE_LABELS: Record<(typeof API_STYLES)[number], HubMessageKey> = {
  openai_compat: "brain.api_style.openai_compat",
  openai_native: "brain.api_style.openai_native",
  anthropic_native: "brain.api_style.anthropic_native",
  gemini_native: "brain.api_style.gemini_native",
  claude_cli: "brain.api_style.claude_cli",
  codex_cli: "brain.api_style.codex_cli",
};
const API_STYLE_DESCRIPTIONS: Record<(typeof API_STYLES)[number], HubMessageKey> = {
  openai_compat: "brain.api_style_description.openai_compat",
  openai_native: "brain.api_style_description.openai_native",
  anthropic_native: "brain.api_style_description.anthropic_native",
  gemini_native: "brain.api_style_description.gemini_native",
  claude_cli: "brain.api_style_description.claude_cli",
  codex_cli: "brain.api_style_description.codex_cli",
};
const PROVIDER_SUGGESTIONS: Record<(typeof API_STYLES)[number], string> = {
  openai_compat: "OpenAI-compatible",
  openai_native: "OpenAI",
  anthropic_native: "Anthropic",
  gemini_native: "Gemini",
  claude_cli: "Claude CLI",
  codex_cli: "Codex CLI",
};

interface ModelDraft {
  id?: number;
  name: string;
  provider: string;
  api_style: string;
  model_id: string;
  base_url: string;
  api_key: string;
  cli_config_dir: string;
  category: string;
  max_requests_per_day: number;
  max_tokens_per_day: number;
  price_input_per_1m: number;
  price_cache_per_1m: number;
  price_output_per_1m: number;
  currency: string;
  enabled: boolean;
}
type EditableModelRecord = ModelRecord & { api_key?: string };

const blankModel = (): ModelDraft => ({
  name: "",
  provider: PROVIDER_SUGGESTIONS.openai_compat,
  api_style: "openai_compat",
  model_id: "",
  base_url: "",
  api_key: "",
  cli_config_dir: "",
  category: "general",
  max_requests_per_day: 0,
  max_tokens_per_day: 0,
  price_input_per_1m: 0,
  price_cache_per_1m: 0,
  price_output_per_1m: 0,
  currency: "USD",
  enabled: true,
});

function isModelEnabled(model: ModelRecord): boolean {
  return model.enabled !== false && model.enabled !== 0;
}

function compactNumber(value: number): string {
  const absolute = Math.abs(value);
  const compact = (divisor: number, suffix: string) => {
    const result = (value / divisor).toFixed(1).replace(/\.0$/, "");
    return `${result}${suffix}`;
  };
  if (absolute >= 1_000_000_000) return compact(1_000_000_000, "B");
  if (absolute >= 1_000_000) return compact(1_000_000, "M");
  if (absolute >= 1_000) return compact(1_000, "K");
  return String(value);
}

function formatCurrency(
  value: number,
  currency: string,
  language: Language,
  exact = false,
): string {
  try {
    return new Intl.NumberFormat(language === "vi" ? "vi-VN" : "en-US", {
      style: "currency",
      currency: currency || "USD",
      notation: !exact && Math.abs(value) >= 10_000 ? "compact" : "standard",
      minimumFractionDigits: exact ? 2 : undefined,
      maximumFractionDigits: exact ? 6 : value > 0 && value < 0.01 ? 4 : 2,
    }).format(value);
  } catch {
    // Mã tiền tệ tự nhập có thể chưa đúng chuẩn ISO; vẫn hiển thị được giá trị.
    return `${value.toLocaleString(language === "vi" ? "vi-VN" : "en-US")} ${currency || "USD"}`;
  }
}

export function BrainPage() {
  const { language } = useLanguage();
  const vi = language === "vi";
  const tooltip = useTooltipText();
  const t = (key: HubMessageKey) => hubText(language, key);
  const [section, setSection] = useState<
    "pool" | "benchmarks" | "experiments"
  >("pool");
  const [modelCreateRequest, setModelCreateRequest] = useState(0);
  const [benchmarkCreateRequest, setBenchmarkCreateRequest] = useState(0);
  const [experimentCreateRequest, setExperimentCreateRequest] = useState(0);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const loadBenchmarks = useCallback(async () => {
    const data = await apiClient.get<{ benchmarks: Benchmark[] }>("/benchmarks/");
    setBenchmarks(data.benchmarks || []);
  }, []);

  useEffect(() => {
    void loadBenchmarks();
  }, [loadBenchmarks]);

  const selectSection = (next: "pool" | "benchmarks" | "experiments") => {
    if (next !== "pool") setModelCreateRequest(0);
    if (next !== "benchmarks") setBenchmarkCreateRequest(0);
    if (next !== "experiments") setExperimentCreateRequest(0);
    setSection(next);
  };

  return (
    <div className={c("page")}>
      <div className={c("modelToolbar")}>
        <nav className={c("benchmarkModeTabs")} aria-label={t("brain.tabs.label")}>
          <Tooltip label={tooltip("tooltip.brain.pool_open")}>
            <button
              data-testid="model-pool-tab"
              className={section === "pool" ? c("benchmarkModeActive") : ""}
              aria-current={section === "pool" ? "page" : undefined}
              onClick={() => selectSection("pool")}
            >
              <Icon name="brain" />
              {t("brain.tab.pool")}
            </button>
          </Tooltip>
          <Tooltip label={tooltip("tooltip.experiment.tab_benchmarks")}>
            <button
              data-testid="benchmark-tab"
              className={section === "benchmarks" ? c("benchmarkModeActive") : ""}
              aria-current={section === "benchmarks" ? "page" : undefined}
              onClick={() => selectSection("benchmarks")}
            >
              <Icon name="scale" />
              {t("experiment.tab.benchmarks")}
            </button>
          </Tooltip>
          <Tooltip label={tooltip("tooltip.experiment.tab_experiments")}>
            <button
              data-testid="experiment-tab"
              className={section === "experiments" ? c("benchmarkModeActive") : ""}
              aria-current={section === "experiments" ? "page" : undefined}
              onClick={() => selectSection("experiments")}
            >
              <Icon name="layers" />
              {t("experiment.tab.experiments")}
            </button>
          </Tooltip>
        </nav>
        <div className={c("headerActions")}>
          {section === "pool" ? (
            <Tooltip label={tooltip("tooltip.brain.model_create")}>
              <button
                data-testid="new-model"
                className={c("primaryButton")}
                onClick={() => setModelCreateRequest((current) => current + 1)}
              >
                <Icon name="brain" />
                {vi ? "Thêm model" : "Add model"}
              </button>
            </Tooltip>
          ) : section === "benchmarks" ? (
            <Tooltip label={tooltip("tooltip.benchmark.create_open")}>
              <button
                data-testid="new-benchmark"
                className={c("primaryButton")}
                onClick={() => setBenchmarkCreateRequest((current) => current + 1)}
              >
                <Icon name="flask" />
                {vi ? "Tạo bài đánh giá" : "Create benchmark"}
              </button>
            </Tooltip>
          ) : (
            <Tooltip label={tooltip("tooltip.experiment.create_open")}>
              <button
                data-testid="new-experiment"
                className={c("primaryButton")}
                onClick={() => setExperimentCreateRequest((current) => current + 1)}
              >
                <Icon name="flask" />
                {t("experiment.action.create")}
              </button>
            </Tooltip>
          )}
        </div>
      </div>
      {section === "pool" ? (
        <ModelPoolPage createRequest={modelCreateRequest} />
      ) : (
        <>
          <BenchmarkPage
            benchmarks={benchmarks}
            createRequest={benchmarkCreateRequest}
            refreshBenchmarks={loadBenchmarks}
            hidden={section !== "benchmarks"}
          />
          {section === "experiments" ? (
            <ExperimentSection
              benchmarks={benchmarks}
              createRequest={experimentCreateRequest}
            />
          ) : null}
        </>
      )}
    </div>
  );
}

function ModelPoolPage({ createRequest }: { createRequest: number }) {
  const { language } = useLanguage();
  const vi = language === "vi";
  const tooltip = useTooltipText();
  const { modelPool, refreshModelPool, toast, confirm } = useHub();
  const [draft, setDraft] = useState<ModelDraft | null>(null);
  const [testing, setTesting] = useState<Set<number>>(() => new Set());
  const [enabledOverrides, setEnabledOverrides] = useState<Record<number, boolean>>({});
  const [toggling, setToggling] = useState<Set<number>>(() => new Set());
  const t = (key: HubMessageKey) => hubText(language, key);
  const locale = language === "vi" ? "vi-VN" : "en-US";
  const showCategory = new Set(
    modelPool.map((model) => model.category || "general"),
  ).size >= 2;
  const open = (model?: ModelRecord) =>
    setDraft(
      model
        ? {
            ...blankModel(),
            id: model.id,
            name: model.name || "",
            provider: model.provider || "9router",
            api_style: model.api_style || "openai_compat",
            model_id: model.model_id || "",
            base_url: String(model.base_url || ""),
            // Giữ secret trong draft để ô bị ẩn vẫn được gửi lại nguyên giá trị khi lưu.
            api_key: String((model as EditableModelRecord).api_key ?? ""),
            cli_config_dir: String(model.cli_config_dir || ""),
            category: model.category || "general",
            max_requests_per_day: Number(model.max_requests_per_day || 0),
            max_tokens_per_day: Number(model.max_tokens_per_day || 0),
            price_input_per_1m: Number(model.price_input_per_1m || 0),
            price_cache_per_1m: Number(model.price_cache_per_1m || 0),
            price_output_per_1m: Number(model.price_output_per_1m || 0),
            currency: String(model.currency || "USD"),
            enabled: isModelEnabled(model),
          }
        : blankModel(),
    );

  useEffect(() => {
    if (createRequest > 0) open();
  }, [createRequest]);

  const save = async () => {
    if (!draft?.name.trim() || !draft.model_id.trim())
      return toast(
        vi ? "Tên và Model ID là bắt buộc" : "Name and model ID are required",
        "error",
      );
    const body: Partial<ModelDraft> = {
      ...draft,
      name: draft.name.trim(),
      model_id: draft.model_id.trim(),
    };
    delete body.id;
    try {
      if (draft.id) await apiClient.patch(`/model-pool/${draft.id}`, body);
      else {
        // API tạo mới chưa nhận enabled; tạo xong mới tắt nếu người dùng yêu cầu.
        const { enabled, ...createBody } = body;
        const created = await apiClient.post<ModelRecord>("/model-pool", createBody);
        if (enabled === false)
          await apiClient.patch(`/model-pool/${created.id}`, { enabled: false });
      }
      await refreshModelPool();
      setDraft(null);
      toast(vi ? "Đã lưu model" : "Model saved", "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Save failed", "error");
    }
  };
  const remove = async (model: ModelRecord) => {
    if (!(await confirm(vi ? "Xoá model này?" : "Delete this model?"))) return;
    await apiClient.delete(`/model-pool/${model.id}`);
    await refreshModelPool();
  };
  const test = async (model: ModelRecord) => {
    if (testing.has(model.id)) return;
    setTesting((current) => new Set(current).add(model.id));
    try {
      const result = await apiClient.post<{ ok: boolean; error?: string }>(
        `/model-pool/${model.id}/test`,
      );
      const message = `${t(
        result.ok ? "brain.test_success" : "brain.test_failure",
      )}: ${model.name}`;
      toast(
        !result.ok && result.error ? `${message} — ${result.error}` : message,
        result.ok ? "success" : "error",
      );
    } catch (error) {
      const detail = error instanceof Error ? ` — ${error.message}` : "";
      toast(`${t("brain.test_failure")}: ${model.name}${detail}`, "error");
    } finally {
      setTesting((current) => {
        const updated = new Set(current);
        updated.delete(model.id);
        return updated;
      });
    }
  };
  const toggleEnabled = async (model: ModelRecord, enabled: boolean) => {
    if (toggling.has(model.id)) return;
    const nextEnabled = !enabled;
    setEnabledOverrides((current) => ({ ...current, [model.id]: nextEnabled }));
    setToggling((current) => new Set(current).add(model.id));
    try {
      await apiClient.patch(`/model-pool/${model.id}`, { enabled: nextEnabled });
      toast(
        t(nextEnabled ? "brain.toggle_enabled_toast" : "brain.toggle_disabled_toast"),
        "success",
      );
      try {
        await refreshModelPool();
        setEnabledOverrides((current) => {
          const updated = { ...current };
          delete updated[model.id];
          return updated;
        });
      } catch {
        // Giữ trạng thái lạc quan nếu PATCH đã thành công nhưng lần tải lại lỗi.
      }
    } catch (error) {
      setEnabledOverrides((current) => {
        const updated = { ...current };
        delete updated[model.id];
        return updated;
      });
      const detail = error instanceof Error ? `: ${error.message}` : "";
      toast(`${t("brain.toggle_error")}${detail}`, "error");
    } finally {
      setToggling((current) => {
        const updated = new Set(current);
        updated.delete(model.id);
        return updated;
      });
    }
  };
  return (
    <>
      <section className={c("modelGrid")}>
        {modelPool.map((model) => {
          const usage = model.usage_today || {};
          const enabled = enabledOverrides[model.id] ?? isModelEnabled(model);
          const isTesting = testing.has(model.id);
          const isToggling = toggling.has(model.id);
          const requestCount = Number(usage.request_count || 0);
          const tokensInput = Number(usage.tokens_input || 0);
          const tokensOutput = Number(usage.tokens_output || 0);
          const tokensUsed = tokensInput + tokensOutput;
          const requestLimit = Number(model.max_requests_per_day || 0);
          const tokenLimit = Number(model.max_tokens_per_day || 0);
          const requestRatio = requestLimit > 0 ? requestCount / requestLimit : 0;
          const tokenRatio = tokenLimit > 0 ? tokensUsed / tokenLimit : 0;
          const usageRatio = Math.max(requestRatio, tokenRatio);
          const hasDailyLimit = requestLimit > 0 || tokenLimit > 0;
          const progressPercent = Math.min(usageRatio * 100, 100);
          const hasPricing =
            Number(model.price_input_per_1m || 0) > 0 ||
            Number(model.price_output_per_1m || 0) > 0;
          const estimatedCost =
            (tokensInput / 1_000_000) * Number(model.price_input_per_1m || 0) +
            (tokensOutput / 1_000_000) * Number(model.price_output_per_1m || 0);
          const currency = model.currency || "USD";
          const fullRequests = requestCount.toLocaleString(locale);
          const fullRequestLimit = requestLimit.toLocaleString(locale);
          const fullTokens = tokensUsed.toLocaleString(locale);
          const fullTokenLimit = tokenLimit.toLocaleString(locale);
          return (
            <article key={model.id} className={c("modelCard")}>
              <header className={c("modelCardHeader")}>
                <div className={c("modelIdentity")}>
                  <h2>{model.name}</h2>
                  <p>
                    {model.model_id} · {model.provider}
                  </p>
                </div>
                <Tooltip
                  label={tooltip(
                    isToggling
                      ? "tooltip.brain.model_toggle_running"
                      : enabled
                        ? "tooltip.brain.model_disable"
                        : "tooltip.brain.model_enable",
                    model.name || "",
                  )}
                >
                  <button
                    type="button"
                    role="switch"
                    aria-checked={enabled}
                    aria-label={tooltip(
                      enabled
                        ? "tooltip.brain.model_disable"
                        : "tooltip.brain.model_enable",
                      model.name || "",
                    )}
                    className={c("modelToggle")}
                    disabled={isToggling}
                    onClick={() => void toggleEnabled(model, enabled)}
                  >
                    <span>{t(enabled ? "brain.enabled" : "brain.disabled")}</span>
                    <i aria-hidden="true" />
                  </button>
                </Tooltip>
              </header>

              <div className={c("modelCost")}>
                <span>{t("brain.cost_today")}</span>
                {hasPricing ? (
                  <Tooltip
                    label={tooltip(
                      "tooltip.brain.cost_exact",
                      formatCurrency(estimatedCost, currency, language, true),
                    )}
                  >
                    <strong tabIndex={0}>
                      {formatCurrency(estimatedCost, currency, language)}
                    </strong>
                  </Tooltip>
                ) : (
                  <Tooltip label={tooltip("tooltip.brain.price_unset")}>
                    <strong className={c("modelPriceUnset")} tabIndex={0}>
                      {t("brain.price_unset")}
                    </strong>
                  </Tooltip>
                )}
              </div>

              <div className={c("modelUsage")}>
                <p>
                  <Tooltip
                    label={tooltip(
                      requestLimit > 0
                        ? "tooltip.brain.requests_limited"
                        : "tooltip.brain.requests_unlimited",
                      fullRequests,
                      fullRequestLimit,
                    )}
                  >
                    <span className={c("modelUsageMetric")} tabIndex={0}>
                      {compactNumber(requestCount)}
                      {requestLimit > 0 ? ` / ${compactNumber(requestLimit)}` : ""}{" "}
                      {t("brain.calls")}
                    </span>
                  </Tooltip>
                  <span aria-hidden="true">·</span>
                  <Tooltip
                    label={tooltip(
                      tokenLimit > 0
                        ? "tooltip.brain.tokens_limited"
                        : "tooltip.brain.tokens_unlimited",
                      fullTokens,
                      fullTokenLimit,
                    )}
                  >
                    <span className={c("modelUsageMetric")} tabIndex={0}>
                      {compactNumber(tokensUsed)}
                      {tokenLimit > 0 ? ` / ${compactNumber(tokenLimit)}` : ""}{" "}
                      {t("brain.tokens")}
                    </span>
                  </Tooltip>
                </p>
                {hasDailyLimit ? (
                  <Tooltip
                    label={tooltip(
                      "tooltip.brain.usage_progress",
                      Math.round(usageRatio * 100),
                    )}
                  >
                    <div
                      className={`${c("modelProgress")} ${
                        usageRatio >= 1
                          ? c("modelProgressDanger")
                        : usageRatio > 0.8
                            ? c("modelProgressWarning")
                            : ""
                      }`}
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={Math.round(progressPercent)}
                      tabIndex={0}
                    >
                      <i style={{ width: `${progressPercent}%` }} />
                    </div>
                  </Tooltip>
                ) : null}
              </div>

              {showCategory ? (
                <div className={c("modelCategory")}>
                  <span className={c("tag")}>{model.category || "general"}</span>
                </div>
              ) : null}

              <footer className={c("modelActions")}>
                <Tooltip
                  label={tooltip(
                    isTesting ? "tooltip.brain.model_test_running" : "tooltip.brain.model_test",
                    model.name || "",
                  )}
                >
                  <button
                    className={c("buttonGhost")}
                    disabled={isTesting}
                    onClick={() => void test(model)}
                  >
                    <Icon name="plug" />
                    {isTesting ? "…" : vi ? "Kiểm tra" : "Test"}
                  </button>
                </Tooltip>
                <Tooltip label={tooltip("tooltip.brain.model_edit", model.name || "")}>
                  <button
                    data-testid={`edit-model-${model.id}`}
                    className={c("buttonGhost")}
                    onClick={() => open(model)}
                  >
                    <Icon name="edit" />
                    {vi ? "Sửa" : "Edit"}
                  </button>
                </Tooltip>
                <Tooltip label={tooltip("tooltip.brain.model_delete", model.name || "")}>
                  <button
                    data-testid={`delete-model-${model.id}`}
                    className={c("dangerLink")}
                    aria-label={tooltip("tooltip.brain.model_delete", model.name || "")}
                    onClick={() => void remove(model)}
                  >
                    <Icon name="trash" />
                  </button>
                </Tooltip>
              </footer>
            </article>
          );
        })}
      </section>
      {draft ? (
        <ModelDialog
          draft={draft}
          setDraft={setDraft}
          vi={vi}
          onSave={save}
          onClose={() => setDraft(null)}
        />
      ) : null}
    </>
  );
}

function ModelDialog({
  draft,
  setDraft,
  vi,
  onSave,
  onClose,
}: {
  draft: ModelDraft;
  setDraft: (draft: ModelDraft) => void;
  vi: boolean;
  onSave: () => Promise<void>;
  onClose: () => void;
}) {
  const { language } = useLanguage();
  const tooltip = useTooltipText();
  const [step, setStep] = useState(1);
  const [showConnectionErrors, setShowConnectionErrors] = useState(false);
  const t = (key: HubMessageKey) => hubText(language, key);
  const set = <K extends keyof ModelDraft>(key: K, value: ModelDraft[K]) =>
    setDraft({ ...draft, [key]: value });
  const isCli = CLI_API_STYLES.has(draft.api_style);
  const missingBaseUrl = !isCli && !draft.base_url.trim();
  const missingApiKey = !isCli && !draft.api_key.trim();
  const connectionInvalid = missingBaseUrl || missingApiKey;
  const goToStep = (targetStep: number) => {
    if (targetStep > 2 && connectionInvalid) {
      setShowConnectionErrors(true);
      setStep(2);
      return;
    }
    setStep(Math.max(1, Math.min(4, targetStep)));
  };
  const next = () => {
    // Tên hiển thị và Model ID là hai trường backend thực sự bắt buộc khi tạo model.
    if (step === 1 && (!draft.name.trim() || !draft.model_id.trim())) return;
    goToStep(step + 1);
  };
  const stepLabels = [
    t("brain.section.identity"),
    t("brain.section.connection"),
    t("brain.step.limits"),
    t("brain.section.pricing"),
  ];
  return (
    <Dialog
      title={
        draft.id
          ? vi
            ? "Sửa model"
            : "Edit model"
          : vi
            ? "Thêm model"
            : "Add model"
      }
      onClose={onClose}
      wide
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (step < 4) next();
          else void onSave();
        }}
      >
        <div className={c("wizardTabs")}>
          {stepLabels.map((label, index) => (
            <Tooltip
              key={label}
              label={tooltip(
                draft.id
                  ? "tooltip.brain.wizard_step"
                  : "tooltip.brain.wizard_step_locked",
                label,
              )}
            >
              <button
                data-testid={`model-step-${index + 1}`}
                type="button"
                className={
                  step === index + 1
                    ? c("wizardActive")
                    : step > index + 1
                      ? c("wizardDone")
                      : ""
                }
                onClick={() => draft.id && goToStep(index + 1)}
              >
                <span>{step > index + 1 ? "✓" : index + 1}</span>
                {label}
              </button>
            </Tooltip>
          ))}
        </div>
        <div className={c("modelForm")}>
          {step === 1 ? (
            <FormSection title={t("brain.section.identity")}>
              <div className={c("formGrid")}>
                <Field label={t("brain.display_name")} required>
                  <input
                    data-testid="model-name"
                    className={c("input")}
                    value={draft.name}
                    required
                    onChange={(event) => set("name", event.target.value)}
                  />
                </Field>
                <Field label="Model ID" required>
                  <input
                    data-testid="model-id"
                    className={c("input")}
                    value={draft.model_id}
                    required
                    onChange={(event) => set("model_id", event.target.value)}
                  />
                </Field>
                <Field label={t("brain.category")}>
                  <select
                    className={c("select")}
                    value={draft.category}
                    onChange={(event) => set("category", event.target.value)}
                  >
                    {["general", "coding", "creative", "fast", "analysis"].map(
                      (category) => (
                        <option key={category}>{category}</option>
                      ),
                    )}
                  </select>
                </Field>
                <div className={c("field")}>
                  <span>{t("brain.enabled_field")}</span>
                  <Tooltip
                    label={tooltip(
                      draft.enabled
                        ? "tooltip.brain.dialog_disable"
                        : "tooltip.brain.dialog_enable",
                    )}
                  >
                    <button
                      type="button"
                      role="switch"
                      aria-checked={draft.enabled}
                      className={`${c("modelToggle")} ${c("modelFormToggle")}`}
                      onClick={() => set("enabled", !draft.enabled)}
                    >
                      <span>{t(draft.enabled ? "brain.enabled" : "brain.disabled")}</span>
                      <i aria-hidden="true" />
                    </button>
                  </Tooltip>
                </div>
              </div>
            </FormSection>
          ) : null}

          {step === 2 ? (
            <FormSection title={t("brain.section.connection")}>
              <div className={c("formGrid")}>
                <fieldset className={`${c("apiStyleFieldset")} ${c("modelFieldWide")}`}>
                  <legend>{t("brain.connection_method")}</legend>
                  <div className={c("apiStyleChoices")}>
                    {API_STYLES.map((style) => {
                      const selected = draft.api_style === style;
                      return (
                        <Tooltip
                          key={style}
                          label={tooltip(
                            "tooltip.brain.connection_method",
                            t(API_STYLE_LABELS[style]),
                            t(API_STYLE_DESCRIPTIONS[style]),
                          )}
                        >
                          <label
                            className={`${c("apiStyleChoice")} ${selected ? c("apiStyleChoiceSelected") : ""}`}
                          >
                            <input
                              className={c("apiStyleRadio")}
                              type="radio"
                              name="model-api-style"
                              value={style}
                              checked={selected}
                              onChange={() => {
                                // Provider chỉ là nhãn hiển thị, nên gợi ý lại nhưng vẫn cho phép sửa ở ô cuối bước.
                                setDraft({
                                  ...draft,
                                  api_style: style,
                                  provider: PROVIDER_SUGGESTIONS[style],
                                });
                              }}
                            />
                            <span className={c("apiStyleChoiceHeader")}>
                              <span className={c("apiStyleIndicator")} aria-hidden="true" />
                              <strong>{t(API_STYLE_LABELS[style])}</strong>
                              <span className={c("apiStylePill")}>
                                {CLI_API_STYLES.has(style) ? "CLI" : "HTTP"}
                              </span>
                            </span>
                            <span className={c("apiStyleDescription")}>
                              {t(API_STYLE_DESCRIPTIONS[style])}
                            </span>
                          </label>
                        </Tooltip>
                      );
                    })}
                  </div>
                </fieldset>
                {!isCli ? (
                  <>
                    <Field
                      label={t("brain.base_url")}
                      required
                      error={showConnectionErrors && missingBaseUrl ? t("brain.base_url_required") : undefined}
                    >
                      <Tooltip label={tooltip("tooltip.brain.base_url")}>
                        <input
                          className={c("input")}
                          value={draft.base_url}
                          required
                          aria-invalid={showConnectionErrors && missingBaseUrl}
                          onChange={(event) => set("base_url", event.target.value)}
                        />
                      </Tooltip>
                    </Field>
                    <Field
                      label={t("brain.api_key")}
                      required
                      error={showConnectionErrors && missingApiKey ? t("brain.api_key_required") : undefined}
                    >
                      <Tooltip label={tooltip("tooltip.brain.api_key")}>
                        <input
                          className={c("input")}
                          type="password"
                          value={draft.api_key}
                          required
                          aria-invalid={showConnectionErrors && missingApiKey}
                          onChange={(event) => set("api_key", event.target.value)}
                        />
                      </Tooltip>
                    </Field>
                  </>
                ) : (
                  <Field label={t("brain.cli_config_dir")} wide>
                    <Tooltip label={tooltip("tooltip.brain.cli_config_dir")}>
                      <input
                        className={c("input")}
                        value={draft.cli_config_dir}
                        onChange={(event) => set("cli_config_dir", event.target.value)}
                      />
                    </Tooltip>
                  </Field>
                )}
                <Field label={t("brain.provider_label")} wide>
                  <Tooltip label={tooltip("tooltip.brain.provider_label")}>
                    <input
                      className={c("input")}
                      value={draft.provider}
                      onChange={(event) => set("provider", event.target.value)}
                    />
                  </Tooltip>
                </Field>
              </div>
            </FormSection>
          ) : null}

          {step === 3 ? (
            <FormSection title={t("brain.section.limits")}>
              <div className={c("formGrid")}>
                <NumberField
                  label={t("brain.calls_limit")}
                  value={draft.max_requests_per_day}
                  set={(value) => set("max_requests_per_day", value)}
                />
                <NumberField
                  label={t("brain.tokens_limit")}
                  value={draft.max_tokens_per_day}
                  set={(value) => set("max_tokens_per_day", value)}
                />
              </div>
            </FormSection>
          ) : null}

          {step === 4 ? (
            <FormSection title={t("brain.section.pricing")}>
              <div className={c("formGrid")}>
                <NumberField
                  label="Input / 1M"
                  value={draft.price_input_per_1m}
                  set={(value) => set("price_input_per_1m", value)}
                />
                <NumberField
                  label="Cache / 1M"
                  value={draft.price_cache_per_1m}
                  set={(value) => set("price_cache_per_1m", value)}
                />
                <NumberField
                  label="Output / 1M"
                  value={draft.price_output_per_1m}
                  set={(value) => set("price_output_per_1m", value)}
                />
                <Field label={t("brain.currency")}>
                  <input
                    className={c("input")}
                    value={draft.currency}
                    onChange={(event) => set("currency", event.target.value)}
                  />
                </Field>
              </div>
            </FormSection>
          ) : null}
        </div>
        <footer className={`${c("formActions")} ${c("modelFormActions")}`}>
          <Tooltip label={tooltip("tooltip.common.cancel_dialog")}>
            <button type="button" className={c("buttonGhost")} onClick={onClose}>
              {hubText(language, "common.cancel")}
            </button>
          </Tooltip>
          <div>
            {step > 1 ? (
              <Tooltip label={tooltip("tooltip.brain.back")}>
                <button
                  type="button"
                  className={c("buttonGhost")}
                  onClick={() => setStep(step - 1)}
                >
                  {vi ? "Quay lại" : "Back"}
                </button>
              </Tooltip>
            ) : null}
            <Tooltip
              label={tooltip(
                step === 4
                  ? "tooltip.brain.model_save"
                  : step === 1 && (!draft.name.trim() || !draft.model_id.trim())
                    ? "tooltip.brain.continue_required"
                    : step === 2 && connectionInvalid
                      ? "tooltip.brain.continue_connection_required"
                    : "tooltip.brain.continue",
                draft.name || "",
              )}
            >
              <button data-testid="save-model" type="submit" className={c("primaryButton")}>
                {step === 4 ? (vi ? "Lưu" : "Save") : vi ? "Tiếp" : "Continue"}
              </button>
            </Tooltip>
          </div>
        </footer>
      </form>
    </Dialog>
  );
}
function NumberField({
  label,
  value,
  set,
}: {
  label: string;
  value: number;
  set: (value: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        className={c("input")}
        type="number"
        min={0}
        step="any"
        value={value}
        onChange={(event) => set(Number(event.target.value) || 0)}
      />
    </Field>
  );
}
function Field({
  label,
  children,
  required = false,
  wide = false,
  error,
}: {
  label: string;
  children: React.ReactNode;
  required?: boolean;
  wide?: boolean;
  error?: string;
}) {
  return (
    <label className={`${c("field")} ${wide ? c("modelFieldWide") : ""}`}>
      <span>
        {label}
        {required ? " *" : ""}
      </span>
      {children}
      {error ? <small className={c("modelFieldError")} role="alert">{error}</small> : null}
    </label>
  );
}

function FormSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className={c("modelFormSection")}>
      <header>
        <h3>{title}</h3>
      </header>
      {children}
    </section>
  );
}
