import asyncio
import time

from api import websocket_workflow
from core import image_gen, model_pool_bridge, project_storage
from hub import database


def _run_image_step(
    monkeypatch,
    tmp_path,
    pools,
    model_pool_ids,
    *,
    failing_models=None,
    usage_by_pool=None,
    provider_usage=None,
):
    """pools: dict {id: entry} có trong Model Pool."""
    events = []
    updates = []
    generated = []
    sleep_delays = []
    usage_records = {"daily": [], "hourly": [], "call_log": []}
    failing_models = set(failing_models or [])
    usage_by_pool = usage_by_pool or {}
    provider_usage = provider_usage or {}

    async def fake_get_skill(skill_id):
        return {"name": "generate_post_image", "config_json": "{}"}

    async def fake_get_pool(entry_id):
        return pools.get(int(entry_id))

    async def fake_get_usage(entry_id):
        usage = {
            "request_count": 0,
            "tokens_input": 0,
            "tokens_cache": 0,
            "tokens_output": 0,
        }
        usage.update(usage_by_pool.get(int(entry_id), {}))
        return usage

    async def fake_update(output_id, **kwargs):
        updates.append((output_id, kwargs))

    async def fake_generate_image(**kwargs):
        generated.append(kwargs)
        if kwargs["model"] in failing_models:
            model_attempt = sum(
                item["model"] == kwargs["model"] for item in generated
            )
            raise image_gen.ImageGenError(
                f"{kwargs['model']} lỗi lần {model_attempt}"
            )
        kwargs["usage_state"].update(provider_usage)

    async def fake_get_run_dir(run_id):
        return tmp_path

    async def fake_sleep(delay):
        sleep_delays.append(delay)

    async def fake_record_daily(*args):
        usage_records["daily"].append(args)

    async def fake_record_hourly(*args):
        usage_records["hourly"].append(args)

    async def fake_record_call_log(*args):
        usage_records["call_log"].append(args)

    async def send(event):
        events.append(event)

    monkeypatch.setattr(websocket_workflow, "get_skill", fake_get_skill)
    monkeypatch.setattr(model_pool_bridge, "get_model_pool_entry", fake_get_pool)
    monkeypatch.setattr(model_pool_bridge, "get_model_usage_today", fake_get_usage)
    monkeypatch.setattr(websocket_workflow, "update_workflow_output", fake_update)
    monkeypatch.setattr(image_gen, "generate_image", fake_generate_image)
    monkeypatch.setattr(project_storage, "get_or_create_run_dir", fake_get_run_dir)
    monkeypatch.setattr(websocket_workflow.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(database, "record_model_usage", fake_record_daily)
    monkeypatch.setattr(database, "record_model_usage_hourly", fake_record_hourly)
    monkeypatch.setattr(database, "record_model_call_log", fake_record_call_log)

    started = time.monotonic()
    result = asyncio.run(websocket_workflow._maybe_generate_image(
        run_id=1,
        step_num=1,
        output_id=99,
        skill_ids=[7],
        full_output="Caption\n\nIMAGE PROMPT\nA product photo",
        model_pool_ids=list(model_pool_ids),
        send=send,
        agent_name="Lexapro",
    ))
    return (
        result,
        events,
        updates,
        generated,
        time.monotonic() - started,
        sleep_delays,
        usage_records,
    )


def _pool(pool_id, name="Model", enabled=1, **overrides):
    entry = {
        "id": pool_id, "enabled": enabled, "name": name,
        "model_id": f"m-{pool_id}", "base_url": "http://x", "api_key": "k",
    }
    entry.update(overrides)
    return entry


def test_uses_agent_first_model(monkeypatch, tmp_path):
    _, events, _, generated, _, _, usage_records = _run_image_step(
        monkeypatch, tmp_path, {9: _pool(9), 10: _pool(10)}, model_pool_ids=[9, 10])
    assert generated and generated[0]["model"] == "m-9"
    assert not any(e["type"] == "agent_error" for e in events)
    assert usage_records["daily"] == [(9, 0, 0, 0)]


def test_skips_deleted_or_disabled_model_of_agent(monkeypatch, tmp_path):
    pools = {10: _pool(10, enabled=0), 11: _pool(11)}
    result, _, _, generated, elapsed, _, _ = _run_image_step(
        monkeypatch, tmp_path, pools, model_pool_ids=[6, 10, 11])  # 6 đã bị xoá
    assert result is not None
    assert elapsed < 1
    assert generated and generated[0]["model"] == "m-11"


def test_no_usable_agent_model_fails_fast(monkeypatch, tmp_path):
    result, events, updates, _, elapsed, sleep_delays, _ = _run_image_step(
        monkeypatch, tmp_path, {}, model_pool_ids=[6])
    assert result is None
    assert elapsed < 1
    assert sleep_delays == []
    assert any(
        e["type"] == "agent_error" and "chưa được gán model" in e["content"]
        for e in events
    )
    assert updates[-1][1]["review_status"] == "failed"


def test_falls_back_to_second_model_after_image_error(monkeypatch, tmp_path):
    pools = {
        9: _pool(9, name="Model đầu"),
        10: _pool(10, name="Model sau"),
    }
    result, events, _, generated, _, sleep_delays, _ = _run_image_step(
        monkeypatch,
        tmp_path,
        pools,
        model_pool_ids=[9, 10],
        failing_models={"m-9"},
    )

    assert result is not None and "![Ảnh đã tạo]" in result
    assert [call["model"] for call in generated] == ["m-9", "m-10"]
    assert sleep_delays == []
    assert not any(event["type"] == "agent_error" for event in events)
    assert any(
        event["type"] == "agent_chunk"
        and "Model đầu" in event["content"]
        and "Model sau" in event["content"]
        for event in events
    )


def test_all_models_fail_twice_with_aggregated_error(monkeypatch, tmp_path):
    pools = {
        9: _pool(9, name="Model đầu"),
        10: _pool(10, name="Model sau"),
    }
    result, events, updates, generated, _, sleep_delays, _ = _run_image_step(
        monkeypatch,
        tmp_path,
        pools,
        model_pool_ids=[9, 10],
        failing_models={"m-9", "m-10"},
    )

    assert result is None
    assert [call["model"] for call in generated] == [
        "m-9", "m-10", "m-9", "m-10",
    ]
    assert sleep_delays == [5]
    error_event = next(event for event in events if event["type"] == "agent_error")
    assert "Model đầu" in error_event["content"]
    assert "Model sau" in error_event["content"]
    assert "m-9 lỗi lần 1" in error_event["content"]
    assert "m-9 lỗi lần 2" in error_event["content"]
    assert "m-10 lỗi lần 1" in error_event["content"]
    assert "m-10 lỗi lần 2" in error_event["content"]
    assert updates[-1][1]["status"] == "error"
    assert updates[-1][1]["review_status"] == "failed"


def test_skips_model_at_daily_request_limit(monkeypatch, tmp_path):
    pools = {
        9: _pool(9, name="Hết quota", max_requests_per_day=2),
        10: _pool(10, name="Còn quota"),
    }
    result, _, _, generated, _, _, _ = _run_image_step(
        monkeypatch,
        tmp_path,
        pools,
        model_pool_ids=[9, 10],
        usage_by_pool={9: {"request_count": 2}},
    )

    assert result is not None
    assert [call["model"] for call in generated] == ["m-10"]


def test_records_usage_for_successful_fallback_model(monkeypatch, tmp_path):
    pools = {
        9: _pool(9, name="Model lỗi"),
        10: _pool(10, name="Model thành công"),
    }
    result, _, _, _, _, _, usage_records = _run_image_step(
        monkeypatch,
        tmp_path,
        pools,
        model_pool_ids=[9, 10],
        failing_models={"m-9"},
        provider_usage={"tokens_in": 12, "tokens_out": 34, "tokens_cache": 5},
    )

    assert result is not None
    assert usage_records == {
        "daily": [(10, 12, 34, 5)],
        "hourly": [(10, 12, 34, 5)],
        "call_log": [(10, 12, 34, 5)],
    }
