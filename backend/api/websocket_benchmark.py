"""
Benchmark WebSocket — run test cases against multiple models and score them.

Client → Server:
  { "type": "run", "benchmark_id": N }

Server → Client:
  { "type": "started",   "benchmark_id": N, "total_models": N, "total_cases": N }
  { "type": "progress",  "model": "...", "case_index": N, "total": N }
  { "type": "response",  "model": "...", "case_index": N, "content": "..." }
  { "type": "scored",    "model": "...", "scores": {...} }
  { "type": "complete",  "results": [...], "recommendation": "..." }
  { "type": "error",     "message": "..." }
"""
from __future__ import annotations

import json
import logging
import time

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.hermes_bridge import hermes
from hub.database import (
    add_benchmark_result, get_benchmark, get_benchmark_results,
    connect, update_benchmark,
)

logger = logging.getLogger("xanax.ws.benchmark")
router = APIRouter()

JUDGE_SYSTEM = """You are a strict evaluator.
Given a question and criteria, rate the following response on a 0-10 scale.
Reply ONLY with a JSON object: {"score": <int 0-10>, "reason": "<one sentence>"}"""


async def _call_model(model: str, messages: list[dict]) -> tuple[str, float]:
    """Call a model and return (response_text, elapsed_seconds)."""
    payload = {"model": model, "messages": messages, "stream": False}
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{hermes.base_url}/chat/completions",
                headers=hermes._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return text, time.monotonic() - t0
    except Exception as e:
        return f"[Error: {e}]", time.monotonic() - t0


async def _judge_response(prompt: str, response: str, criteria: str) -> int:
    """Use LLM to score a response. Returns 0-10."""
    judge_prompt = (
        f"Question: {prompt}\n\n"
        f"Evaluation criteria: {criteria or 'General quality, accuracy, helpfulness'}\n\n"
        f"Response to evaluate:\n{response}"
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": judge_prompt},
    ]
    text, _ = await _call_model(hermes.model, messages)
    try:
        data = json.loads(text)
        return max(0, min(10, int(data.get("score", 5))))
    except Exception:
        return 5


@router.websocket("/ws/benchmark")
async def benchmark_ws(ws: WebSocket):
    await ws.accept()

    try:
        data = await ws.receive_json()
        if data.get("type") != "run":
            await ws.send_json({"type": "error", "message": "Expected {type: 'run', benchmark_id: N}"})
            return

        benchmark_id = data.get("benchmark_id")
        benchmark = await get_benchmark(benchmark_id)
        if not benchmark:
            await ws.send_json({"type": "error", "message": "Benchmark not found"})
            return

        test_cases = json.loads(benchmark["test_cases_json"])
        models = json.loads(benchmark["models_json"])
        role_desc = benchmark["role_description"]

        if not models:
            await ws.send_json({"type": "error", "message": "No models configured"})
            return
        if not test_cases:
            await ws.send_json({"type": "error", "message": "No test cases configured"})
            return

        await update_benchmark(benchmark_id, status="running")
        await ws.send_json({
            "type": "started",
            "benchmark_id": benchmark_id,
            "total_models": len(models),
            "total_cases": len(test_cases),
        })

        system_msg = (
            f"You are an AI assistant playing the role of: {role_desc}\n"
            "Answer the following question thoroughly and accurately."
            if role_desc else
            "You are a helpful AI assistant. Answer the following question thoroughly and accurately."
        )

        all_results = []

        for model in models:
            model_responses = []
            total_quality = 0
            total_speed = 0.0

            for i, case in enumerate(test_cases):
                await ws.send_json({
                    "type": "progress",
                    "model": model,
                    "case_index": i,
                    "total": len(test_cases),
                    "prompt": case["prompt"][:80],
                })

                messages = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": case["prompt"]},
                ]
                response_text, elapsed = await _call_model(model, messages)
                total_speed += elapsed

                await ws.send_json({
                    "type": "response",
                    "model": model,
                    "case_index": i,
                    "content": response_text[:500],
                    "elapsed": round(elapsed, 2),
                })

                quality_score = await _judge_response(
                    case["prompt"], response_text, case.get("criteria", "")
                )
                total_quality += quality_score

                model_responses.append({
                    "prompt": case["prompt"],
                    "response": response_text,
                    "quality": quality_score,
                    "elapsed": round(elapsed, 2),
                })

            avg_quality = round(total_quality / len(test_cases), 1)
            avg_speed = round(total_speed / len(test_cases), 2)
            speed_score = max(0, min(10, round(10 - avg_speed, 1)))
            total_score = round((avg_quality * 0.7 + speed_score * 0.3), 1)

            scores = {
                "quality": avg_quality,
                "speed_score": speed_score,
                "avg_response_time": avg_speed,
                "total": total_score,
            }

            await ws.send_json({
                "type": "scored",
                "model": model,
                "scores": scores,
            })

            await add_benchmark_result(
                benchmark_id=benchmark_id,
                model=model,
                scores_json=json.dumps(scores),
                responses_json=json.dumps(model_responses),
                recommendation="",
            )
            all_results.append({"model": model, "scores": scores})

        # Determine best model
        best = max(all_results, key=lambda r: r["scores"]["total"])
        recommendation = best["model"]

        # Update recommendation text in DB for best model
        results_db = await get_benchmark_results(benchmark_id)
        for r in results_db:
            scores = json.loads(r["scores_json"])
            if scores.get("total") == best["scores"]["total"]:
                async with connect() as db:
                    await db.execute(
                        "UPDATE benchmark_results SET recommendation = ? WHERE id = ?",
                        ("Recommended for this role", r["id"]),
                    )
                    await db.commit()
                break

        from datetime import datetime, timezone
        await update_benchmark(
            benchmark_id,
            status="completed",
            completed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )

        await ws.send_json({
            "type": "complete",
            "results": all_results,
            "recommendation": recommendation,
        })

    except WebSocketDisconnect:
        logger.info("Benchmark WS client disconnected")
    except Exception:
        logger.exception("Benchmark WS error")
        try:
            await ws.send_json({"type": "error", "message": "Internal error during benchmark"})
        except Exception:
            pass
