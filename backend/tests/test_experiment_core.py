"""Chốt an toàn cho lõi thí nghiệm cơ chế tự cải thiện."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def prompt_data(tmp_path, monkeypatch):
    """Dựng đủ ba soul trong thư mục tạm, không đụng dữ liệu nghiên cứu thật."""
    from core import agent_soul, project_soul, skill_soul

    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path / "agents")
    monkeypatch.setattr(project_soul, "PROJECT_SOULS_DIR", tmp_path / "projects")
    monkeypatch.setattr(skill_soul, "SKILL_SOULS_DIR", tmp_path / "skills")

    agent = {
        "id": 17,
        "name": "Celexa",
        "role": "Content writer",
        "system_prompt": "SYSTEM GỐC",
        "skills_json": "[3, 8]",
    }
    agent_soul.ensure_soul_file(agent)
    agent_soul.append_lessons(17, "Celexa", "Buổi dạy", ["Xưng em với Sếp."])
    skill_soul.append_skill_lessons(3, "write_post", "Buổi dạy", ["Không dùng markdown."])
    project_soul.append_project_lessons(9, "Shop len", "Buổi dạy", ["Gọi khách là mấy bà."])

    skills = {
        3: {"id": 3, "name": "write_post", "config_json": json.dumps({"content": "CÔNG THỨC VIẾT"})},
        8: {"id": 8, "name": "research", "config_json": json.dumps({"content": "CÔNG THỨC NGHIÊN CỨU"})},
    }

    async def fake_get_skill(skill_id):
        return skills.get(skill_id)

    monkeypatch.setattr("hub.database.get_skill", fake_get_skill)
    return agent, skills


@pytest.mark.asyncio
async def test_prompt_day_du_khop_byte_voi_cach_ghep_cu(prompt_data):
    """Chốt quan trọng nhất: bật đủ tầng phải đúng byte-for-byte với code cũ."""
    from core.agent_prompt import compose_agent_system_prompt, load_agent_prompt_context
    from core.agent_soul import soul_for_prompt
    from core.project_soul import project_soul_for_prompt
    from core.skill_soul import skill_soul_for_prompt

    agent, skills = prompt_data
    photo_note = "GHI CHÚ ẢNH"
    output_rule = "LUẬT OUTPUT"
    multi_rule = "LUẬT NHIỀU KỸ NĂNG"

    # Bản sao độc lập của phép ghép trước khi tách khỏi websocket_workflow.py.
    skills_content = ""
    for skill_id in [3, 8]:
        skill = skills[skill_id]
        content = json.loads(skill["config_json"]).get("content", "")
        appendix = skill_soul_for_prompt(skill_id, skill["name"])
        if content or appendix:
            skills_content += "\n\n---\n" + "\n\n".join(filter(None, [content, appendix]))
    legacy = "\n\n".join(filter(None, [
        agent["system_prompt"],
        skills_content.strip(),
        soul_for_prompt(agent["id"]),
        project_soul_for_prompt(9),
        photo_note,
        output_rule,
        multi_rule,
    ]))

    context = await load_agent_prompt_context(agent, 9, sync_souls=False)
    current = compose_agent_system_prompt(
        context, trailing_parts=[photo_note, output_rule, multi_rule]
    )
    assert current == legacy


@pytest.mark.asyncio
async def test_bon_dieu_kien_cong_don_dung_tung_tang(prompt_data):
    from core.agent_prompt import PromptLayerFlags, compose_agent_system_prompt, load_agent_prompt_context

    agent, _ = prompt_data
    context = await load_agent_prompt_context(agent, 9, sync_souls=False)
    control = compose_agent_system_prompt(context, layers=PromptLayerFlags(False, False, False))
    employee = compose_agent_system_prompt(context, layers=PromptLayerFlags(True, False, False))
    skill = compose_agent_system_prompt(context, layers=PromptLayerFlags(True, True, False))
    full = compose_agent_system_prompt(context, layers=PromptLayerFlags(True, True, True))

    assert "CÔNG THỨC VIẾT" in control, "năng lực nền của kỹ năng không phải tầng bị loại"
    assert "Xưng em với Sếp" not in control
    assert "Xưng em với Sếp" in employee and "Không dùng markdown" not in employee
    assert "Không dùng markdown" in skill and "Gọi khách là mấy bà" not in skill
    assert "Gọi khách là mấy bà" in full


@pytest.mark.asyncio
async def test_che_do_thi_nghiem_chi_doc_khong_sync_soul(prompt_data, monkeypatch):
    from core import agent_soul, project_soul
    from core.agent_prompt import load_agent_prompt_context

    agent, _ = prompt_data
    before_agent = agent_soul.soul_path(17).read_bytes()
    before_project = project_soul.project_soul_path(9).read_bytes()

    async def forbidden_agent_sync(_agent):
        raise AssertionError("thí nghiệm không được gọi sync_agent_soul")

    async def forbidden_project_prompt(_project_id, mode="product"):
        raise AssertionError("thí nghiệm không được gọi project_prompt")

    monkeypatch.setattr(agent_soul, "sync_agent_soul", forbidden_agent_sync)
    monkeypatch.setattr(project_soul, "project_prompt", forbidden_project_prompt)
    await load_agent_prompt_context(agent, 9, sync_souls=False)

    assert agent_soul.soul_path(17).read_bytes() == before_agent
    assert project_soul.project_soul_path(9).read_bytes() == before_project


@pytest.mark.asyncio
async def test_usage_policy_experiment_khong_kiem_han_muc_khong_ghi_usage(monkeypatch):
    from core import model_pool_bridge as bridge

    entry = {
        "id": 4, "name": "model test", "enabled": 1,
        "api_style": "openai_compat", "base_url": "http://invalid",
        "api_key": "", "model_id": "test-model",
    }

    async def fake_entry(_model_pool_id):
        return entry

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("không được kiểm/ghi usage production")

    async def fake_stream(_base_url, _api_key, _model_id, _messages, usage_state, _tools):
        usage_state.update(tokens_in=12, tokens_out=3, tokens_cache=2)
        yield "xin chào"

    monkeypatch.setattr(bridge, "get_model_pool_entry", fake_entry)
    monkeypatch.setattr(bridge, "_check_daily_limits", forbidden)
    monkeypatch.setattr(bridge, "record_model_usage", forbidden)
    monkeypatch.setattr(bridge, "record_model_usage_hourly", forbidden)
    monkeypatch.setattr(bridge, "record_model_call_log", forbidden)
    monkeypatch.setattr(bridge, "_stream_openai", fake_stream)

    usage = {}
    chunks = [chunk async for chunk in bridge.stream_from_pool(
        4, [{"role": "user", "content": "x"}],
        usage_policy="experiment", usage_out=usage,
    )]
    assert chunks == ["xin chào"]
    assert usage == {"tokens_in": 12, "tokens_out": 3, "tokens_cache": 2}


def test_tong_hop_dung_do_lech_chuan_mau_va_dong_gop_tung_tang():
    from core.experiment_runner import calculate_experiment_summary

    trials = []
    scores = {
        "khong_soul": [4, 6],
        "soul_nhan_vien": [5, 7],
        "them_ky_nang": [7, 9],
        "day_du": [8, 10],
    }
    for condition, values in scores.items():
        trials.extend({"condition": condition, "score": value} for value in values)

    summary = calculate_experiment_summary(trials)
    control = summary["conditions"][0]
    assert control["condition"] == "khong_soul"
    assert control["mean"] == 5.0
    assert control["stddev"] == 1.4142
    assert control["n"] == control["total_n"] == 2
    assert control["clarify_n"] == control["conflict_n"] == 0
    assert control["delta_vs_control"] == 0.0
    assert summary["layer_contributions"] == {
        "soul_nhan_vien": 1.0,
        "phu_luc_ky_nang": 2.0,
        "soul_du_an": 1.0,
        "tong_day_du_vs_doi_chung": 4.0,
    }


def test_giam_khao_phan_loai_du_ba_dang_va_lui_an_toan_ve_answered(caplog):
    from core.experiment_runner import _valid_scores

    raw = json.dumps({"scores": [
        {"id": "a", "score": 8, "reason": "đã làm", "classification": "answered"},
        {"id": "b", "score": 1, "reason": "hỏi thêm", "classification": "clarify"},
        {"id": "c", "score": 0, "reason": "đá luật", "classification": "conflict"},
        {"id": "d", "score": 7, "reason": "schema cũ"},
        {"id": "e", "score": 6, "reason": "giá trị lạ", "classification": "other"},
        {"id": "f", "score": 5, "reason": "sai kiểu", "classification": ["answered"]},
    ]})

    parsed = _valid_scores(raw, {"a", "b", "c", "d", "e", "f"})

    assert parsed == {
        "a": (8.0, "đã làm", "answered"),
        "b": (1.0, "hỏi thêm", "clarify"),
        "c": (0.0, "đá luật", "conflict"),
        "d": (7.0, "schema cũ", "answered"),
        "e": (6.0, "giá trị lạ", "answered"),
        "f": (5.0, "sai kiểu", "answered"),
    }
    assert caplog.text.count("coi là answered") == 3


def test_tong_hop_tach_clarify_conflict_khoi_diem_va_bat_co_mau_nho():
    from core.experiment_runner import calculate_experiment_summary

    trials = [
        {"condition": "khong_soul", "score": 8, "response_classification": "answered"},
        {"condition": "khong_soul", "score": 10, "response_classification": "answered"},
        {"condition": "khong_soul", "score": 0, "response_classification": "conflict"},
        {"condition": "khong_soul", "score": 0.5, "response_classification": "clarify"},
    ]
    trials.extend(
        {"condition": "soul_nhan_vien", "score": 6, "response_classification": "answered"}
        for _ in range(10)
    )

    summary = calculate_experiment_summary(trials)
    control, employee = summary["conditions"][:2]
    assert control["mean"] == 9.0, "conflict/clarify không được kéo trung bình xuống"
    assert control["n"] == 2
    assert control["total_n"] == 4
    assert control["clarify_n"] == 1 and control["clarify_rate"] == 0.25
    assert control["conflict_n"] == 1 and control["conflict_rate"] == 0.25
    assert control["insufficient_answered"] is True
    assert employee["n"] == 10 and employee["insufficient_answered"] is False
    assert summary["warnings"] == [{
        "code": "insufficient_answered",
        "condition": "khong_soul",
        "answered_n": 2,
        "minimum_answered": 10,
    }]
    assert summary["score_population"] == "answered_only"


@pytest.mark.asyncio
async def test_db_cu_thieu_phan_loai_duoc_doc_nhu_answered(tmp_path, monkeypatch):
    """Migration phải giữ nguyên nghĩa số liệu cũ, không đoán lại từ response."""
    import sqlite3

    from hub import database

    db_path = tmp_path / "legacy-experiment.db"
    with sqlite3.connect(db_path) as db:
        db.execute(
            """CREATE TABLE experiment_trials (
                id INTEGER PRIMARY KEY, experiment_id INTEGER, condition TEXT,
                execution_order INTEGER, score REAL
            )"""
        )
        db.execute(
            "INSERT INTO experiment_trials VALUES (1, 9, 'khong_soul', 1, 7.5)"
        )
    monkeypatch.setattr(database, "DB_PATH", str(db_path))

    await database.init_db()
    trials = await database.list_experiment_trials(9)

    assert trials[0]["response_classification"] == "answered"


@pytest.mark.asyncio
async def test_runner_nen_luu_du_bon_dieu_kien_va_snapshot(tmp_path, monkeypatch):
    """Smoke end-to-end bằng model giả: schema → runner → điểm → snapshot."""
    import re

    from core import agent_soul, project_soul, skill_soul
    from core.experiment_runner import ExperimentRunnerManager
    from hub import database

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "experiment.db"))
    monkeypatch.setattr(agent_soul, "SOULS_DIR", tmp_path / "agent_souls")
    monkeypatch.setattr(project_soul, "PROJECT_SOULS_DIR", tmp_path / "project_souls")
    monkeypatch.setattr(skill_soul, "SKILL_SOULS_DIR", tmp_path / "skill_souls")
    await database.init_db()

    skill_id = await database.create_skill(
        "write_post", config_json=json.dumps({"content": "Nội dung kỹ năng nền"})
    )
    measured_id = await database.create_model_pool_entry(
        "Model đo", "test", model_id="measured-model"
    )
    judge_id = await database.create_model_pool_entry(
        "Model chấm", "test", model_id="judge-model"
    )
    agent_id = await database.create_agent_config(
        "Celexa", system_prompt="System gốc", skills_json=json.dumps([skill_id])
    )
    project_id = await database.create_project("Shop", "Mô tả dự án")
    benchmark_id = await database.create_benchmark(
        "Bộ đề", test_cases_json=json.dumps([
            {"prompt": "Viết một câu.", "criteria": "Đúng giọng."}
        ])
    )
    agent_soul.ensure_soul_file({"id": agent_id, "name": "Celexa", "role": "Writer"})
    agent_soul.append_lessons(agent_id, "Celexa", "Dạy", ["Xưng em."])
    skill_soul.append_skill_lessons(skill_id, "write_post", "Dạy", ["Không markdown."])
    project_soul.append_project_lessons(project_id, "Shop", "Dạy", ["Giọng vui."])
    before = agent_soul.soul_path(agent_id).read_bytes()

    experiment_id = await database.create_experiment(
        "Smoke", agent_id, project_id, benchmark_id, measured_id, judge_id,
        repetitions=1,
    )
    manager = ExperimentRunnerManager()
    measured_user_prompts = []

    async def fake_call(model_pool_id, messages):
        if model_pool_id == measured_id:
            measured_user_prompts.append(messages[-1]["content"])
            return "Câu trả lời nguyên văn", 0.01, {
                "tokens_in": 10, "tokens_cache": 0, "tokens_out": 4,
            }
        ids = re.findall(r"### Mã ([0-9a-f]+)", messages[-1]["content"])
        raw = json.dumps({"scores": [
            {
                "id": opaque_id, "score": 8, "reason": "Đạt tiêu chí",
                "classification": "answered",
            }
            for opaque_id in ids
        ]})
        return raw, 0.02, {"tokens_in": 20, "tokens_cache": 0, "tokens_out": 5}

    monkeypatch.setattr(manager, "_call_model", fake_call)
    await manager._run_inner(experiment_id)

    experiment = await database.get_experiment(experiment_id)
    trials = await database.list_experiment_trials(experiment_id)
    assert experiment["status"] == "completed"
    assert {trial["condition"] for trial in trials} == {
        "khong_soul", "soul_nhan_vien", "them_ky_nang", "day_du",
    }
    assert all(trial["response"] == "Câu trả lời nguyên văn" for trial in trials)
    assert all(trial["score"] == 8 for trial in trials)
    assert all(trial["response_classification"] == "answered" for trial in trials)
    assert all("không hỏi ngược" in prompt for prompt in measured_user_prompts)
    assert all("giả định hợp lý" in prompt for prompt in measured_user_prompts)
    assert agent_soul.soul_path(agent_id).read_bytes() == before
    snapshot = json.loads(experiment["soul_snapshot_json"])
    assert "Xưng em" in snapshot["agent"]
    assert "Không markdown" in snapshot["skills"][0]["content"]
    assert "Giọng vui" in snapshot["project"]
