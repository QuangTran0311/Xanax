import { useEffect, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { useHub } from "./HubContext";
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
  const tooltip = useTooltipText();
  const { modelPool, toast, confirm } = useHub();
  const [selected, setSelected] = useState<Benchmark | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState({
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
    setProgress([]);
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
    } else setResults([]);
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
        {creating ? (
          <BenchmarkForm
            draft={draft}
            setDraft={setDraft}
            models={modelPool
              .map((model) => model.model_id || model.name || "")
              .filter(Boolean)}
            vi={vi}
            onRun={createAndRun}
          />
        ) : selected ? (
          <>
            <header className={c("detailHeader")}>
              <div>
                <h2>{selected.name}</h2>
                <p>{selected.role_description}</p>
              </div>
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
  vi,
  onRun,
}: {
  draft: {
    name: string;
    role_description: string;
    models: string[];
    test_cases: TestCase[];
  };
  setDraft: (draft: {
    name: string;
    role_description: string;
    models: string[];
    test_cases: TestCase[];
  }) => void;
  models: string[];
  vi: boolean;
  onRun: () => Promise<void>;
}) {
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
          <strong>{vi ? "Câu hỏi thử nghiệm" : "Test cases"}</strong>
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
          <div key={index}>
            <textarea
              className={c("textarea")}
              value={item.prompt}
              placeholder={vi ? "Câu hỏi" : "Prompt"}
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
            <input
              className={c("input")}
              value={item.criteria}
              placeholder={vi ? "Tiêu chí kết quả tốt" : "Success criteria"}
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
            <Tooltip label={tooltip("tooltip.benchmark.case_remove", index + 1)}>
              <button
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
      <Tooltip label={tooltip("tooltip.benchmark.run")}>
        <button
          data-testid="run-benchmark"
          className={c("primaryButton")}
          onClick={() => void onRun()}
        >
          <Icon name="play" />
          {vi ? "Tạo và chạy" : "Create and run"}
        </button>
      </Tooltip>
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
