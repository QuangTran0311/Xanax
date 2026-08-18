import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { useWebSocket } from "../../ws/useWebSocket";
import { useHub } from "./HubContext";
import { hubText, type HubMessageKey } from "./i18n";
import styles from "./HubPage.module.css";
import type { AgentRecord, ModelRecord, ProjectRecord } from "./types";

const c = (name: string) => styles[name] ?? name;

const CONDITIONS = [
  "khong_soul",
  "soul_nhan_vien",
  "them_ky_nang",
  "day_du",
] as const;

const TRIAL_LIFECYCLE_STATUSES = [
  "pending",
  "running",
  "generated",
  "judging",
  "scored",
] as const;

type ExperimentCondition = (typeof CONDITIONS)[number];

interface ExperimentBenchmark {
  id: number;
  name: string;
  status: string;
  test_cases: Array<{ prompt: string; criteria: string }>;
}

interface ExperimentWarning {
  code: string;
  message: string;
}

interface ExperimentRecord {
  id: number;
  name: string;
  status: string;
  agent_id: number;
  agent_name?: string;
  project_id: number;
  project_name?: string;
  benchmark_id: number;
  benchmark_name?: string;
  measured_model_pool_id: number;
  measured_model_name?: string;
  judge_model_pool_id: number;
  judge_model_name?: string;
  repetitions: number;
  total_trials: number;
  completed_trials: number;
  scored_trials: number;
  warnings: ExperimentWarning[];
  error_text?: string;
  created_at?: string;
}

interface ExperimentTrial {
  id: number;
  condition: ExperimentCondition;
  case_index: number;
  repetition: number;
  execution_order: number;
  prompt: string;
  criteria: string;
  response: string;
  score: number | null;
  score_reason: string;
  response_classification?: "answered" | "clarify" | "conflict";
  status: string;
  error_text?: string;
  elapsed_seconds?: number;
  tokens_input?: number;
  tokens_cache?: number;
  tokens_output?: number;
}

interface SummaryRow {
  condition: ExperimentCondition;
  mean: number | null;
  stddev: number | null;
  n: number;
  total_n: number;
  clarify_n: number;
  clarify_rate: number;
  conflict_n: number;
  conflict_rate: number;
  insufficient_answered: boolean;
  delta_vs_control: number | null;
  delta_standard_error?: number | null;
  delta_confidence_margin_95?: number | null;
  delta_distinguishable?: boolean;
}

interface CaseSummary {
  case_index: number;
  prompt: string;
  conditions: SummaryRow[];
}

interface ExperimentSummary {
  experiment_id?: number;
  status?: string;
  conditions: SummaryRow[];
  cases: CaseSummary[];
  score_population?: string;
  minimum_answered?: number;
  stddev_method?: string;
  delta_confidence_level?: number;
  delta_confidence_z?: number;
}

interface ExperimentDetail {
  experiment: ExperimentRecord;
  trials: ExperimentTrial[];
}

interface ExperimentProgress {
  status: string;
  totalTrials: number;
  completedTrials: number;
  scoredTrials: number;
  caseIndex: number | null;
  remainingInCase: number | null;
}

type ExperimentEvent = {
  type: string;
  experiment_id?: number;
  status?: string;
  total_trials?: number;
  completed_trials?: number;
  scored_trials?: number;
  trial_id?: number;
  execution_order?: number;
  case_index?: number;
  remaining_in_case?: number;
  summary?: ExperimentSummary;
  message?: string;
};

interface ExperimentDraft {
  name: string;
  agent_id: string;
  project_id: string;
  benchmark_id: string;
  measured_model_pool_id: string;
  judge_model_pool_id: string;
  repetitions: number;
}

const EMPTY_PROGRESS: ExperimentProgress = {
  status: "pending",
  totalTrials: 0,
  completedTrials: 0,
  scoredTrials: 0,
  caseIndex: null,
  remainingInCase: null,
};

function progressFromRecord(record: ExperimentRecord): ExperimentProgress {
  return {
    status: record.status,
    totalTrials: record.total_trials || 0,
    completedTrials: record.completed_trials || 0,
    scoredTrials: record.scored_trials || 0,
    caseIndex: null,
    remainingInCase: null,
  };
}

function isActiveStatus(status: string): boolean {
  return status === "running" || status === "starting" || status === "cancelling";
}

export function ExperimentSection({
  benchmarks,
  createRequest,
}: {
  benchmarks: ExperimentBenchmark[];
  createRequest: number;
}) {
  const { language } = useLanguage();
  const tooltip = useTooltipText();
  const { agents, projects, modelPool, toast } = useHub();
  const t = useCallback(
    (key: HubMessageKey) => hubText(language, key),
    [language],
  );
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selectedIdRef = useRef<number | null>(null);
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [summary, setSummary] = useState<ExperimentSummary | null>(null);
  const [progress, setProgress] = useState<ExperimentProgress>(EMPTY_PROGRESS);
  const [creating, setCreating] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [command, setCommand] = useState<{
    id: number;
    type: "run" | "cancel";
  } | null>(null);

  const enabledModels = useMemo(
    () => modelPool.filter((model) => Boolean(model.enabled)),
    [modelPool],
  );
  const [draft, setDraft] = useState<ExperimentDraft>(() =>
    newExperimentDraft([], [], [], []),
  );

  const loadExperiments = useCallback(async () => {
    try {
      const data = await apiClient.get<{ experiments: ExperimentRecord[] }>(
        "/experiments/",
      );
      setExperiments(data.experiments || []);
    } catch (error) {
      toast(error instanceof Error ? error.message : t("experiment.error.load"), "error");
    }
  }, [t, toast]);

  const loadDetail = useCallback(async (id: number, showLoading = false) => {
    if (showLoading) setLoadingDetail(true);
    try {
      const [nextDetail, nextSummary] = await Promise.all([
        apiClient.get<ExperimentDetail>(`/experiments/${id}`),
        apiClient.get<ExperimentSummary>(`/experiments/${id}/summary`),
      ]);
      if (selectedIdRef.current !== id) return;
      setDetail(nextDetail);
      setSummary(nextSummary);
      setProgress((current) => ({
        ...progressFromRecord(nextDetail.experiment),
        caseIndex: current.caseIndex,
        remainingInCase: current.remainingInCase,
      }));
    } catch (error) {
      if (selectedIdRef.current === id) {
        toast(error instanceof Error ? error.message : t("experiment.error.load"), "error");
      }
    } finally {
      if (selectedIdRef.current === id) setLoadingDetail(false);
    }
  }, [t, toast]);

  const openExperiment = useCallback((record: ExperimentRecord) => {
    selectedIdRef.current = record.id;
    setSelectedId(record.id);
    setCreating(false);
    setCommand(null);
    setDetail(null);
    setSummary(null);
    setProgress(progressFromRecord(record));
    void loadDetail(record.id, true);
  }, [loadDetail]);

  const openCreate = useCallback(() => {
    selectedIdRef.current = null;
    setSelectedId(null);
    setDetail(null);
    setSummary(null);
    setProgress(EMPTY_PROGRESS);
    setCommand(null);
    setDraft(newExperimentDraft(agents, projects, benchmarks, enabledModels));
    setCreating(true);
  }, [agents, benchmarks, enabledModels, projects]);

  useEffect(() => {
    void loadExperiments();
  }, [loadExperiments]);

  useEffect(() => {
    if (createRequest > 0) openCreate();
  }, [createRequest, openCreate]);

  const handleSocketMessage = useCallback((message: ExperimentEvent) => {
    if (message.experiment_id && message.experiment_id !== selectedIdRef.current) return;

    if (message.type === "snapshot") {
      setProgress((current) => ({
        ...current,
        status: message.status || current.status,
        totalTrials: message.total_trials ?? current.totalTrials,
        completedTrials: message.completed_trials ?? current.completedTrials,
        scoredTrials: message.scored_trials ?? current.scoredTrials,
      }));
      if (message.summary) setSummary(message.summary);
      return;
    }

    if (message.type === "started") {
      setProgress({
        status: "running",
        totalTrials: message.total_trials || 0,
        completedTrials: 0,
        scoredTrials: 0,
        caseIndex: null,
        remainingInCase: null,
      });
      if (selectedIdRef.current) void loadDetail(selectedIdRef.current);
      void loadExperiments();
      return;
    }

    if (message.type === "generation_progress") {
      setProgress((current) => ({
        ...current,
        status: "running",
        totalTrials: message.total_trials ?? current.totalTrials,
        completedTrials: message.completed_trials ?? current.completedTrials,
        scoredTrials: message.scored_trials ?? current.scoredTrials,
      }));
      return;
    }

    if (message.type === "judging_progress") {
      setProgress((current) => ({
        ...current,
        status: "running",
        totalTrials: message.total_trials ?? current.totalTrials,
        completedTrials: message.completed_trials ?? current.completedTrials,
        scoredTrials: message.scored_trials ?? current.scoredTrials,
        caseIndex: message.case_index ?? current.caseIndex,
        remainingInCase: message.remaining_in_case ?? current.remainingInCase,
      }));
      if (selectedIdRef.current) void loadDetail(selectedIdRef.current);
      return;
    }

    if (message.type === "complete") {
      setProgress((current) => ({
        ...current,
        status: message.status || "completed",
        totalTrials: message.total_trials ?? current.totalTrials,
        completedTrials: message.completed_trials ?? current.completedTrials,
        scoredTrials: message.scored_trials ?? current.scoredTrials,
      }));
      if (message.summary) setSummary(message.summary);
      if (selectedIdRef.current) void loadDetail(selectedIdRef.current);
      void loadExperiments();
      toast(t("experiment.toast.complete"), "success");
      return;
    }

    if (message.type === "cancelled") {
      setProgress((current) => ({ ...current, status: "cancelled" }));
      if (selectedIdRef.current) void loadDetail(selectedIdRef.current);
      void loadExperiments();
      toast(t("experiment.toast.cancelled"), "info");
      return;
    }

    if (message.type === "error") {
      setProgress((current) => ({ ...current, status: "failed" }));
      if (selectedIdRef.current) void loadDetail(selectedIdRef.current);
      void loadExperiments();
      toast(message.message || t("experiment.error.socket"), "error");
      return;
    }

    if (message.type === "run_rejected" || message.type === "cancel_rejected") {
      toast(t("experiment.error.command"), "error");
    }
  }, [loadDetail, loadExperiments, t, toast]);

  const { state: socketState, isOpen, send } = useWebSocket<ExperimentEvent>({
    path: `/ws/experiments/${selectedId ?? 0}`,
    enabled: selectedId !== null,
    connectionKey: selectedId,
    onMessage: handleSocketMessage,
  });

  useEffect(() => {
    if (!command || command.id !== selectedId || !isOpen) return;
    send({ type: command.type });
    setCommand(null);
  }, [command, isOpen, selectedId, send]);

  const createAndRun = async () => {
    if (
      !draft.name.trim()
      || !draft.agent_id
      || !draft.project_id
      || !draft.benchmark_id
      || !draft.measured_model_pool_id
      || draft.repetitions < 1
      || draft.repetitions > 20
    ) {
      toast(t("experiment.form.validation"), "error");
      return;
    }
    try {
      const created = await apiClient.post<ExperimentRecord>("/experiments/", {
        name: draft.name.trim(),
        agent_id: Number(draft.agent_id),
        project_id: Number(draft.project_id),
        benchmark_id: Number(draft.benchmark_id),
        measured_model_pool_id: Number(draft.measured_model_pool_id),
        judge_model_pool_id: draft.judge_model_pool_id
          ? Number(draft.judge_model_pool_id)
          : undefined,
        repetitions: draft.repetitions,
      });
      selectedIdRef.current = created.id;
      setSelectedId(created.id);
      setCreating(false);
      setDetail({ experiment: created, trials: [] });
      setSummary(null);
      setProgress(progressFromRecord(created));
      setCommand({ id: created.id, type: "run" });
      await loadExperiments();
      toast(t("experiment.toast.created"), "success");
    } catch (error) {
      toast(error instanceof Error ? error.message : t("experiment.error.create"), "error");
    }
  };

  const requestRun = () => {
    if (selectedId !== null) setCommand({ id: selectedId, type: "run" });
  };

  const requestCancel = () => {
    if (selectedId === null) return;
    setProgress((current) => ({ ...current, status: "cancelling" }));
    setCommand({ id: selectedId, type: "cancel" });
  };

  return (
    <div className={c("experimentWorkspace")} data-testid="experiments-section">
      <div className={c("splitView")}>
        <aside className={`${c("sideList")} ${c("experimentList")}`}>
          <header>
            <strong>{t("experiment.list.title")}</strong>
            <small>{experiments.length}</small>
          </header>
          {experiments.length ? experiments.map((experiment) => (
            <Tooltip
              key={experiment.id}
              label={tooltip("tooltip.experiment.open", experiment.name)}
            >
              <button
                data-testid={`experiment-item-${experiment.id}`}
                className={selectedId === experiment.id ? c("sideSelected") : ""}
                onClick={() => openExperiment(experiment)}
              >
                <strong>{experiment.name}</strong>
                <small>
                  {statusLabel(experiment.status, t)} · {experiment.scored_trials || 0}/
                  {experiment.total_trials || 0}
                </small>
              </button>
            </Tooltip>
          )) : (
            <p className={c("experimentListEmpty")}>{t("experiment.list.empty")}</p>
          )}
        </aside>

        <section className={`${c("detailPane")} ${c("experimentDetail")}`}>
          {creating ? (
            <ExperimentForm
              draft={draft}
              setDraft={setDraft}
              agents={agents}
              projects={projects}
              benchmarks={benchmarks}
              models={enabledModels}
              onCancel={() => setCreating(false)}
              onRun={createAndRun}
            />
          ) : selectedId !== null ? (
            loadingDetail && !detail ? (
              <div className={c("empty")}>{t("common.loading")}</div>
            ) : detail ? (
              <ExperimentDetailView
                detail={detail}
                summary={summary}
                progress={progress}
                socketState={socketState}
                onRun={requestRun}
                onCancel={requestCancel}
              />
            ) : null
          ) : (
            <div className={c("empty")}>
              <Icon name="flask" />
              {t("experiment.empty")}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function newExperimentDraft(
  agents: AgentRecord[],
  projects: ProjectRecord[],
  benchmarks: ExperimentBenchmark[],
  models: ModelRecord[],
): ExperimentDraft {
  return {
    name: "",
    agent_id: agents[0]?.id ? String(agents[0].id) : "",
    project_id: projects[0]?.id ? String(projects[0].id) : "",
    benchmark_id: benchmarks[0]?.id ? String(benchmarks[0].id) : "",
    measured_model_pool_id: models[0]?.id ? String(models[0].id) : "",
    judge_model_pool_id: "",
    repetitions: 3,
  };
}

function ExperimentForm({
  draft,
  setDraft,
  agents,
  projects,
  benchmarks,
  models,
  onCancel,
  onRun,
}: {
  draft: ExperimentDraft;
  setDraft: (draft: ExperimentDraft) => void;
  agents: AgentRecord[];
  projects: ProjectRecord[];
  benchmarks: ExperimentBenchmark[];
  models: ModelRecord[];
  onCancel: () => void;
  onRun: () => Promise<void>;
}) {
  const { language } = useLanguage();
  const tooltip = useTooltipText();
  const t = (key: HubMessageKey) => hubText(language, key);
  const selectedBenchmark = benchmarks.find(
    (benchmark) => String(benchmark.id) === draft.benchmark_id,
  );
  const caseCount = selectedBenchmark?.test_cases.filter(
    (testCase) => testCase.prompt.trim(),
  ).length || 0;
  const totalTrials = 4 * caseCount * draft.repetitions;

  return (
    <form
      className={c("experimentForm")}
      data-testid="experiment-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onRun();
      }}
    >
      <header className={c("detailHeader")}>
        <div>
          <h2>{t("experiment.form.title")}</h2>
          <p>{t("experiment.form.subtitle")}</p>
        </div>
      </header>
      <div className={c("formGrid")}>
        <ExperimentField label={t("experiment.form.name")} wide>
          <input
            data-testid="experiment-name"
            className={c("input")}
            value={draft.name}
            required
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          />
        </ExperimentField>
        <ExperimentField label={t("experiment.form.agent")}>
          <select
            data-testid="experiment-agent"
            className={c("select")}
            value={draft.agent_id}
            required
            onChange={(event) => setDraft({ ...draft, agent_id: event.target.value })}
          >
            <option value="">—</option>
            {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
          </select>
        </ExperimentField>
        <ExperimentField label={t("experiment.form.project")}>
          <select
            data-testid="experiment-project"
            className={c("select")}
            value={draft.project_id}
            required
            onChange={(event) => setDraft({ ...draft, project_id: event.target.value })}
          >
            <option value="">—</option>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </ExperimentField>
        <ExperimentField label={t("experiment.form.benchmark")}>
          <select
            data-testid="experiment-benchmark"
            className={c("select")}
            value={draft.benchmark_id}
            required
            onChange={(event) => setDraft({ ...draft, benchmark_id: event.target.value })}
          >
            <option value="">—</option>
            {benchmarks.map((benchmark) => (
              <option key={benchmark.id} value={benchmark.id}>
                {benchmark.name} ({benchmark.test_cases.filter((item) => item.prompt.trim()).length})
              </option>
            ))}
          </select>
        </ExperimentField>
        <ExperimentField label={t("experiment.form.repetitions")}>
          <input
            data-testid="experiment-repetitions"
            className={c("input")}
            type="number"
            min={1}
            max={20}
            value={draft.repetitions}
            required
            onChange={(event) => setDraft({
              ...draft,
              repetitions: Math.max(1, Math.min(20, Number(event.target.value) || 1)),
            })}
          />
        </ExperimentField>
        <ExperimentField label={t("experiment.form.measured_model")}>
          <select
            data-testid="experiment-measured-model"
            className={c("select")}
            value={draft.measured_model_pool_id}
            required
            onChange={(event) => setDraft({
              ...draft,
              measured_model_pool_id: event.target.value,
            })}
          >
            <option value="">—</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} · {model.model_id}
              </option>
            ))}
          </select>
        </ExperimentField>
        <ExperimentField label={t("experiment.form.judge_model")}>
          <select
            data-testid="experiment-judge-model"
            className={c("select")}
            value={draft.judge_model_pool_id}
            onChange={(event) => setDraft({
              ...draft,
              judge_model_pool_id: event.target.value,
            })}
          >
            <option value="">{t("experiment.form.judge_auto")}</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} · {model.model_id}
              </option>
            ))}
          </select>
        </ExperimentField>
      </div>

      <section className={c("experimentRunEstimate")} data-testid="experiment-run-estimate">
        <div>
          <span>{t("experiment.form.total_trials")}</span>
          <strong>{totalTrials.toLocaleString(language)}</strong>
        </div>
        <p>
          4 × {caseCount} × {draft.repetitions} = {totalTrials.toLocaleString(language)}
          {" "}{t("experiment.form.trial_unit")}
        </p>
        <p className={c("experimentCliWarning")}>
          <Icon name="warning" />
          {t("experiment.form.cli_warning")}
        </p>
      </section>

      <footer className={c("formActions")}>
        <span />
        <div>
          <Tooltip label={tooltip("tooltip.experiment.form_cancel")}>
            <button type="button" className={c("buttonGhost")} onClick={onCancel}>
              {t("common.cancel")}
            </button>
          </Tooltip>
          <Tooltip label={tooltip("tooltip.experiment.create_run")}>
            <button
              data-testid="create-run-experiment"
              type="submit"
              className={c("primaryButton")}
            >
              <Icon name="play" />
              {t("experiment.form.create_run")}
            </button>
          </Tooltip>
        </div>
      </footer>
    </form>
  );
}

function ExperimentField({
  label,
  wide = false,
  children,
}: {
  label: string;
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <label className={`${c("field")} ${wide ? c("experimentFieldWide") : ""}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function ExperimentDetailView({
  detail,
  summary,
  progress,
  socketState,
  onRun,
  onCancel,
}: {
  detail: ExperimentDetail;
  summary: ExperimentSummary | null;
  progress: ExperimentProgress;
  socketState: string;
  onRun: () => void;
  onCancel: () => void;
}) {
  const { language } = useLanguage();
  const tooltip = useTooltipText();
  const t = (key: HubMessageKey) => hubText(language, key);
  const experiment = detail.experiment;
  const sameJudgeWarning = experiment.warnings?.some(
    (warning) => warning.code === "judge_same_as_measured",
  );
  const hasPartialResults = (summary?.conditions || []).some(
    (row) => (row.total_n ?? row.n) > 0,
  );
  const generationPercent = percent(progress.completedTrials, progress.totalTrials);
  const judgingPercent = percent(progress.scoredTrials, progress.totalTrials);
  const active = isActiveStatus(progress.status);

  return (
    <div data-testid="experiment-detail">
      <header className={c("detailHeader")}>
        <div>
          <h2>{experiment.name}</h2>
          <p>
            {experiment.agent_name || "—"} · {experiment.project_name || "—"} ·
            {" "}{experiment.benchmark_name || "—"}
          </p>
        </div>
        <div className={c("experimentHeaderActions")}>
          <span className={`${c("statusBadge")} ${c("experimentStatusBadge")} ${c(`status_${progress.status}`)}`}>
            {statusLabel(progress.status, t)}
          </span>
          {progress.status === "pending" ? (
            <Tooltip label={tooltip("tooltip.experiment.run")}>
              <button
                data-testid="run-experiment"
                className={c("primaryButton")}
                onClick={onRun}
              >
                <Icon name="play" />
                {t("experiment.action.run")}
              </button>
            </Tooltip>
          ) : null}
          {active ? (
            <Tooltip label={tooltip("tooltip.experiment.cancel")}>
              <button
                data-testid="cancel-experiment"
                className={c("buttonDanger")}
                disabled={progress.status === "cancelling"}
                onClick={onCancel}
              >
                <Icon name="stop" />
                {t("experiment.action.cancel")}
              </button>
            </Tooltip>
          ) : null}
          <Tooltip label={tooltip("tooltip.experiment.download_csv", experiment.name)}>
            <a
              data-testid="download-experiment-csv"
              className={c("buttonGhost")}
              href={`/api/experiments/${experiment.id}/csv`}
              download
            >
              <Icon name="download" />
              CSV
            </a>
          </Tooltip>
        </div>
      </header>

      {sameJudgeWarning ? (
        <section className={c("experimentMethodWarning")} data-testid="judge-bias-warning">
          <Icon name="warning" />
          <div>
            <strong>{t("experiment.warning.title")}</strong>
            <p>{t("experiment.warning.judge_bias")}</p>
          </div>
        </section>
      ) : null}

      <dl className={c("experimentMetadata")}>
        <div><dt>{t("experiment.meta.measured")}</dt><dd>{experiment.measured_model_name || "—"}</dd></div>
        <div><dt>{t("experiment.meta.judge")}</dt><dd>{experiment.judge_model_name || "—"}</dd></div>
        <div><dt>{t("experiment.meta.repetitions")}</dt><dd>{experiment.repetitions}</dd></div>
        <div><dt>{t("experiment.meta.total")}</dt><dd>{progress.totalTrials || "—"}</dd></div>
      </dl>

      {(active || progress.totalTrials > 0) ? (
        <ExperimentProgressView
          progress={progress}
          generationPercent={generationPercent}
          judgingPercent={judgingPercent}
          socketState={socketState}
        />
      ) : null}

      {experiment.error_text ? (
        <p className={c("experimentErrorText")}>{experiment.error_text}</p>
      ) : null}

      {hasPartialResults ? (
        <ExperimentResults summary={summary!} trials={detail.trials} partial={active || progress.status === "cancelled"} />
      ) : detail.trials.length ? (
        <EvidenceList trials={detail.trials} />
      ) : (
        <div className={c("experimentNoResults")}>{t("experiment.results.empty")}</div>
      )}
    </div>
  );
}

function ExperimentProgressView({
  progress,
  generationPercent,
  judgingPercent,
  socketState,
}: {
  progress: ExperimentProgress;
  generationPercent: number;
  judgingPercent: number;
  socketState: string;
}) {
  const { language } = useLanguage();
  const t = (key: HubMessageKey) => hubText(language, key);
  return (
    <section className={c("experimentProgress")} data-testid="experiment-progress">
      <header>
        <h3>{t("experiment.progress.title")}</h3>
        {socketState !== "open" && isActiveStatus(progress.status) ? (
          <small>{t("experiment.progress.reconnecting")}</small>
        ) : null}
      </header>
      <div className={c("experimentProgressStage")}>
        <div>
          <strong>{t("experiment.progress.generation")}</strong>
          <span>{progress.completedTrials}/{progress.totalTrials} · {generationPercent}%</span>
        </div>
        <div
          className={c("experimentProgressTrack")}
          role="progressbar"
          aria-label={t("experiment.progress.generation")}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={generationPercent}
        >
          <i style={{ width: `${generationPercent}%` }} />
        </div>
      </div>
      <div className={c("experimentProgressStage")}>
        <div>
          <strong>{t("experiment.progress.judging")}</strong>
          <span>{progress.scoredTrials}/{progress.totalTrials} · {judgingPercent}%</span>
        </div>
        <div
          className={c("experimentProgressTrack")}
          role="progressbar"
          aria-label={t("experiment.progress.judging")}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={judgingPercent}
        >
          <i style={{ width: `${judgingPercent}%` }} />
        </div>
        {progress.caseIndex !== null ? (
          <small>
            {t("experiment.progress.current_case")} {progress.caseIndex + 1}
            {progress.remainingInCase !== null
              ? ` · ${progress.remainingInCase} ${t("experiment.progress.remaining")}`
              : ""}
          </small>
        ) : null}
      </div>
    </section>
  );
}

function ExperimentResults({
  summary,
  trials,
  partial,
}: {
  summary: ExperimentSummary;
  trials: ExperimentTrial[];
  partial: boolean;
}) {
  const { language } = useLanguage();
  const t = (key: HubMessageKey) => hubText(language, key);
  const orderedRows = CONDITIONS.map(
    (condition) => summary.conditions.find((row) => row.condition === condition),
  ).filter((row): row is SummaryRow => Boolean(row));
  const lowSampleRows = orderedRows.filter((row) => row.insufficient_answered);
  const minimumAnswered = summary.minimum_answered ?? 10;

  return (
    <div className={c("experimentResults")} data-testid="experiment-results">
      {partial ? (
        <p className={c("experimentPartialNotice")}>{t("experiment.results.partial")}</p>
      ) : null}
      <p className={c("experimentMethodNote")}>{t("experiment.results.answered_only_note")}</p>
      <p className={c("experimentMethodNote")}>{t("experiment.results.delta_noise_note")}</p>
      {lowSampleRows.length ? (
        <section
          className={c("experimentMethodWarning")}
          data-testid="experiment-small-sample-warning"
        >
          <Icon name="warning" />
          <div>
            <strong>{t("experiment.warning.small_sample_title")}</strong>
            <p>{t("experiment.warning.small_sample_detail")}</p>
            <p>
              {lowSampleRows.map((row) => (
                `${conditionLabel(row.condition, t)}: n=${row.n}/${minimumAnswered}`
              )).join(" · ")}
            </p>
          </div>
        </section>
      ) : null}
      <section data-testid="experiment-condition-table">
        <h3>{t("experiment.results.conditions")}</h3>
        <div className={c("experimentTableFrame")}>
          <table className={c("dataTable")}>
            <thead>
              <tr>
                <th>{t("experiment.column.condition")}</th>
                <th>{t("experiment.column.mean")}</th>
                <th>{t("experiment.column.stddev")}</th>
                <th>{t("experiment.column.answered_n")}</th>
                <th>{t("experiment.column.clarify")}</th>
                <th>{t("experiment.column.conflict")}</th>
                <th>{t("experiment.column.delta")}</th>
              </tr>
            </thead>
            <tbody>
              {orderedRows.map((row) => (
                <tr key={row.condition} className={row.condition === "khong_soul" ? c("experimentControlRow") : ""}>
                  <td>
                    <strong>{conditionLabel(row.condition, t)}</strong>
                    {row.condition === "khong_soul" ? <span>{t("experiment.control")}</span> : null}
                  </td>
                  <td>{formatScore(row.mean, language)}</td>
                  <td>{formatScore(row.stddev, language)}</td>
                  <td>{row.n}</td>
                  <td>{formatCountRate(row.clarify_n, row.clarify_rate, language)}</td>
                  <td>{formatCountRate(row.conflict_n, row.conflict_rate, language)}</td>
                  <td className={deltaClass(row)}>
                    <DeltaEstimate row={row} language={language} t={t} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section data-testid="experiment-chart">
        <h3>{t("experiment.results.chart")}</h3>
        <ConditionChart rows={orderedRows} />
      </section>

      <section data-testid="experiment-case-table">
        <h3>{t("experiment.results.cases")}</h3>
        <div className={`${c("experimentTableFrame")} ${c("experimentCaseTableFrame")}`}>
          <table className={c("dataTable")}>
            <thead>
              <tr>
                <th>{t("experiment.column.case")}</th>
                <th>{t("experiment.column.condition")}</th>
                <th>{t("experiment.column.mean")}</th>
                <th>{t("experiment.column.stddev")}</th>
                <th>{t("experiment.column.answered_n")}</th>
                <th>{t("experiment.column.clarify")}</th>
                <th>{t("experiment.column.conflict")}</th>
                <th>{t("experiment.column.delta")}</th>
              </tr>
            </thead>
            <tbody>
              {summary.cases.flatMap((caseRow) => CONDITIONS.map((condition, index) => {
                const row = caseRow.conditions.find((item) => item.condition === condition);
                if (!row) return null;
                return (
                  <tr key={`${caseRow.case_index}-${condition}`}>
                    {index === 0 ? (
                      <td rowSpan={4} className={c("experimentCaseCell")}>
                        <strong>{t("experiment.column.case")} {caseRow.case_index + 1}</strong>
                        <span>{caseRow.prompt}</span>
                      </td>
                    ) : null}
                    <td>{conditionLabel(condition, t)}</td>
                    <td>{formatScore(row.mean, language)}</td>
                    <td>{formatScore(row.stddev, language)}</td>
                    <td>{row.n}</td>
                    <td>{formatCountRate(row.clarify_n, row.clarify_rate, language)}</td>
                    <td>{formatCountRate(row.conflict_n, row.conflict_rate, language)}</td>
                    <td className={deltaClass(row)}>
                      <DeltaEstimate row={row} language={language} t={t} />
                    </td>
                  </tr>
                );
              }))}
            </tbody>
          </table>
        </div>
      </section>

      <EvidenceList trials={trials} />
    </div>
  );
}

function ConditionChart({ rows }: { rows: SummaryRow[] }) {
  const { language } = useLanguage();
  const t = (key: HubMessageKey) => hubText(language, key);
  const width = 760;
  const height = 390;
  const left = 54;
  const top = 24;
  const plotWidth = 686;
  const plotHeight = 274;
  const baseline = top + plotHeight;
  const y = (value: number) => top + ((10 - value) / 10) * plotHeight;
  const ticks = [0, 2, 4, 6, 8, 10];

  return (
    <figure className={c("experimentChartFigure")}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby="experiment-chart-title experiment-chart-description"
      >
        <title id="experiment-chart-title">{t("experiment.results.chart")}</title>
        <desc id="experiment-chart-description">{t("experiment.chart.legend")}</desc>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className={c("experimentChartGrid")} x1={left} x2={left + plotWidth} y1={y(tick)} y2={y(tick)} />
            <text className={c("experimentChartTick")} x={left - 10} y={y(tick) + 4} textAnchor="end">{tick}</text>
          </g>
        ))}
        <line className={c("experimentChartAxis")} x1={left} x2={left + plotWidth} y1={baseline} y2={baseline} />
        {CONDITIONS.map((condition, index) => {
          const row = rows.find((item) => item.condition === condition);
          const center = left + (plotWidth / CONDITIONS.length) * (index + 0.5);
          const mean = row?.mean;
          const stddev = row?.stddev || 0;
          if (mean === null || mean === undefined) {
            return (
              <g key={condition}>
                <text className={c("experimentChartValue")} x={center} y={baseline - 8} textAnchor="middle">—</text>
                <ChartLabel condition={condition} x={center} y={baseline + 26} t={t} />
              </g>
            );
          }
          const high = Math.min(10, mean + stddev);
          const low = Math.max(0, mean - stddev);
          return (
            <g key={condition} className={condition === "khong_soul" ? c("experimentControlBar") : c("experimentDataBar")}>
              <rect x={center - 38} y={y(mean)} width={76} height={baseline - y(mean)} rx={4} />
              <line className={c("experimentErrorBar")} x1={center} x2={center} y1={y(high)} y2={y(low)} />
              <line className={c("experimentErrorBar")} x1={center - 10} x2={center + 10} y1={y(high)} y2={y(high)} />
              <line className={c("experimentErrorBar")} x1={center - 10} x2={center + 10} y1={y(low)} y2={y(low)} />
              <text className={c("experimentChartValue")} x={center} y={Math.max(16, y(high) - 8)} textAnchor="middle">
                {formatScore(mean, language)}
              </text>
              <ChartLabel condition={condition} x={center} y={baseline + 26} t={t} />
            </g>
          );
        })}
      </svg>
      <figcaption>{t("experiment.chart.legend")}</figcaption>
    </figure>
  );
}

function ChartLabel({
  condition,
  x,
  y,
  t,
}: {
  condition: ExperimentCondition;
  x: number;
  y: number;
  t: (key: HubMessageKey) => string;
}) {
  return (
    <text className={c("experimentChartLabel")} x={x} y={y} textAnchor="middle">
      <tspan x={x}>{conditionChartLabel(condition, t)}</tspan>
      {condition === "khong_soul" ? <tspan x={x} dy="1.35em">({t("experiment.control")})</tspan> : null}
    </text>
  );
}

function EvidenceList({ trials }: { trials: ExperimentTrial[] }) {
  const { language } = useLanguage();
  const t = (key: HubMessageKey) => hubText(language, key);
  const ordered = [...trials].sort((first, second) =>
    first.case_index - second.case_index
    || CONDITIONS.indexOf(first.condition) - CONDITIONS.indexOf(second.condition)
    || first.repetition - second.repetition,
  );
  return (
    <section data-testid="experiment-evidence">
      <h3>{t("experiment.results.evidence")} ({ordered.length})</h3>
      <div className={c("experimentEvidenceLegend")}>
        {TRIAL_LIFECYCLE_STATUSES.map((status) => (
          <span key={status} className={c(`trial_${status}`)}>
            <i aria-hidden="true" />
            {trialStatusLabel(status, t)}
          </span>
        ))}
      </div>
      <div className={c("experimentEvidenceList")}>
        {ordered.map((trial) => (
          <details
            key={trial.id}
            className={`${c("experimentEvidenceCard")} ${c(`trial_${trial.status}`)}`}
            data-trial-status={trial.status}
          >
            <summary>
              <span>
                <strong>{t("experiment.column.case")} {trial.case_index + 1}</strong>
                <small>{conditionLabel(trial.condition, t)} · {t("experiment.evidence.repetition")} {trial.repetition}</small>
              </span>
              <span>
                <strong>{trial.score === null ? "—" : formatScore(trial.score, language)}</strong>
                <small className={c("trialStatusChip")}>{trialStatusLabel(trial.status, t)}</small>
              </span>
            </summary>
            <div className={c("experimentEvidenceBody")}>
              <EvidenceBlock title={t("experiment.evidence.prompt")} text={trial.prompt} />
              <EvidenceBlock title={t("experiment.evidence.criteria")} text={trial.criteria || "—"} />
              <EvidenceBlock title={t("experiment.evidence.response")} text={trial.response || t("experiment.evidence.no_response")} />
              <EvidenceBlock title={t("experiment.evidence.reason")} text={trial.score_reason || trial.error_text || "—"} />
              <dl>
                <div><dt>{t("experiment.evidence.score")}</dt><dd>{formatScore(trial.score, language)}</dd></div>
                <div><dt>{t("experiment.evidence.time")}</dt><dd>{formatSeconds(trial.elapsed_seconds, language)}</dd></div>
                <div><dt>{t("experiment.evidence.tokens")}</dt><dd>{(trial.tokens_input || 0) + (trial.tokens_cache || 0) + (trial.tokens_output || 0)}</dd></div>
                <div><dt>{t("experiment.evidence.order")}</dt><dd>{trial.execution_order}</dd></div>
              </dl>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function EvidenceBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className={c("experimentEvidenceBlock")}>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function percent(value: number, total: number): number {
  return total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
}

function formatScore(value: number | null | undefined, language: string): string {
  return value === null || value === undefined
    ? "—"
    : value.toLocaleString(language, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDelta(value: number | null, language: string): string {
  if (value === null) return "—";
  if (value === 0) return formatScore(0, language);
  return `${value > 0 ? "+" : ""}${formatScore(value, language)}`;
}

function DeltaEstimate({
  row,
  language,
  t,
}: {
  row: SummaryRow;
  language: string;
  t: (key: HubMessageKey) => string;
}) {
  const margin = row.delta_confidence_margin_95;
  const estimate = margin === null || margin === undefined
    ? formatDelta(row.delta_vs_control, language)
    : `${formatDelta(row.delta_vs_control, language)} ± ${formatScore(margin, language)}`;
  const isControl = row.condition === "khong_soul";
  const noiseLabel = margin === null || margin === undefined
    ? t("experiment.delta.noise_unavailable")
    : row.delta_distinguishable
      ? t("experiment.delta.outside_noise")
      : t("experiment.delta.inside_noise");

  return (
    <span className={c("experimentDeltaEstimate")}>
      <span>{estimate}</span>
      {!isControl && row.delta_vs_control !== null ? <small>{noiseLabel}</small> : null}
    </span>
  );
}

function formatCountRate(count: number, rate: number, language: string): string {
  const safeCount = count ?? 0;
  const safeRate = rate ?? 0;
  return `${safeCount} (${safeRate.toLocaleString(language, {
    style: "percent",
    maximumFractionDigits: 1,
  })})`;
}

function formatSeconds(value: number | undefined, language: string): string {
  if (value === undefined || value === null) return "—";
  return `${value.toLocaleString(language, { maximumFractionDigits: 2 })} s`;
}

function deltaClass(row: SummaryRow): string {
  // Chỉ tô màu khi hiệu đã vượt biên nhiễu 95%. Tô xanh/đỏ một hiệu còn nằm
  // trong nhiễu là mời người đọc kết luận sai; ở đây sai lầm đó có thể dẫn tới
  // quyết định gỡ tri thức khỏi nhân viên dù dữ liệu chưa chứng minh điều gì.
  if (!row.delta_distinguishable || row.delta_vs_control === null || row.delta_vs_control === 0) {
    return "";
  }
  return row.delta_vs_control > 0
    ? c("experimentDeltaPositive")
    : c("experimentDeltaNegative");
}

function conditionLabel(
  condition: ExperimentCondition,
  t: (key: HubMessageKey) => string,
): string {
  const keys: Record<ExperimentCondition, HubMessageKey> = {
    khong_soul: "experiment.condition.khong_soul",
    soul_nhan_vien: "experiment.condition.soul_nhan_vien",
    them_ky_nang: "experiment.condition.them_ky_nang",
    day_du: "experiment.condition.day_du",
  };
  return t(keys[condition]);
}

function conditionChartLabel(
  condition: ExperimentCondition,
  t: (key: HubMessageKey) => string,
): string {
  const keys: Record<ExperimentCondition, HubMessageKey> = {
    khong_soul: "experiment.chart.khong_soul",
    soul_nhan_vien: "experiment.chart.soul_nhan_vien",
    them_ky_nang: "experiment.chart.them_ky_nang",
    day_du: "experiment.chart.day_du",
  };
  return t(keys[condition]);
}

function statusLabel(status: string, t: (key: HubMessageKey) => string): string {
  const keys: Record<string, HubMessageKey> = {
    pending: "experiment.status.pending",
    starting: "experiment.status.starting",
    running: "experiment.status.running",
    cancelling: "experiment.status.cancelling",
    cancelled: "experiment.status.cancelled",
    completed: "experiment.status.completed",
    completed_with_errors: "experiment.status.completed_with_errors",
    failed: "experiment.status.failed",
  };
  return keys[status] ? t(keys[status]) : status;
}

function trialStatusLabel(status: string, t: (key: HubMessageKey) => string): string {
  const keys: Record<string, HubMessageKey> = {
    pending: "experiment.trial.pending",
    running: "experiment.trial.running",
    generated: "experiment.trial.generated",
    judging: "experiment.trial.judging",
    generation_error: "experiment.trial.generation_error",
    scored: "experiment.trial.scored",
    judge_error: "experiment.trial.judge_error",
    cancelled: "experiment.trial.cancelled",
  };
  return keys[status] ? t(keys[status]) : status;
}
