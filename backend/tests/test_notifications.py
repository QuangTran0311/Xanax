import pytest

from core.notifications import (
    check_cli_auth_notifications,
    create_notification,
    reason_text,
    read_all_notifications,
    read_notification,
)
from hub.database import (
    create_model_pool_entry,
    get_unread_notification_count,
    list_notifications,
)


@pytest.mark.asyncio
async def test_notification_chong_trung_theo_source_dang_unread():
    first = await create_notification(
        kind="workflow_failed", severity="error", title="Lần đầu",
        source_type="workflow_run", source_id=42,
    )
    second = await create_notification(
        kind="workflow_failed", severity="error", title="Nội dung mới",
        payload={"run_id": 42}, source_type="workflow_run", source_id=42,
    )

    rows, total = await list_notifications()
    assert total == 1
    assert len(rows) == 1
    assert first["id"] == second["id"] == rows[0]["id"]
    assert rows[0]["title"] == "Nội dung mới"

    # Một cảnh báo đã đọc không còn là dòng chống trùng; sự cố tái diễn được báo mới.
    await read_notification(first["id"])
    third = await create_notification(
        kind="workflow_failed", severity="error", title="Tái diễn",
        source_type="workflow_run", source_id=42,
    )
    assert third["id"] != first["id"]
    assert await get_unread_notification_count() == 1


@pytest.mark.asyncio
async def test_dem_va_danh_dau_tat_ca_notification_da_doc():
    one = await create_notification(
        kind="one", severity="info", title="Một", source_type="test", source_id=1,
    )
    await create_notification(
        kind="two", severity="warning", title="Hai", source_type="test", source_id=2,
    )
    assert await get_unread_notification_count() == 2

    await read_notification(one["id"])
    assert await get_unread_notification_count() == 1
    assert await read_all_notifications() == 1
    assert await get_unread_notification_count() == 0


def test_reason_duoc_anh_xa_thanh_cau_song_ngu_cho_nguoi_doc():
    assert reason_text("no_matching_agent", "vi") == (
        "Không tìm thấy nhân viên AI phù hợp với công việc này."
    )
    assert reason_text("no_matching_agent", "en") == (
        "No suitable AI employee was found for this work item."
    )
    assert reason_text("custom_machine_reason", "vi") == "custom machine reason"


@pytest.mark.asyncio
async def test_loi_cli_duoc_lam_sach_truoc_khi_luu_notification(monkeypatch):
    credential_dir = r"C:\Users\Secret\.codex-profile"
    await create_model_pool_entry(
        name="Codex thuê bao", provider="openai", api_style="codex_cli",
        model_id="codex", cli_config_dir=credential_dir,
    )

    async def failed_probe(_entry):
        raise RuntimeError(f"failed at {credential_dir} access_token=super-secret")

    monkeypatch.setattr("core.cli_login.read_cli_auth_status", failed_probe)
    await check_cli_auth_notifications()

    rows, total = await list_notifications()
    assert total == 1
    stored = f"{rows[0]['body']} {rows[0]['payload_json']}"
    assert credential_dir not in stored
    assert "super-secret" not in stored
    assert "<credential directory>" in rows[0]["body"]
    assert "access_token=<redacted>" in rows[0]["body"]
