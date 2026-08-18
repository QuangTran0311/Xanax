import { useEffect, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage, type Language } from "../../store/language";
import { useHub } from "./HubContext";
import { hubText, type HubMessageKey } from "./i18n";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
export interface Benchmark {
  id: number;
  name: string;
  role_description?: string;
  status: string;
  models: string[];
  test_cases: TestCase[];
}
interface TestCase {
  prompt: string;
  criteria: string;
}
interface BenchmarkDraft {
  name: string;
  role_description: string;
  models: string[];
  test_cases: TestCase[];
}
interface Scores {
  quality: number;
  speed_score: number;
  avg_response_time: number;
  total: number;
}
interface Result {
  model: string;
  scores: Scores;
}
interface Progress {
  model: string;
  text: string;
  done?: boolean;
  scores?: Scores;
}

export function BenchmarkPage({
  benchmarks,
  createRequest,
  refreshBenchmarks,
  hidden,
}: {
  benchmarks: Benchmark[];
  createRequest: number;
  refreshBenchmarks: () => Promise<void>;
  hidden?: boolean;
}) {
  const { language } = useLanguage();
  const vi = language === "vi";
  const t = (key: HubMessageKey) => hubText(language, key);
  const tooltip = useTooltipText();
  const { modelPool, toast, confirm } = useHub();
  const [selected, setSelected] = useState<Benchmark | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<BenchmarkDraft>({
    name: "",
    role_description: "",
    models: [] as string[],
    test_cases: [{ prompt: "", criteria: "" }] as TestCase[],
  });
  const [progress, setProgress] = useState<Progress[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  useEffect(() => {
    if (createRequest <= 0) return;
    setCreating(true);
    setEditing(false);
    setSelected(null);
    setDraft({
      name: "",
      role_description: "",
      models: [],
      test_cases: [{ prompt: "", criteria: "" }],
    });
  }, [createRequest]);
  const open = async (benchmark: Benchmark) => {
    setSelected(benchmark);
    setCreating(false);
    setEditing(false);
    setProgress([]);
    setResults([]);
    if (benchmark.status === "completed") {
      const data = await apiClient.get<{
        results: Array<Result & { scores?: Scores; scores_json?: string }>;
      }>(`/benchmarks/${benchmark.id}/results`);
      setResults(
        (data.results || []).map((item) => ({
          model: item.model,
          scores:
            item.scores || (JSON.parse(item.scores_json || "{}") as Scores),
        })),
      );
    }
  };
  const createAndRun = async () => {
    const cases = draft.test_cases.filter((item) => item.prompt.trim());
    if (!draft.name.trim() || !draft.models.length || !cases.length)
      return toast(
        vi
          ? "Cần tên, ít nhất một model và một câu hỏi"
          : "Name, model, and test case are required",
        "error",
      );
    const benchmark = await apiClient.post<Benchmark>("/benchmarks/", {
      ...draft,
      name: draft.name.trim(),
      test_cases: cases,
    });
    setSelected(benchmark);
    setCreating(false);
    await refreshBenchmarks();
    run(benchmark.id, draft.models);
  };
  const edit = (benchmark: Benchmark) => {
    setSelected(benchmark);
    setCreating(false);
    setEditing(true);
    setDraft({
      name: benchmark.name,
      role_description: benchmark.role_description || "",
      models: [...(benchmark.models || [])],
      test_cases: benchmark.test_cases?.length
        ? benchmark.test_cases.map((item) => ({
            prompt: item.prompt,
            criteria: item.criteria || "",
          }))
        : [{ prompt: "", criteria: "" }],
    });
  };
  const save = async () => {
    if (!selected) return;
    const cases = draft.test_cases.filter((item) => item.prompt.trim());
    if (!draft.name.trim() || !cases.length) {
      toast(t("benchmark.validation.edit"), "error");
      return;
    }

    try {
      const prior = await apiClient.get<{ results: Result[] }>(
        `/benchmarks/${selected.id}/results`,
      );
      // Kết quả cũ vẫn là dữ liệu có giá trị nên chủ dự án được quyền sửa. Chỉ
      // cảnh báo vì hai lần chạy dùng hai bộ đề sẽ không còn so sánh trực tiếp.
      if (
        (prior.results || []).length > 0 &&
        !(await confirm(t("benchmark.confirm.results")))
      ) {
        return;
      }

      const updated = await apiClient.patch<Benchmark>(
        `/benchmarks/${selected.id}`,
        {
          name: draft.name.trim(),
          role_description: draft.role_description,
          models: draft.models,
          test_cases: cases,
        },
      );
      setSelected(updated);
      setEditing(false);
      await refreshBenchmarks();
      toast(t("benchmark.toast.saved"), "success");
    } catch (error) {
      toast(
        error instanceof Error ? error.message : t("benchmark.error.save"),
        "error",
      );
    }
  };
  const run = (id: number, models: string[]) => {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${location.host}/ws/benchmark`);
    socketRef.current = socket;
    setProgress(
      models.map((model) => ({ model, text: vi ? "Đang chờ…" : "Waiting…" })),
    );
    socket.onopen = () =>
      socket.send(JSON.stringify({ type: "run", benchmark_id: id }));
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as {
        type: string;
        model?: string;
        case_index?: number;
        total?: number;
        prompt?: string;
        scores?: Scores;
        results?: Result[];
        recommendation?: string;
        message?: string;
      };
      if (message.type === "progress" && message.model)
        setProgress((current) =>
          current.map((item) =>
            item.model === message.model
              ? {
                  ...item,
                  text: `${vi ? "Câu" : "Case"} ${(message.case_index || 0) + 1}/${message.total}: ${message.prompt}`,
                }
              : item,
          ),
        );
      if (message.type === "scored" && message.model)
        setProgress((current) =>
          current.map((item) =>
            item.model === message.model
              ? {
                  ...item,
                  done: true,
                  scores: message.scores,
                  text: `${message.scores?.total}/10`,
                }
              : item,
          ),
        );
      if (message.type === "complete") {
        setResults(message.results || []);
        void refreshBenchmarks();
        socket.close(1000);
      }
      if (message.type === "error")
        toast(message.message || "Benchmark error", "error");
    };
    socket.onclose = (event) => {
      if (event.code === 1008) window.location.assign("/login");
    };
  };
  const remove = async (benchmark: Benchmark) => {
    if (
      !(await confirm(vi ? "Xoá bài đánh giá này?" : "Delete this benchmark?"))
    )
      return;
    await apiClient.delete(`/benchmarks/${benchmark.id}`);
    if (selected?.id === benchmark.id) setSelected(null);
    await refreshBenchmarks();
  };
  return (
    <div className={c("splitView")} hidden={hidden}>
      <aside className={c("sideList")}>
        {benchmarks.map((benchmark) => (
          <Tooltip
            key={benchmark.id}
            label={tooltip("tooltip.benchmark.open", benchmark.name || "")}
          >
            <button
              className={selected?.id === benchmark.id ? c("sideSelected") : ""}
              onClick={() => void open(benchmark)}
            >
              <strong>{benchmark.name}</strong>
              <small>
                {benchmark.status} · {(benchmark.models || []).length} models
              </small>
            </button>
          </Tooltip>
        ))}
      </aside>
      <section className={c("detailPane")}>
        {creating || editing ? (
          <BenchmarkForm
            draft={draft}
            setDraft={setDraft}
            models={Array.from(new Set([
              ...modelPool
                .map((model) => model.model_id || model.name || "")
                .filter(Boolean),
              ...(editing ? draft.models : []),
            ]))}
            language={language}
            editing={editing}
            onSubmit={editing ? save : createAndRun}
            onCancel={editing ? () => setEditing(false) : undefined}
          />
        ) : selected ? (
          <>
            <header className={c("detailHeader")}>
              <div>
                <h2>{selected.name}</h2>
                <p>{selected.role_description}</p>
              </div>
              <div className={c("detailHeaderActions")}>
                <Tooltip
                  label={tooltip("tooltip.benchmark.edit", selected.name || "")}
                >
                  <button
                    className={c("buttonGhost")}
                    onClick={() => edit(selected)}
                  >
                    <Icon name="edit" />
                    {t("benchmark.action.edit")}
                  </button>
                </Tooltip>
                <Tooltip
                  label={tooltip("tooltip.benchmark.delete", selected.name || "")}
                >
                  <button
                    className={c("dangerLink")}
                    onClick={() => void remove(selected)}
                  >
                    <Icon name="trash" />
                    {vi ? "Xoá" : "Delete"}
                  </button>
                </Tooltip>
              </div>
            </header>
            {progress.length && !results.length ? (
              <div className={c("progressList")}>
                {progress.map((item) => (
                  <div key={item.model}>
                    <span
                      className={
                        item.done ? c("progressDone") : c("progressRunning")
                      }
                    />
                    <strong>{item.model}</strong>
                    <small>{item.text}</small>
                  </div>
                ))}
              </div>
            ) : null}
            {results.length ? (
              <Results results={results} vi={vi} />
            ) : selected.status !== "completed" && !progress.length ? (
              <div className={c("empty")}>
                <Icon name="clock" />
                {vi
                  ? "Bài đánh giá chưa hoàn tất"
                  : "Benchmark has not completed"}
              </div>
            ) : null}
          </>
        ) : (
          <div className={c("empty")}>
            <Icon name="flask" />
            {vi
              ? "Chọn hoặc tạo một bài đánh giá"
              : "Select or create a benchmark"}
          </div>
        )}
      </section>
    </div>
  );
}

function BenchmarkForm({
  draft,
  setDraft,
  models,
  language,
  editing,
  onSubmit,
  onCancel,
}: {
  draft: BenchmarkDraft;
  setDraft: (draft: BenchmarkDraft) => void;
  models: string[];
  language: Language;
  editing: boolean;
  onSubmit: () => Promise<void>;
  onCancel?: () => void;
}) {
  const vi = language === "vi";
  const tooltip = useTooltipText();
  return (
    <div className={c("formStack")}>
      <Field label={vi ? "Tên bài đánh giá" : "Benchmark name"}>
        <input
          className={c("input")}
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
        />
      </Field>
      <Field label={vi ? "Vai trò cần đánh giá" : "Role to evaluate"}>
        <textarea
          className={c("textarea")}
          value={draft.role_description}
          onChange={(event) =>
            setDraft({ ...draft, role_description: event.target.value })
          }
        />
      </Field>
      <Field label="Models">
        <div className={c("toolChecklist")}>
          {models.map((model) => (
            <label key={model}>
              <input
                type="checkbox"
                checked={draft.models.includes(model)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    models: event.target.checked
                      ? [...draft.models, model]
                      : draft.models.filter((item) => item !== model),
                  })
                }
              />
              <code>{model}</code>
            </label>
          ))}
        </div>
      </Field>
      <div className={c("testCases")}>
        <header>
          <strong>{hubText(language, "benchmark.form.test_cases")}</strong>
          <Tooltip label={tooltip("tooltip.benchmark.case_add")}>
            <button
              className={c("buttonGhost")}
              aria-label={tooltip("tooltip.benchmark.case_add")}
              onClick={() =>
                setDraft({
                  ...draft,
                  test_cases: [...draft.test_cases, { prompt: "", criteria: "" }],
                })
              }
            >
              +
            </button>
          </Tooltip>
        </header>
        {draft.test_cases.map((item, index) => (
          <div key={index} className={c("testCaseRow")}>
            <label className={c("testCaseField")}>
              <span>{hubText(language, "benchmark.form.prompt_label")}</span>
              <span
                className={c("testCaseTextareaSizer")}
                data-replicated-value={item.prompt}
              >
                <textarea
                  className={c("textarea")}
                  rows={4}
                  value={item.prompt}
                  placeholder={hubText(language, "benchmark.form.prompt_placeholder")}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      test_cases: draft.test_cases.map((current, currentIndex) =>
                        currentIndex === index
                          ? { ...current, prompt: event.target.value }
                          : current,
                      ),
                    })
                  }
                />
              </span>
            </label>
            <label className={c("testCaseField")}>
              <span>{hubText(language, "benchmark.form.criteria_label")}</span>
              <span
                className={c("testCaseTextareaSizer")}
                data-replicated-value={item.criteria}
              >
                <textarea
                  className={c("textarea")}
                  rows={4}
                  value={item.criteria}
                  placeholder={hubText(language, "benchmark.form.criteria_placeholder")}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      test_cases: draft.test_cases.map((current, currentIndex) =>
                        currentIndex === index
                          ? { ...current, criteria: event.target.value }
                          : current,
                      ),
                    })
                  }
                />
              </span>
            </label>
            <Tooltip label={tooltip("tooltip.benchmark.case_remove", index + 1)}>
              <button
                className={c("testCaseRemove")}
                aria-label={tooltip("tooltip.benchmark.case_remove", index + 1)}
                onClick={() =>
                  setDraft({
                    ...draft,
                    test_cases: draft.test_cases.filter(
                      (_, currentIndex) => currentIndex !== index,
                    ),
                  })
                }
              >
                ×
              </button>
            </Tooltip>
          </div>
        ))}
      </div>
      {editing ? (
        <div className={c("formActions")}>
          <div />
          <div>
            <Tooltip label={tooltip("tooltip.benchmark.cancel")}>
              <button className={c("buttonGhost")} onClick={onCancel}>
                {hubText(language, "common.cancel")}
              </button>
            </Tooltip>
            <Tooltip label={tooltip("tooltip.benchmark.save")}>
              <button
                data-testid="save-benchmark"
                className={c("primaryButton")}
                onClick={() => void onSubmit()}
              >
                <Icon name="save" />
                {hubText(language, "benchmark.action.save")}
              </button>
            </Tooltip>
          </div>
        </div>
      ) : (
        <Tooltip label={tooltip("tooltip.benchmark.run")}>
          <button
            data-testid="run-benchmark"
            className={c("primaryButton")}
            onClick={() => void onSubmit()}
          >
            <Icon name="play" />
            {vi ? "Tạo và chạy" : "Create and run"}
          </button>
        </Tooltip>
      )}
    </div>
  );
}
function Results({ results, vi }: { results: Result[]; vi: boolean }) {
  const sorted = [...results].sort((a, b) => b.scores.total - a.scores.total);
  return (
    <div className={c("results")}>
      <article>
        <Icon name="trophy" />
        <span>
          <small>{vi ? "Đề xuất" : "Recommended"}</small>
          <strong>{sorted[0]?.model || "—"}</strong>
        </span>
      </article>
      <table className={c("dataTable")}>
        <thead>
          <tr>
            <th>Model</th>
            <th>{vi ? "Chất lượng" : "Quality"}</th>
            <th>{vi ? "Tốc độ" : "Speed"}</th>
            <th>{vi ? "Tổng" : "Total"}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((result) => (
            <tr key={result.model}>
              <td>{result.model}</td>
              <td>{result.scores.quality}/10</td>
              <td>{result.scores.speed_score}/10</td>
              <td>
                <strong>{result.scores.total}/10</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className={c("field")}>
      <span>{label}</span>
      {children}
    </label>
  );
}
