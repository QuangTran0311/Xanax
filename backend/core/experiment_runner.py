"""Runner nền cho thí nghiệm ablation ba tầng tri thức.

Mọi lượt sinh và chấm đều đi qua ``stream_from_pool`` với chính sách experiment:
cùng provider/CLI như production, nhưng không kiểm/ghi hạn mức thật.  Module này
không import bất kỳ hàm append/sync soul nào.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import secrets
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone

from core.agent_prompt import (
    AgentPromptContext,
    PromptLayerFlags,
    compose_agent_system_prompt,
    load_agent_prompt_context,
)
from core.model_pool_bridge import stream_from_pool
from core.notifications import notify_experiment_finished
from hub.database import (
    cancel_unfinished_experiment_trials,
    claim_experiment_run,
    create_experiment_judgement,
    create_experiment_trials,
    get_agent_config,
    get_benchmark,
    get_experiment,
    get_model_pool_entry,
    get_project,
    list_experiment_trials,
    refresh_experiment_progress,
    update_experiment,
    update_experiment_judgement,
    update_experiment_trial,
)

logger = logging.getLogger("xanax.experiment_runner")

# Thứ tự này là thứ tự trình bày trong báo cáo; thứ tự THỰC THI được xáo riêng.
CONDITIONS: dict[str, PromptLayerFlags] = {
    "khong_soul": PromptLayerFlags(False, False, False),
    "soul_nhan_vien": PromptLayerFlags(True, False, False),
    "them_ky_nang": PromptLayerFlags(True, True, False),
    "day_du": PromptLayerFlags(True, True, True),
}

RESPONSE_CLASSIFICATIONS = frozenset({"answered", "clarify", "conflict"})
MIN_ANSWERED_TRIALS = 10
# Bảng t Student hai phía 95% được ghi tường minh để người đọc có thể đối chiếu
# từng bậc tự do khi bảo vệ luận văn, đồng thời không kéo scipy vào chỉ cho 30 số cố định.
T_CRITICAL_TWO_SIDED_95 = (
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
)
TRIAL_RESPONSE_INSTRUCTION = (
    "Hãy trả lời bằng kiến thức và bối cảnh HIỆN CÓ, không hỏi ngược chỉ vì thiếu "
    "thông tin; nếu thiếu thông tin, hãy tự đưa ra giả định hợp lý và nói rõ giả định đó."
)


def _t_critical_two_sided_95(df: float) -> float:
    """Tra t hai phía 95%; bậc tự do hữu hạn luôn làm tròn xuống thận trọng."""
    floored_df = math.floor(df)
    if floored_df > len(T_CRITICAL_TWO_SIDED_95):
        return 1.96
    return T_CRITICAL_TWO_SIDED_95[max(1, floored_df) - 1]


JUDGE_SYSTEM = """Bạn là giám khảo độc lập, nghiêm khắc cho một nghiên cứu AI.
Chấm MỖI câu trả lời độc lập theo đúng đề bài và tiêu chí được cung cấp, thang 0-10.
Không xếp hạng tương đối giữa các câu. Không suy đoán nguồn gốc hay cách tạo câu trả lời.
Ngoài điểm, phân loại cách câu trả lời xử lý đề bài bằng đúng một trong ba giá trị:
- "answered": có trả lời đúng dạng đề yêu cầu, dù chất lượng cao hay thấp.
- "clarify": hỏi ngược để xin thêm thông tin thay vì làm bài.
- "conflict": báo đề bài mâu thuẫn với luật/tri thức đã được dạy và từ chối làm theo.
Chỉ trả JSON hợp lệ theo dạng:
{"scores":[{"id":"mã ẩn danh","score":7.5,"reason":"lý do ngắn gọn","classification":"answered"}]}"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _safe_model_snapshot(entry: dict) -> dict:
    """Không bao giờ đóng băng api_key hay thư mục tài khoản CLI vào kết quả."""
    return {
        "id": entry.get("id"),
        "name": entry.get("name", ""),
        "provider": entry.get("provider", ""),
        "api_style": entry.get("api_style", ""),
        "model_id": entry.get("model_id", ""),
    }


def _parse_json_object(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Giám khảo không trả JSON object")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Kết quả chấm không phải JSON object")
    return value


def _valid_scores(raw: str, allowed_ids: set[str]) -> dict[str, tuple[float, str, str]]:
    """Chỉ nhận điểm có id đúng và trong thang; tuyệt đối không tự điền điểm 5."""
    value = _parse_json_object(raw)
    rows = value.get("scores")
    if not isinstance(rows, list):
        raise ValueError("JSON chấm thiếu mảng scores")
    result: dict[str, tuple[float, str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        opaque_id = str(row.get("id", ""))
        score = row.get("score")
        if opaque_id not in allowed_ids or opaque_id in result:
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        score_value = float(score)
        if not 0 <= score_value <= 10:
            continue
        classification = row.get("classification")
        if not isinstance(classification, str) or classification not in RESPONSE_CLASSIFICATIONS:
            # Giữ tương thích kết quả chấm cũ, nhưng phải để lại dấu vết vì im lặng
            # nuốt schema sai sẽ làm số liệu hành vi trông đáng tin hơn thực tế.
            logger.warning(
                "Giám khảo trả classification thiếu hoặc lạ cho mã %s (%r); coi là answered",
                opaque_id,
                classification,
            )
            classification = "answered"
        result[opaque_id] = (
            score_value,
            str(row.get("reason", "")).strip(),
            classification,
        )
    return result


def calculate_experiment_summary(trials: list[dict]) -> dict:
    """Tổng hợp toàn bộ và từng đề bằng độ lệch chuẩn mẫu (n-1)."""
    def classification_of(trial: dict) -> str:
        classification = trial.get("response_classification", "answered")
        return (
            classification
            if isinstance(classification, str) and classification in RESPONSE_CLASSIFICATIONS
            else "answered"
        )

    def summarize(
        condition_trials: list[dict],
        condition: str,
        score_filter,
    ) -> tuple[dict, float | None, float | None]:
        scored = [trial for trial in condition_trials
                  if trial.get("condition") == condition and trial.get("score") is not None]
        population_scores = [float(trial["score"]) for trial in scored if score_filter(trial)]
        mean = statistics.fmean(population_scores) if population_scores else None
        stddev = (
            statistics.stdev(population_scores) if len(population_scores) >= 2
            else (0.0 if population_scores else None)
        )
        return ({
            "condition": condition,
            "mean": round(mean, 4) if mean is not None else None,
            "stddev": round(stddev, 4) if stddev is not None else None,
            "n": len(population_scores),
            "delta_vs_control": None,
            "delta_standard_error": None,
            "delta_confidence_margin_95": None,
            "delta_confidence_df": None,
            "delta_distinguishable": False,
            "cohens_d": None,
            "stats_reliable": False,
            "unreliable_reason": "",
        }, mean, stddev)

    def add_control_comparisons(
        summary_rows: list[dict],
        stats: dict[str, tuple[float | None, float | None, int]],
    ) -> None:
        control_mean, control_stddev, control_n = stats["khong_soul"]
        for row in summary_rows:
            mean, stddev, n = stats[row["condition"]]
            row["stats_reliable"] = (
                n >= MIN_ANSWERED_TRIALS and control_n >= MIN_ANSWERED_TRIALS
            )
            if n < MIN_ANSWERED_TRIALS:
                row["unreliable_reason"] = f"n={n} < ngưỡng {MIN_ANSWERED_TRIALS}"
            elif control_n < MIN_ANSWERED_TRIALS:
                row["unreliable_reason"] = f"n={control_n} < ngưỡng {MIN_ANSWERED_TRIALS}"
            if control_mean is None or mean is None:
                continue

            difference = mean - control_mean
            row["delta_vs_control"] = round(difference, 4)
            if row["condition"] == "khong_soul":
                row["delta_standard_error"] = 0.0
                row["delta_confidence_margin_95"] = 0.0
                if row["stats_reliable"]:
                    row["cohens_d"] = 0.0
                continue

            # Với n < 2, độ lệch chuẩn mẫu chưa được ước lượng. Giữ kết quả trung
            # tính thay vì biến một mẫu đơn lẻ có "độ lệch chuẩn 0" thành chắc chắn.
            if (
                n < 2
                or control_n < 2
                or stddev is None
                or control_stddev is None
            ):
                continue

            standard_error = math.sqrt(
                (stddev ** 2 / n) + (control_stddev ** 2 / control_n)
            )
            row["delta_standard_error"] = round(standard_error, 4)
            condition_variance = stddev ** 2 / n
            control_variance = control_stddev ** 2 / control_n
            df_denominator = (
                condition_variance ** 2 / (n - 1)
                + control_variance ** 2 / (control_n - 1)
            )
            # Khi cả hai độ lệch chuẩn bằng 0, mẫu số Welch bằng 0. Không gắn một
            # khoảng tin cậy giả tạo vào dữ liệu hoàn toàn không có ước lượng nhiễu.
            if df_denominator == 0:
                continue
            confidence_df = (
                (condition_variance + control_variance) ** 2 / df_denominator
            )
            confidence_margin = (
                _t_critical_two_sided_95(confidence_df) * standard_error
            )
            row["delta_confidence_df"] = round(confidence_df, 4)
            row["delta_confidence_margin_95"] = round(confidence_margin, 4)
            if not row["stats_reliable"]:
                continue
            row["delta_distinguishable"] = abs(difference) > confidence_margin

            pooled_sd = math.sqrt(
                (
                    (n - 1) * stddev ** 2
                    + (control_n - 1) * control_stddev ** 2
                )
                / (n + control_n - 2)
            )
            # Độ lệch chuẩn gộp bằng 0 không chứng minh hiệu ứng là vô hạn. Giữ None
            # để báo cáo trung tính, giống cách CI không bịa độ chắc chắn từ mẫu thiếu.
            if pooled_sd == 0:
                continue
            row["cohens_d"] = round(difference / pooled_sd, 4)

    def summarize_population(condition_trials: list[dict], score_filter):
        population_rows: list[dict] = []
        population_stats: dict[str, tuple[float | None, float | None, int]] = {}
        for condition in CONDITIONS:
            row, mean, stddev = summarize(condition_trials, condition, score_filter)
            population_stats[condition] = (mean, stddev, row["n"])
            population_rows.append(row)
        add_control_comparisons(population_rows, population_stats)
        return population_rows, population_stats

    def is_answered(trial: dict) -> bool:
        return classification_of(trial) == "answered"

    def is_scored(_trial: dict) -> bool:
        return True

    def add_behavior_counts(row: dict, condition_trials: list[dict]) -> None:
        scored = [trial for trial in condition_trials
                  if trial.get("condition") == row["condition"]
                  and trial.get("score") is not None]
        classifications = [classification_of(trial) for trial in scored]
        total_n = len(scored)
        clarify_n = classifications.count("clarify")
        conflict_n = classifications.count("conflict")
        row.update({
            "total_n": total_n,
            "clarify_n": clarify_n,
            "clarify_rate": round(clarify_n / total_n, 4) if total_n else 0.0,
            "conflict_n": conflict_n,
            "conflict_rate": round(conflict_n / total_n, 4) if total_n else 0.0,
            "insufficient_answered": 0 < total_n and row["n"] < MIN_ANSWERED_TRIALS,
        })

    def combined_population_rows(condition_trials: list[dict]):
        answered_rows, answered_stats = summarize_population(condition_trials, is_answered)
        all_scored_rows, _ = summarize_population(condition_trials, is_scored)
        for row, all_scored_row in zip(answered_rows, all_scored_rows):
            add_behavior_counts(row, condition_trials)
            row["all_scored"] = {
                key: value for key, value in all_scored_row.items() if key != "condition"
            }
        return answered_rows, answered_stats

    rows, stats = combined_population_rows(trials)

    def delta(after: str, before: str) -> float | None:
        a, b = stats[after][0], stats[before][0]
        return round(a - b, 4) if a is not None and b is not None else None

    case_summaries: list[dict] = []
    case_indices = sorted({int(t["case_index"]) for t in trials if t.get("case_index") is not None})
    for case_index in case_indices:
        case_trials = [t for t in trials if int(t.get("case_index", -1)) == case_index]
        condition_rows, _ = combined_population_rows(case_trials)
        case_summaries.append({
            "case_index": case_index,
            "prompt": case_trials[0].get("prompt", "") if case_trials else "",
            "conditions": condition_rows,
        })

    return {
        "conditions": rows,
        "cases": case_summaries,
        "warnings": [
            {
                "code": "insufficient_answered",
                "condition": row["condition"],
                "answered_n": row["n"],
                "minimum_answered": MIN_ANSWERED_TRIALS,
            }
            for row in rows if row["insufficient_answered"]
        ],
        "layer_contributions": {
            "soul_nhan_vien": delta("soul_nhan_vien", "khong_soul"),
            "phu_luc_ky_nang": delta("them_ky_nang", "soul_nhan_vien"),
            "soul_du_an": delta("day_du", "them_ky_nang"),
            "tong_day_du_vs_doi_chung": delta("day_du", "khong_soul"),
        },
        # Không gộp conflict thành điểm 0: làm vậy sẽ phạt đúng hành vi ta muốn
        # giữ — phát hiện lệnh mới đá luật cũ và hỏi lại thay vì âm thầm vi phạm.
        "score_population": "answered_only",
        "secondary_score_population": "all_scored",
        "minimum_answered": MIN_ANSWERED_TRIALS,
        "stddev_method": "sample_n_minus_1",
        "effect_size_method": "cohens_d_pooled",
        "delta_confidence_level": 0.95,
        "delta_confidence_method": "welch_t_two_sided_95",
    }


class ExperimentRunnerManager:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}
        self._subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)

    async def start(self, experiment_id: int) -> bool:
        current = self._tasks.get(experiment_id)
        if current and not current.done():
            return False
        experiment = await get_experiment(experiment_id)
        if not experiment or experiment.get("status") != "pending":
            return False
        task = asyncio.create_task(self._run(experiment_id), name=f"experiment-{experiment_id}")
        self._tasks[experiment_id] = task
        task.add_done_callback(lambda _task, eid=experiment_id: self._tasks.pop(eid, None))
        return True

    async def cancel(self, experiment_id: int) -> bool:
        experiment = await get_experiment(experiment_id)
        if not experiment or experiment.get("status") not in ("pending", "running"):
            return False
        task = self._tasks.get(experiment_id)
        if task and not task.done():
            task.cancel()
        else:
            await cancel_unfinished_experiment_trials(experiment_id)
            await update_experiment(
                experiment_id, status="cancelled", completed_at=_utc_now(),
                error_text="Đã huỷ theo yêu cầu người dùng",
            )
            await self.broadcast(experiment_id, {"type": "cancelled", "experiment_id": experiment_id})
        return True

    def subscribe(self, experiment_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers[experiment_id].add(queue)
        return queue

    def unsubscribe(self, experiment_id: int, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(experiment_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(experiment_id, None)

    async def broadcast(self, experiment_id: int, event: dict) -> None:
        for queue in list(self._subscribers.get(experiment_id, set())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Tiến độ luôn có thể dựng lại từ DB; bỏ event cũ tốt hơn chặn runner.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def _call_model(self, model_pool_id: int, messages: list[dict]) -> tuple[str, float, dict]:
        usage: dict = {}
        chunks: list[str] = []
        started = time.monotonic()
        async for chunk in stream_from_pool(
            model_pool_id,
            messages,
            usage_policy="experiment",
            usage_out=usage,
        ):
            chunks.append(chunk)
        return "".join(chunks).strip(), time.monotonic() - started, usage

    async def _run(self, experiment_id: int) -> None:
        try:
            await self._run_inner(experiment_id)
        except asyncio.CancelledError:
            await cancel_unfinished_experiment_trials(experiment_id)
            await refresh_experiment_progress(experiment_id)
            await update_experiment(
                experiment_id,
                status="cancelled",
                completed_at=_utc_now(),
                error_text="Đã huỷ theo yêu cầu người dùng",
            )
            await self.broadcast(experiment_id, {
                "type": "cancelled", "experiment_id": experiment_id,
            })
        except Exception as exc:
            logger.exception("Thí nghiệm %s thất bại", experiment_id)
            await update_experiment(
                experiment_id,
                status="failed",
                completed_at=_utc_now(),
                error_text=str(exc),
            )
            await self.broadcast(experiment_id, {
                "type": "error", "experiment_id": experiment_id, "message": str(exc),
            })
            try:
                experiment = await get_experiment(experiment_id)
                await notify_experiment_finished(
                    experiment_id,
                    str((experiment or {}).get("name") or f"Experiment #{experiment_id}"),
                    "failed",
                )
            except Exception:
                logger.exception("Không phát được notification cho thí nghiệm %s", experiment_id)

    async def _run_inner(self, experiment_id: int) -> None:
        experiment = await get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Không tìm thấy thí nghiệm")
        agent = await get_agent_config(experiment["agent_id"])
        project = await get_project(experiment["project_id"]) if experiment.get("project_id") else None
        benchmark = await get_benchmark(experiment["benchmark_id"])
        measured = await get_model_pool_entry(experiment["measured_model_pool_id"])
        judge = await get_model_pool_entry(experiment["judge_model_pool_id"])
        if not agent or not benchmark or not measured or not judge:
            raise ValueError("Cấu hình tham chiếu đã bị xoá trước khi chạy")
        if experiment.get("project_id") and not project:
            raise ValueError("Dự án đã bị xoá trước khi chạy")
        if not measured.get("enabled") or not judge.get("enabled"):
            raise ValueError("Model bị đo hoặc model giám khảo đang bị tắt")

        try:
            test_cases = json.loads(benchmark.get("test_cases_json") or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Bộ đề có JSON không hợp lệ") from exc
        test_cases = [case for case in test_cases
                      if isinstance(case, dict) and str(case.get("prompt", "")).strip()]
        if not test_cases:
            raise ValueError("Bộ đề không có câu hỏi hợp lệ")

        # Chế độ chỉ đọc là ranh giới an toàn quan trọng nhất của runner.
        context = await load_agent_prompt_context(
            agent, experiment.get("project_id"), sync_souls=False, project_mode="product"
        )
        warnings = json.loads(experiment.get("warnings_json") or "[]")
        same_judge_model = (
            (measured.get("model_id") or "").strip().casefold()
            == (judge.get("model_id") or "").strip().casefold()
        )
        if same_judge_model and not any(
            item.get("code") == "judge_same_as_measured" for item in warnings if isinstance(item, dict)
        ):
            warnings.append({
                "code": "judge_same_as_measured",
                "message": "Không có model giám khảo khác; model đang bị đo tự chấm chính nó.",
            })

        total = len(CONDITIONS) * len(test_cases) * int(experiment["repetitions"])
        trial_specs: list[dict] = []
        for condition in CONDITIONS:
            for case_index, case in enumerate(test_cases):
                for repetition in range(1, int(experiment["repetitions"]) + 1):
                    trial_specs.append({
                        "condition": condition,
                        "case_index": case_index,
                        "repetition": repetition,
                        "prompt": str(case.get("prompt", "")),
                        "criteria": str(case.get("criteria", "")),
                    })
        random.SystemRandom().shuffle(trial_specs)
        for index, item in enumerate(trial_specs, start=1):
            item["execution_order"] = index

        context_snapshot = context.to_snapshot()
        config_snapshot = {
            "agent": {
                "id": agent.get("id"), "name": agent.get("name", ""),
                "role": agent.get("role", ""), "system_prompt": agent.get("system_prompt", ""),
                "skills_json": agent.get("skills_json", "[]"),
            },
            "project": project or None,
            "benchmark": {
                "id": benchmark.get("id"), "name": benchmark.get("name", ""),
                "test_cases": test_cases,
            },
            "measured_model": _safe_model_snapshot(measured),
            "judge_model": _safe_model_snapshot(judge),
            "repetitions": int(experiment["repetitions"]),
            "conditions": {
                name: {
                    "agent_soul": flags.agent_soul,
                    "skill_souls": flags.skill_souls,
                    "project_soul": flags.project_soul,
                }
                for name, flags in CONDITIONS.items()
            },
            "trial_response_instruction": TRIAL_RESPONSE_INSTRUCTION,
            # Lưu luôn các mảnh prompt để tái lập byte-for-byte dù DB đổi sau này.
            "prompt_context": context_snapshot,
        }
        soul_snapshot = {
            "agent": context.agent_soul_raw,
            "skills": [
                {"id": skill.id, "name": skill.name, "content": skill.soul_raw}
                for skill in context.skills
            ],
            "project": context.project_soul_raw,
        }
        claimed = await claim_experiment_run(
            experiment_id,
            total_trials=total,
            config_snapshot_json=json.dumps(config_snapshot, ensure_ascii=False),
            soul_snapshot_json=json.dumps(soul_snapshot, ensure_ascii=False),
            warnings_json=json.dumps(warnings, ensure_ascii=False),
        )
        if not claimed:
            return
        await create_experiment_trials(experiment_id, trial_specs)
        await self.broadcast(experiment_id, {
            "type": "started", "experiment_id": experiment_id,
            "total_trials": total, "conditions": list(CONDITIONS),
        })

        # Dùng lại chính snapshot vừa lưu, không đọc soul thêm lần nào trong lúc chạy.
        frozen_context = AgentPromptContext.from_snapshot(context_snapshot)
        trials = await list_experiment_trials(experiment_id)
        for trial in trials:
            await update_experiment_trial(trial["id"], status="running", started_at=_utc_now())
            layers = CONDITIONS[trial["condition"]]
            system_prompt = compose_agent_system_prompt(frozen_context, layers=layers)
            messages: list[dict] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({
                "role": "user",
                "content": f"{trial['prompt']}\n\n{TRIAL_RESPONSE_INSTRUCTION}",
            })
            try:
                response, elapsed, usage = await self._call_model(measured["id"], messages)
                await update_experiment_trial(
                    trial["id"],
                    response=response,
                    status="generated",
                    elapsed_seconds=elapsed,
                    tokens_input=usage.get("tokens_in", 0),
                    tokens_cache=usage.get("tokens_cache", 0),
                    tokens_output=usage.get("tokens_out", 0),
                    completed_at=_utc_now(),
                )
                event_status = "generated"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Lượt thí nghiệm %s lỗi sinh câu trả lời: %s", trial["id"], exc)
                await update_experiment_trial(
                    trial["id"], status="generation_error", error_text=str(exc),
                    completed_at=_utc_now(),
                )
                event_status = "generation_error"
            progress = await refresh_experiment_progress(experiment_id)
            await self.broadcast(experiment_id, {
                "type": "generation_progress", "experiment_id": experiment_id,
                "trial_id": trial["id"], "execution_order": trial["execution_order"],
                "status": event_status, **progress,
            })

        # Chấm theo từng đề để mọi câu trong một batch dùng đúng cùng tiêu chí.
        generated = await list_experiment_trials(experiment_id)
        by_case: dict[int, list[dict]] = defaultdict(list)
        for trial in generated:
            if trial.get("status") == "generated":
                by_case[int(trial["case_index"])].append(trial)
        for case_index in sorted(by_case):
            await self._judge_batch(
                experiment_id, judge["id"], test_cases[case_index], by_case[case_index]
            )

        final_trials = await list_experiment_trials(experiment_id)
        progress = await refresh_experiment_progress(experiment_id)
        has_errors = any(t.get("status") in ("generation_error", "judge_error") for t in final_trials)
        status = "completed_with_errors" if has_errors else "completed"
        await update_experiment(experiment_id, status=status, completed_at=_utc_now())
        await self.broadcast(experiment_id, {
            "type": "complete", "experiment_id": experiment_id, "status": status,
            "summary": calculate_experiment_summary(final_trials), **progress,
        })
        try:
            await notify_experiment_finished(
                experiment_id,
                str(experiment.get("name") or f"Experiment #{experiment_id}"),
                status,
                judge_error_count=sum(
                    1 for trial in final_trials if trial.get("status") == "judge_error"
                ),
            )
        except Exception:
            logger.exception("Không phát được notification cho thí nghiệm %s", experiment_id)

    async def _judge_batch(
        self,
        experiment_id: int,
        judge_model_pool_id: int,
        case: dict,
        trials: list[dict],
    ) -> None:
        cancelled = False
        try:
            for trial in trials:
                await update_experiment_trial(trial["id"], status="judging")

            progress = await refresh_experiment_progress(experiment_id)
            await self.broadcast(experiment_id, {
                "type": "judging_progress", "experiment_id": experiment_id,
                "case_index": int(trials[0]["case_index"]),
                "remaining_in_case": len(trials), **progress,
            })

            await self._judge_case(
                experiment_id, judge_model_pool_id, case, trials
            )
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            current_trials = await list_experiment_trials(experiment_id)
            trial_ids = {int(trial["id"]) for trial in trials}
            stuck_trials = [
                trial for trial in current_trials
                if int(trial["id"]) in trial_ids and trial.get("status") == "judging"
            ]
            for trial in stuck_trials:
                if cancelled:
                    # Trả về generated để luồng huỷ chung đổi thành cancelled; nếu giữ
                    # judging, lượt sẽ bị kẹt vì giám khảo đã không còn xử lý nó nữa.
                    await update_experiment_trial(trial["id"], status="generated")
                else:
                    # Mọi nhánh lỗi phải rời judging, nếu không giao diện sẽ báo đang
                    # chấm mãi dù batch đã thoát khỏi giám khảo.
                    await update_experiment_trial(
                        trial["id"], status="judge_error",
                        error_text=trial.get("error_text") or "Batch chấm kết thúc bất thường",
                        completed_at=_utc_now(),
                    )

    async def _judge_case(
        self,
        experiment_id: int,
        judge_model_pool_id: int,
        case: dict,
        trials: list[dict],
    ) -> None:
        pending = list(trials)
        last_error = ""
        for _attempt in range(2):
            if not pending:
                break
            shuffled = list(pending)
            random.SystemRandom().shuffle(shuffled)
            opaque_to_trial: dict[str, dict] = {}
            for trial in shuffled:
                opaque_to_trial[secrets.token_hex(8)] = trial

            responses = "\n\n".join(
                f"### Mã {opaque_id}\n{trial.get('response', '')}"
                for opaque_id, trial in opaque_to_trial.items()
            )
            judge_prompt = (
                f"Đề bài:\n{case.get('prompt', '')}\n\n"
                f"Tiêu chí chấm:\n{case.get('criteria') or 'Đúng, đầy đủ, hữu ích và rõ ràng.'}\n\n"
                "Thang điểm: 0 đến 10. Hãy trả đúng một phần tử scores cho mỗi mã dưới đây.\n\n"
                f"Các câu trả lời (thứ tự đã xáo ngẫu nhiên):\n{responses}"
            )
            item_map = {opaque_id: trial["id"] for opaque_id, trial in opaque_to_trial.items()}
            judgement_id = await create_experiment_judgement(
                experiment_id, int(shuffled[0]["case_index"]), judge_model_pool_id,
                json.dumps(item_map), judge_prompt,
            )
            for order, trial in enumerate(shuffled, start=1):
                await update_experiment_trial(
                    trial["id"], judgement_id=judgement_id, judge_order=order
                )

            raw = ""
            elapsed = 0.0
            usage: dict = {}
            try:
                raw, elapsed, usage = await self._call_model(judge_model_pool_id, [
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": judge_prompt},
                ])
                parsed = _valid_scores(raw, set(opaque_to_trial))
                completed_ids: set[int] = set()
                for opaque_id, (score, reason, classification) in parsed.items():
                    trial = opaque_to_trial[opaque_id]
                    await update_experiment_trial(
                        trial["id"], score=score, score_reason=reason,
                        response_classification=classification,
                        status="scored", completed_at=_utc_now(),
                    )
                    completed_ids.add(trial["id"])
                pending = [trial for trial in pending if trial["id"] not in completed_ids]
                last_error = "Giám khảo trả thiếu hoặc sai định dạng một số mã" if pending else ""
                await update_experiment_judgement(
                    judgement_id, raw_response=raw,
                    status="partial" if pending else "completed",
                    error_text=last_error, elapsed_seconds=elapsed,
                    tokens_input=usage.get("tokens_in", 0),
                    tokens_cache=usage.get("tokens_cache", 0),
                    tokens_output=usage.get("tokens_out", 0),
                    completed_at=_utc_now(),
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = str(exc)
                await update_experiment_judgement(
                    judgement_id, raw_response=raw, status="error",
                    error_text=last_error, elapsed_seconds=elapsed,
                    tokens_input=usage.get("tokens_in", 0),
                    tokens_cache=usage.get("tokens_cache", 0),
                    tokens_output=usage.get("tokens_out", 0),
                    completed_at=_utc_now(),
                )

            progress = await refresh_experiment_progress(experiment_id)
            await self.broadcast(experiment_id, {
                "type": "judging_progress", "experiment_id": experiment_id,
                "case_index": int(shuffled[0]["case_index"]),
                "remaining_in_case": len(pending), **progress,
            })

        for trial in pending:
            await update_experiment_trial(
                trial["id"], status="judge_error",
                error_text=last_error or "Không nhận được điểm hợp lệ sau 2 lần chấm",
                completed_at=_utc_now(),
            )


experiment_runner = ExperimentRunnerManager()
