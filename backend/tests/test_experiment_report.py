"""Test effect size, workbook luận văn và route tải báo cáo thí nghiệm."""
from io import BytesIO
import json

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from core.experiment_report_xlsx import build_experiment_report_xlsx
from core.experiment_runner import calculate_experiment_summary
from hub.server import create_app


_TEST_USER = "_pytest_experiment_report"
_TEST_PASS = "pytest-only-do-not-reuse"


@pytest.fixture
async def client():
    """Đi qua auth thật để chắc file được phục vụ bởi đúng route FastAPI."""
    import aiosqlite
    from hub.database import DB_PATH, create_user, get_user_by_username, init_db

    await init_db()
    if not await get_user_by_username(_TEST_USER):
        await create_user(_TEST_USER, _TEST_PASS)

    app = create_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
            response = await value.post(
                "/api/auth/login", json={"username": _TEST_USER, "password": _TEST_PASS},
            )
            assert response.status_code == 200, response.text
            yield value
    finally:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM users WHERE username = ?", (_TEST_USER,))
            await db.commit()


def _report_trials() -> list[dict]:
    prompt = "Hãy phân tích tác động của tri thức lên chất lượng câu trả lời. " * 3
    scores = {
        "khong_soul": [4, 6],
        "soul_nhan_vien": [5, 7],
        # Cố ý không có mẫu để kiểm tra None không bị biến thành 0 hoặc ô trống.
        "them_ky_nang": [],
        "day_du": [8, 10],
    }
    return [
        {
            "condition": condition,
            "score": score,
            "case_index": 0,
            "prompt": prompt,
            "response_classification": "answered",
        }
        for condition, values in scores.items()
        for score in values
    ]


def _experiment() -> dict:
    return {
        "id": 42,
        "name": "Ablation luận văn",
        "status": "completed",
        "agent_name": "Nhân viên nghiên cứu",
        "project_name": "Luận văn",
        "benchmark_name": "Bộ đề chuẩn",
        "measured_model_name": "Model đo",
        "judge_model_name": "Model chấm",
        "repetitions": 2,
        "total_trials": 8,
        "scored_trials": 6,
        "started_at": "2026-08-18 08:00:00",
        "completed_at": "2026-08-18 08:12:34",
    }


def _config() -> dict:
    return {
        "agent": {"id": 1, "name": "Nhân viên nghiên cứu"},
        "project": {"id": 2, "name": "Luận văn"},
        "benchmark": {
            "id": 3,
            "name": "Bộ đề chuẩn",
            "test_cases": [{"prompt": "Đề thử"}],
        },
        "measured_model": {
            "name": "Model đo", "model_id": "measure-v1",
            "provider": "provider-a", "api_style": "openai_compat",
        },
        "judge_model": {
            "name": "Model chấm", "model_id": "judge-v1",
            "provider": "provider-b", "api_style": "anthropic_native",
        },
        "repetitions": 2,
    }


def test_cohens_d_bi_chan_o_ca_tong_hop_va_tung_de_khi_mau_nho():
    trials = []
    for condition, scores in {
        "khong_soul": [2, 4],
        "soul_nhan_vien": [4, 8],
    }.items():
        trials.extend({
            "condition": condition, "score": score, "case_index": 0, "prompt": "Đề 1",
        } for score in scores)

    summary = calculate_experiment_summary(trials)

    assert summary["conditions"][0]["cohens_d"] is None
    assert summary["conditions"][1]["cohens_d"] is None
    assert summary["conditions"][1]["stats_reliable"] is False
    assert summary["conditions"][1]["unreliable_reason"] == "n=2 < ngưỡng 10"
    assert summary["cases"][0]["conditions"][1]["cohens_d"] is None
    assert summary["effect_size_method"] == "cohens_d_pooled"
    assert summary["delta_confidence_method"] == "welch_t_two_sided_95"
    assert "delta_confidence_z" not in summary


def test_cohens_d_giu_none_khi_mau_nho_hoac_pooled_sd_bang_khong():
    small_sample = calculate_experiment_summary([
        {"condition": "khong_soul", "score": 5},
        {"condition": "soul_nhan_vien", "score": 9},
    ])
    zero_pooled_sd = calculate_experiment_summary([
        *({"condition": "khong_soul", "score": 5} for _ in range(10)),
        *({"condition": "soul_nhan_vien", "score": 7} for _ in range(10)),
    ])

    assert small_sample["conditions"][1]["cohens_d"] is None
    assert zero_pooled_sd["conditions"][1]["cohens_d"] is None


def test_workbook_mo_lai_duoc_du_sheet_bold_dung_mot_dong_va_none_la_gach_ngang():
    trials = _report_trials() + [{
        "condition": "khong_soul",
        "score": 0,
        "case_index": 0,
        "prompt": "Đề có lượt clarify",
        "response_classification": "clarify",
    }]
    summary = calculate_experiment_summary(trials)
    content = build_experiment_report_xlsx(_experiment(), summary, _config())

    assert isinstance(content, bytes) and content
    workbook = load_workbook(BytesIO(content))
    assert workbook.sheetnames == [
        "Moi truong",
        "Bang 1 - So sanh dieu kien",
        "Bang 2 - Dong gop tung tang",
        "Bang 3 - Hanh vi",
        "Bang 4 - Tung de",
        "Canh bao",
    ]

    comparison = workbook["Bang 1 - So sanh dieu kien"]
    # Dữ liệu ở dòng 4-7 theo CONDITIONS; day_du (dòng 7) có mean cao nhất.
    assert all(comparison.cell(7, column).font.bold for column in range(1, 9))
    assert all(
        not comparison.cell(row, column).font.bold
        for row in range(4, 7)
        for column in range(1, 9)
    )
    assert comparison["B6"].value == "—"
    assert comparison["C6"].value == "—"
    assert comparison["H6"].value == "—"
    assert comparison["G4"].value == "—", "đối chứng thiếu mẫu cũng không được kết luận Không"
    assert comparison["H4"].value == "—", "đối chứng thiếu mẫu không được gán d = 0"
    assert "n=2 < ngưỡng 10" in comparison["A9"].value
    assert comparison["A11"].value == (
        "BẢNG 1B - ĐỐI CHIẾU QUẦN THỂ ĐẦY ĐỦ (mọi lượt đã chấm)"
    )
    assert comparison["B14"].value == pytest.approx(3.3333)
    assert comparison["D14"].value == 3
    assert "không lọc classification" in comparison["A19"].value

    environment = workbook["Moi truong"]
    method_text = next(
        environment.cell(row, 2).value
        for row in range(1, environment.max_row + 1)
        if environment.cell(row, 1).value == "Phương pháp"
    )
    assert "t Welch hai phía" in method_text
    assert "z =" not in method_text


@pytest.mark.asyncio
async def test_route_report_xlsx_tra_dung_header_va_content_type(client, monkeypatch):
    from api.routes import experiments as experiment_routes

    experiment = _experiment()
    experiment["config_snapshot_json"] = json.dumps(_config(), ensure_ascii=False)

    async def fake_get_experiment(experiment_id: int):
        return experiment if experiment_id == 42 else None

    async def fake_list_trials(experiment_id: int):
        return _report_trials() if experiment_id == 42 else []

    monkeypatch.setattr(experiment_routes, "get_experiment", fake_get_experiment)
    monkeypatch.setattr(experiment_routes, "list_experiment_trials", fake_list_trials)

    response = await client.get("/api/experiments/42/report.xlsx")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="experiment_42_report.xlsx"'
    )
    load_workbook(BytesIO(response.content))
