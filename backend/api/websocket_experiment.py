"""WebSocket tiến độ thời gian thực cho thí nghiệm tự cải thiện."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.experiment_runner import calculate_experiment_summary, experiment_runner
from hub.database import get_experiment, list_experiment_trials

logger = logging.getLogger("xanax.ws.experiment")
router = APIRouter()


@router.websocket("/ws/experiments/{experiment_id}")
async def experiment_ws(ws: WebSocket, experiment_id: int):
    await ws.accept()
    experiment = await get_experiment(experiment_id)
    if not experiment:
        await ws.send_json({"type": "error", "message": "Không tìm thấy thí nghiệm"})
        await ws.close(code=1008)
        return

    queue = experiment_runner.subscribe(experiment_id)
    try:
        trials = await list_experiment_trials(experiment_id)
        await ws.send_json({
            "type": "snapshot",
            "experiment_id": experiment_id,
            "status": experiment["status"],
            "total_trials": experiment.get("total_trials", 0),
            "completed_trials": experiment.get("completed_trials", 0),
            "scored_trials": experiment.get("scored_trials", 0),
            "summary": calculate_experiment_summary(trials),
        })

        while True:
            event_task = asyncio.create_task(queue.get())
            receive_task = asyncio.create_task(ws.receive_json())
            done, pending = await asyncio.wait(
                {event_task, receive_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if pending:
                # Chờ coroutine receive thật sự kết thúc trước vòng kế tiếp; nếu
                # chỉ gọi cancel rồi bỏ đó, Starlette có thể báo hai receive song song.
                await asyncio.gather(*pending, return_exceptions=True)

            if event_task in done:
                await ws.send_json(event_task.result())
            if receive_task in done:
                message = receive_task.result()
                command = message.get("type")
                if command == "run":
                    started = await experiment_runner.start(experiment_id)
                    await ws.send_json({
                        "type": "run_accepted" if started else "run_rejected",
                        "experiment_id": experiment_id,
                    })
                elif command == "cancel":
                    cancelled = await experiment_runner.cancel(experiment_id)
                    await ws.send_json({
                        "type": "cancel_accepted" if cancelled else "cancel_rejected",
                        "experiment_id": experiment_id,
                    })
                elif command == "ping":
                    await ws.send_json({"type": "pong"})
                else:
                    await ws.send_json({
                        "type": "error",
                        "message": "Lệnh hợp lệ: run, cancel hoặc ping",
                    })
    except WebSocketDisconnect:
        logger.info("Client ngắt WebSocket thí nghiệm %s; runner vẫn tiếp tục nền", experiment_id)
    except Exception:
        logger.exception("WebSocket thí nghiệm %s lỗi", experiment_id)
        try:
            await ws.send_json({"type": "error", "message": "Lỗi WebSocket thí nghiệm"})
        except Exception:
            pass
    finally:
        experiment_runner.unsubscribe(experiment_id, queue)
