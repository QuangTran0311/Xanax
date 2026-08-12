"""
Training WebSocket — streams Xanax responses.
Summarise chỉ xảy ra khi Papa bấm Pass hoặc Fail (không tự động sau mỗi tin nhắn).

Protocol:
  Client → Server:
    { "training_session_id": 1, "message": "..." }          -- chat message
    { "action": "summarise_pass", "session_id": 1 }         -- pass → đúc kết → SOUL.md
    { "action": "summarise_fail", "session_id": 1 }         -- fail → phân tích thất bại

  Server → Client:
    { "type": "status",           "status": "thinking" }
    { "type": "chunk",            "content": "..." }
    { "type": "done" }
    { "type": "notes_updated",    "content": "<summary>" }  -- pass: SOUL.md cập nhật
    { "type": "failure_analysed", "content": "<analysis>" } -- fail: phân tích thất bại
    { "type": "error",            "message": "..." }
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from core.hermes_bridge import hermes
from hub.database import (
    add_training_message,
    get_training_messages,
    get_training_session,
    update_training_session,
    get_agent_config,
    get_skill,
    list_agent_configs,
    list_skills,
    list_projects,
    list_work_items,
    list_workflow_tasks,
    list_model_pool,
    create_xanax_note,
    list_xanax_notes,
    delete_xanax_note,
    create_work_item,
    update_work_item,
)

logger = logging.getLogger("xanax.ws.training")
router = APIRouter()


# ── Buổi dạy có học viên ──────────────────────────────────────────────────────

async def _student_tools(agent: dict, allowed: list[str]) -> list[dict]:
    """Schema công cụ cho học viên: giao của (kỹ năng nhân viên) ∩ (Papa đã tick).

    Cấp theo BUỔI DẠY chứ không theo nhân viên, và mặc định rỗng. Một buổi dạy về
    cắt ảnh không có lý do gì được cầm luôn công cụ đăng bài của cùng nhân viên đó
    — mà nhân viên đăng bài thì chỉ cần một câu dạy thử là bài lên fanpage thật.

    Phép giao là hàng rào thứ hai: Papa gỡ một kỹ năng khỏi nhân viên thì công cụ
    đã tick từ buổi trước cũng hết hiệu lực, không cần đi dọn.
    """
    if not allowed:
        return []
    from api.websocket_meeting import _build_agent_tools
    return [
        schema for schema in await _build_agent_tools(agent)
        if schema["function"]["name"] in set(allowed)
    ]


async def _student_skill_scope(agent: dict, granted: set[str]) -> tuple[list[int], dict]:
    """Thu hẹp kỹ năng của nhân viên còn đúng phần chứa công cụ đã được cấp.

    Cần riêng cho ĐƯỜNG CLI. Model CLI không nhận `tools[]` theo JSON Schema; kỹ
    năng đi xuống qua cầu nối MCP dựng từ `skill_ids` (xem core/cli_provider.
    build_mcp_config). Truyền nguyên skill_ids của nhân viên vào đó thì buổi dạy
    chỉ tick `cut_product` vẫn phơi ra cả `facebook_post_page` — tức là một câu
    dạy thử đăng được bài thật lên fanpage.

    Trả về (skill_ids đã lọc, tool_filter cho skill MCP).
    """
    from core.hermes.tool_registry import tool_registry
    from core.mcp_client import tool_prefix_for_skill
    from core.skill_tools import tool_name_for_skill

    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        return [], {}

    kept: list[int] = []
    tool_filter: dict[int, list[str]] = {}
    for sid in skill_ids:
        skill = await get_skill(sid)
        if not skill:
            continue
        kind = skill.get("type")
        if kind == "mcp":
            prefix = tool_prefix_for_skill(skill)
            picked = [t.name[len(prefix):] for t in tool_registry.list_tools(tag="mcp")
                      if t.name.startswith(prefix) and t.name in granted]
            if picked:
                kept.append(sid)
                tool_filter[sid] = picked
        else:
            # api/builtin: một skill đúng một tool, nên có mặt trong `granted`
            # là đủ, không cần lọc thêm bên trong.
            if kind == "api":
                name = tool_name_for_skill(skill)
            else:
                name = (json.loads(skill.get("config_json") or "{}") or {}).get("tool_name")
            if name and name in granted:
                kept.append(sid)
    return kept, tool_filter


async def _stream_student(ws: WebSocket, agent: dict, history: list[dict],
                          project_id: int | None = None, session_id: int = 0,
                          allowed_tools: list[str] | None = None) -> str:
    """Chính nhân viên học viên trả lời, bằng model và soul của nó.

    Tách khỏi `_stream_agent` của phòng họp dù cùng ý tưởng, vì luật hai nơi
    khác nhau: ở đây không có nhân viên khác để lẫn vai, không có định dạng
    "[Tên]: " cần gỡ, và quan trọng nhất là học viên KHÔNG được cầm công cụ.

    Không truyền `tools` và không phân tích [[XANAX:...]] cho học viên. Bộ công
    cụ trong file này (save_note, create_work_item, trigger_workflow...) là
    quyền của Xanax; đưa cho một học viên đang được dạy nghĩa là một câu dạy
    thử có thể tạo việc thật hoặc chạy quy trình thật.
    """
    from core.agent_soul import soul_for_prompt, sync_agent_soul

    persona = (agent.get("system_prompt") or "").strip() or (
        f"Bạn là {agent.get('name')}, {agent.get('role') or 'nhân viên AI'}."
    )
    from core.project_soul import project_prompt

    await sync_agent_soul(agent)
    soul_content = soul_for_prompt(agent["id"])
    # Buổi dạy gắn dự án thì học viên phải đọc được giọng thương hiệu của dự án
    # NGAY TRONG LÚC HỌC. Không có nó, Papa sửa một câu chữ mà học viên không biết
    # dự án đang bán gì cho ai, trả lời chung chung, và bản đúc kết cuối buổi cũng
    # chung chung theo.
    project_content = await project_prompt(project_id, mode="conversation")

    # Nội dung kỹ năng — CÙNG hàm với phòng họp, để một kỹ năng có tác dụng như
    # nhau ở mọi nơi. Thiếu nó thì buổi dạy về `generate_post_image` diễn ra mà
    # học viên chưa từng đọc mô tả kỹ năng đó, và mọi câu nó nói về "cách con vẫn
    # làm" đều là bịa.
    from api.websocket_meeting import _build_skills_content
    skills_content = await _build_skills_content(agent)

    # Có kỹ năng tạo ảnh thì máy tự chốt chế độ A hay B theo việc Papa có gửi ảnh
    # hay không, rồi nói thẳng cho học viên. Để học viên tự suy từ mô tả kỹ năng
    # thì nó suy sai — và người dùng phổ thông không có cách nào biết mà sửa.
    photo_note = ""
    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        skill_ids = []
    skill_names = {(await get_skill(sid) or {}).get("name") for sid in skill_ids}
    if "generate_post_image" in skill_names:
        from core.image_gen import latest_attached_images, photo_mode_note
        photo_note = photo_mode_note(latest_attached_images(history))

    # Công cụ Papa cấp riêng cho buổi này (mặc định rỗng — xem _student_tools).
    student_tools = await _student_tools(agent, allowed_tools or [])
    if student_tools:
        names = ", ".join(t["function"]["name"] for t in student_tools)
        tools_note = (
            "CÔNG CỤ TRONG BUỔI HỌC NÀY: Papa đã cấp cho bạn " + names + ". Đây là "
            "công cụ THẬT, chạy thật — dùng khi Papa bảo làm thử, và nói rõ bạn vừa "
            "gọi cái gì. Ngoài danh sách này bạn không có công cụ nào khác; đừng nói "
            "là mình làm được việc mà bạn không có công cụ để làm."
        )
    else:
        tools_note = (
            "Trong buổi học này bạn KHÔNG có công cụ nào và không thực hiện việc "
            "thật. Papa hỏi gì thì trả lời, đừng nhận là mình vừa chạy cái gì."
        )

    system_prompt = "\n\n".join(filter(None, [
        persona,
        skills_content,
        soul_content,
        project_content,
        f"BỐI CẢNH: bạn LÀ {agent.get('name')} ({agent.get('role') or 'nhân viên AI'}), "
        "đang trong một buổi học riêng. Người nói chuyện với bạn là Papa — người "
        "trực tiếp dạy bạn. Hãy trả lời với tư cách chính bạn, ngôi thứ nhất.\n"
        "- Papa dạy điều gì thì nói lại BẰNG LỜI CỦA BẠN để Papa biết bạn hiểu đúng "
        "hay chưa; hiểu sai còn sửa được, gật đầu cho qua thì sai sẽ đi vào soul.\n"
        "- Chỗ nào chưa rõ thì HỎI LẠI, đừng đoán. Đây là lúc để hỏi.\n"
        "- KHÔNG bịa là mình đã làm hay đã chạy bất cứ thứ gì.\n"
        "- NGOẠI LỆ: nếu bạn có kỹ năng tạo ảnh, Papa bảo làm thử thì cứ viết khối "
        "IMAGE PROMPT đúng khuôn của kỹ năng — ảnh sẽ được vẽ thật ngay trong buổi "
        "học để Papa xem. Đây là làm thử, không phải bài đăng thật.\n"
        "- Khi đã có ảnh sản phẩm THẬT đã tách nền (Papa gửi kèm, hoặc bạn vừa cắt "
        "bằng công cụ), hãy thêm khối này ngay sau TỶ LỆ:\n"
        "  ẢNH SẢN PHẨM\n"
        "  <đường dẫn tuyệt đối tới file .png đã tách nền>\n"
        "  Lúc đó IMAGE PROMPT chỉ mô tả CÁI NỀN — đừng tả món hàng nữa, vì sản "
        "phẩm sẽ được dán vào giữa nền bằng chính ảnh chụp thật. Tả nền, ánh sáng, "
        "chất liệu mặt phẳng, chỗ trống để đặt chữ. Chừa khoảng giữa cho sản phẩm.\n"
        "- Muốn tự chỉnh cỡ và chỗ đặt món hàng thì thêm khối này sau ẢNH SẢN PHẨM:\n"
        "  VỊ TRÍ SẢN PHẨM\n"
        "  cao: 0.78\n"
        "  xuống: 0.02\n"
        "  `cao` là chiều cao món hàng so với chiều cao ảnh, `xuống` là đẩy xuống "
        "dưới tâm. Không khai báo thì dùng mặc định 0.68 / 0.04. Đổi số thì vùng "
        "phải chừa trống cũng đổi theo — xem công thức trong kỹ năng tạo ảnh.",
        photo_note,
        tools_note,
    ]))

    await _send(ws, {"type": "status", "status": "thinking"})

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    try:
        model_pool_ids: list[int] = json.loads(agent.get("model_pool_ids_json") or "[]")
    except Exception:
        model_pool_ids = []

    full = ""
    if model_pool_ids:
        # Dùng đúng danh sách model ưu tiên đã cấu hình cho nhân viên, tự fallback
        # khi model đầu hỏng — giống phòng họp và quy trình.
        from core.model_pool_bridge import stream_from_agent_models
        # Đường CLI nhận công cụ qua skill_ids chứ không qua tools[], nên phải thu
        # hẹp skill_ids lại cho khớp đúng phần Papa đã tick — xem _student_skill_scope.
        # Chưa tick gì thì cả hai đều rỗng: học viên không cầm công cụ nào.
        cli_skill_ids, cli_tool_filter = (
            await _student_skill_scope(agent, {s["function"]["name"] for s in student_tools})
            if student_tools else ([], {})
        )
        async for delta in stream_from_agent_models(
            model_pool_ids, llm_messages,
            tools=student_tools or None,
            skill_ids=cli_skill_ids or None,
            tool_filter=cli_tool_filter or None,
        ):
            if ws.client_state != WebSocketState.CONNECTED:
                break
            full += delta
            await _send(ws, {"type": "chunk", "content": delta})
    else:
        async for delta in hermes.stream_with_context(llm_messages):
            if ws.client_state != WebSocketState.CONNECTED:
                break
            full += delta
            await _send(ws, {"type": "chunk", "content": delta})

    full = await _maybe_draw_in_class(ws, agent, session_id, full, model_pool_ids)
    full = await _inline_local_images(ws, session_id, full)
    return full


# Thư mục ảnh vẽ thử trong phòng dạy. Tách hẳn khỏi archive của quy trình: ảnh ở
# đây là bài tập, không phải sản phẩm giao đi, và không được lẫn vào hồ sơ lần chạy.
TRAINING_IMAGE_DIR = Path(__file__).parent.parent / "data" / "training-images"

# Chỉ ảnh nằm TRONG thư mục data/ của dự án mới được hiện ra. Học viên tự viết ra
# đường dẫn trong câu trả lời, nên nếu không chặn thì một câu "ảnh ở
# C:\Users\Quang\Documents\gi-do.png" là đủ để lôi file bất kỳ trên máy vào khung
# chat. Ràng buộc theo thư mục, không theo phần mở rộng.
_DATA_ROOT = Path(__file__).parent.parent / "data"
_LOCAL_IMAGE_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|/)[^\s\"'`<>|*?]+?\.(?:png|jpe?g|webp|gif)", re.IGNORECASE)
_MAX_INLINE_IMAGES = 3


async def _inline_local_images(ws, session_id: int, full: str) -> str:
    """Ảnh do CÔNG CỤ tạo ra thì hiện thẳng trong chat, không bắt Papa đọc đường dẫn.

    `cut_product` trả về một dòng chữ kèm đường dẫn file, nên học viên chỉ chép
    lại đường dẫn đó. Ở đây bắt lấy, chép vào thư mục ảnh của buổi học rồi chèn
    markdown ảnh — dùng lại đúng endpoint đã có cho ảnh vẽ thử.

    Chép chứ không phục vụ thẳng từ đường dẫn gốc: có một endpoint nhận đường dẫn
    tuỳ ý là mở cửa cho mọi file trên máy. Chép trước rồi phục vụ từ thư mục buổi
    học thì phần kiểm tra đã nằm sẵn ở endpoint cũ.
    """
    if not full:
        return full

    added: list[str] = []
    seen: set[str] = set()
    for raw in _LOCAL_IMAGE_RE.findall(full):
        if len(added) >= _MAX_INLINE_IMAGES:
            break
        try:
            src = Path(raw.strip())
            key = str(src).lower()
            if key in seen:
                continue
            seen.add(key)
            if not src.is_file():
                continue
            src_res, root = src.resolve(), _DATA_ROOT.resolve()
            if root != src_res and root not in src_res.parents:
                logger.info("Bỏ qua ảnh ngoài thư mục data: %s", src_res)
                continue
            dest_dir = TRAINING_IMAGE_DIR / str(session_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{datetime.now().strftime('%H%M%S')}_{src_res.name}"
            if src_res == dest.resolve():
                continue                      # đã nằm sẵn trong thư mục buổi học
            await asyncio.get_running_loop().run_in_executor(
                None, shutil.copyfile, str(src_res), str(dest))
            added.append(f"![{src_res.name}](/api/training/sessions/{session_id}/image/{dest.name})")
        except Exception:
            logger.exception("Không chèn được ảnh %s vào buổi học %s", raw, session_id)

    if not added:
        return full
    block = "\n\n" + "\n".join(added)
    await _send(ws, {"type": "chunk", "content": block})
    return full + block


async def _maybe_draw_in_class(ws, agent: dict, session_id: int, full: str,
                               model_pool_ids: list[int]) -> str:
    """Học viên có kỹ năng tạo ảnh và vừa viết ra IMAGE PROMPT thì vẽ luôn.

    Đây là điều biến phòng dạy từ chỗ nói chuyện suông thành chỗ thử được người và
    thử được kỹ năng: Papa nhìn thấy ảnh thật do chính học viên nghĩ ra, chê ngay
    tại chỗ, sửa, rồi bảo vẽ lại — không phải chạy cả quy trình mới biết nó vẽ gì.

    Dùng chung `generate_with_agent_models` với luồng quy trình, nên thứ tự ưu tiên
    model, việc bỏ qua model không vẽ được và cả hạn mức ngày đều giống hệt. Vẽ
    hỏng thì chỉ nói ra chứ không làm hỏng câu trả lời — buổi học vẫn tiếp tục.
    """
    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        return full
    names = {(await get_skill(sid) or {}).get("name") for sid in skill_ids}
    if "generate_post_image" not in names or not full:
        return full

    from core.image_gen import (
        extract_image_prompt, extract_image_ratio, extract_product_image,
        extract_product_placement, generate_with_agent_models, safe_product_path,
    )

    prompt = extract_image_prompt(full)
    if not prompt:
        return full

    # Khai báo ẢNH SẢN PHẨM thì prompt là mô tả nền, sản phẩm là ảnh thật dán lên.
    overlay = safe_product_path(extract_product_image(full), _DATA_ROOT)
    placement = extract_product_placement(full)

    save_dir = TRAINING_IMAGE_DIR / str(session_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now().strftime('%H%M%S')}.png"

    async def _notice(text: str) -> None:
        await _send(ws, {"type": "chunk", "content": f"\n\n{text}"})

    err = await generate_with_agent_models(
        prompt=prompt, ratio=extract_image_ratio(full),
        model_pool_ids=model_pool_ids or [], save_path=save_dir / name, notify=_notice,
        product_overlay=overlay, placement=placement,
    )
    if err:
        note = f"\n\n❌ Vẽ thử không thành: {err}"
        await _send(ws, {"type": "chunk", "content": note})
        return full + note

    url = f"/api/training/sessions/{session_id}/image/{name}"
    await _send(ws, {"type": "chunk", "content": f"\n\n![Ảnh vẽ thử]({url})"})
    return full + f"\n\n![Ảnh vẽ thử]({url})"


# ── Live DB context ───────────────────────────────────────────────────────────

async def _build_live_context() -> str:
    """Build a fresh snapshot of Xanax DB data to inject into every chat prompt."""
    import json as _json
    lines = ["**[DỮ LIỆU THỰC TẾ XANAX — cập nhật real-time mỗi tin nhắn]**\n"]

    agents = await list_agent_configs()
    skills_all = await list_skills()
    skill_map = {s["id"]: s["name"] for s in skills_all}

    lines.append("Nhân viên:")
    for a in agents:
        try:
            skill_ids = _json.loads(a.get("skills_json") or "[]")
            skill_names = [skill_map.get(i, str(i)) for i in skill_ids]
        except Exception:
            skill_names = []
        enabled = "✓" if a.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] {a['name']} | {a['role']} | model: {a.get('model','')} | skills: {', '.join(skill_names) or 'không có'}")

    lines.append("\nKỹ năng:")
    for s in skills_all:
        enabled = "✓" if s.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] {s['name']} — {s.get('description','')}")

    projects = await list_projects()
    project_map = {p["id"]: p["name"] for p in projects}
    lines.append("\nDự án:")
    for p in projects:
        lines.append(f"- [{p['status']}] {p['name']} — {(p.get('description') or '')[:80]}")

    lines.append("\nCông việc:")
    added_items = False
    for p in projects:
        items = await list_work_items(p["id"])
        for i in items:
            lines.append(f"- [{i['status']}] {i['title']} (dự án: {p['name']}, priority: {i.get('priority','')})")
            added_items = True
    if not added_items:
        lines.append("- (chưa có)")

    # Tách quy trình (kind=company) và tác vụ (kind=automation): hai loại khác nhau
    # và có thể trùng tên, gộp chung một danh sách thì không phân biệt được cái nào.
    workflows = await list_workflow_tasks()
    for kind, title in (
        ("company", "Quy trình (luồng phối hợp nhiều bước, thường gọi các tác vụ con)"),
        ("automation", "Tác vụ (một việc tự động đơn lẻ)"),
    ):
        rows = [w for w in workflows if (w.get("kind") or "automation") == kind]
        lines.append(f"\n{title}:")
        if not rows:
            lines.append("- (chưa có)")
        for w in rows:
            pname = project_map.get(w.get("project_id"), "?")
            lines.append(
                f"- id={w['id']} {w['name']} — {w.get('description','')} "
                f"(dự án: {pname}, trạng thái: {w.get('status','')})"
            )

    model_pool = await list_model_pool()
    lines.append("\nModel Pool:")
    for m in model_pool:
        enabled = "✓" if m.get("enabled", 1) else "✗"
        lines.append(f"- [{enabled}] ID={m['id']} {m['name']} | provider: {m.get('provider','')} | model_id: {m.get('model_id','')} | category: {m.get('category','')}")

    notes = await list_xanax_notes()
    if notes:
        lines.append("\nGhi nhớ của Xanax (bền vững giữa các session):")
        for n in notes:
            lines.append(f"- [Note #{n['id']}] {n['content']}")

    lines.append("\nKhi Papa hỏi về dữ liệu công ty → dùng thông tin trên, không suy đoán.")
    lines.append("""
---
## Hành động Xanax có thể thực hiện

Khi Papa yêu cầu thực hiện hành động, nhúng lệnh vào CUỐI response (sau nội dung trả lời):
[[XANAX:action|param1=value1|param2=value2]]

Hành động hỗ trợ:
- [[XANAX:save_note|content=Nội dung cần ghi nhớ lâu dài]] — Lưu ghi nhớ bền vững qua các session
- [[XANAX:delete_note|id=3]] — Xóa ghi nhớ cũ theo ID
- [[XANAX:create_work_item|project_id=1|title=Tên công việc|description=...|priority=high|assignee=Tên Agent]] — Tạo công việc mới trong dự án
- [[XANAX:update_work_item|id=5|status=in_progress|assignee=Tên Agent]] — Cập nhật trạng thái/người phụ trách
- [[XANAX:trigger_workflow|task_id=2|input=Chủ đề/nội dung cho lần chạy này]] — Kích hoạt quy trình tự động.
  input là chủ đề truyền vào node Bắt đầu; nếu Papa chưa nói rõ chủ đề thì hỏi lại, đừng tự bịa.

Quy tắc:
- Chỉ dùng khi Papa yêu cầu hành động cụ thể, KHÔNG tự ý thực hiện
- Dùng đúng ID thật từ dữ liệu phía trên (project_id, task_id, agent name)
- priority: low / medium / high / urgent | status: backlog / todo / in_progress / done
- Lệnh sẽ được thực thi tự động và Papa thấy kết quả — không cần giải thích lại lệnh""")
    return "\n".join(lines)


# ── Tool call execution ───────────────────────────────────────────────────────

_TOOL_RE = re.compile(r'\[\[XANAX:([^\]]+)\]\]')


def _parse_tool_calls(text: str) -> list[dict]:
    calls = []
    for m in _TOOL_RE.finditer(text):
        parts = m.group(1).split('|')
        action = parts[0].strip()
        params: dict[str, str] = {}
        for p in parts[1:]:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k.strip()] = v.strip()
        calls.append({'action': action, 'params': params})
    return calls


async def _execute_tool_call(call: dict) -> dict:
    action = call['action']
    params = call['params']
    try:
        if action == 'save_note':
            content = params.get('content', '').strip()
            if not content:
                return {'ok': False, 'action': action, 'error': 'content là bắt buộc'}
            note_id = await create_xanax_note(content)
            return {'ok': True, 'action': action, 'message': f'Đã lưu ghi nhớ #{note_id}'}

        elif action == 'delete_note':
            try:
                note_id = int(params.get('id', 0))
            except ValueError:
                return {'ok': False, 'action': action, 'error': 'id không hợp lệ'}
            ok = await delete_xanax_note(note_id)
            return {'ok': ok, 'action': action,
                    'message': f'Đã xóa ghi nhớ #{note_id}' if ok else f'Không tìm thấy ghi nhớ #{note_id}'}

        elif action == 'create_work_item':
            try:
                project_id = int(params.get('project_id', 0))
            except ValueError:
                project_id = 0
            title = params.get('title', '').strip()
            if not project_id or not title:
                return {'ok': False, 'action': action, 'error': 'project_id và title là bắt buộc'}
            description = params.get('description', '')
            priority = params.get('priority', 'medium')
            assigned_agent_id = None
            assignee = params.get('assignee', '').strip()
            if assignee:
                agents = await list_agent_configs()
                for a in agents:
                    if a['name'].lower() == assignee.lower() or str(a['id']) == assignee:
                        assigned_agent_id = a['id']
                        break
            item_id = await create_work_item(project_id, title, description, 'backlog', priority, assigned_agent_id)
            return {'ok': True, 'action': action, 'message': f'Đã tạo công việc #{item_id}: "{title}"'}

        elif action == 'update_work_item':
            try:
                item_id = int(params.get('id', 0))
            except ValueError:
                item_id = 0
            if not item_id:
                return {'ok': False, 'action': action, 'error': 'id là bắt buộc'}
            kwargs: dict = {}
            for k in ('status', 'priority', 'title', 'description'):
                if k in params:
                    kwargs[k] = params[k]
            if 'assignee' in params:
                agents = await list_agent_configs()
                for a in agents:
                    if a['name'].lower() == params['assignee'].lower() or str(a['id']) == params['assignee']:
                        kwargs['assigned_agent_id'] = a['id']
                        break
            ok = await update_work_item(item_id, **kwargs)
            return {'ok': ok, 'action': action,
                    'message': f'Đã cập nhật công việc #{item_id}' if ok else f'Không tìm thấy công việc #{item_id}'}

        elif action == 'trigger_workflow':
            try:
                task_id = int(params.get('task_id', 0))
            except ValueError:
                task_id = 0
            if not task_id:
                return {'ok': False, 'action': action, 'error': 'task_id là bắt buộc'}
            # Chủ đề đi kèm: quy trình nhận nó qua node Bắt đầu. Thiếu tham số này
            # thì quy trình chạy với đầu vào rỗng và nội dung do AI tự bịa.
            topic = str(params.get('input') or '').strip()
            from api.websocket_workflow import execute_workflow_headless
            asyncio.create_task(execute_workflow_headless(
                task_id, user_input=topic, triggered_by='chat',
            ))
            return {
                'ok': True, 'action': action,
                'message': f'Đã kích hoạt quy trình #{task_id}'
                           + (f' với chủ đề: "{topic}"' if topic else ' (không có chủ đề)'),
            }

        else:
            return {'ok': False, 'action': action, 'error': f'Hành động không hỗ trợ: {action}'}

    except Exception as e:
        logger.exception("Tool call failed: %s", action)
        return {'ok': False, 'action': action, 'error': str(e)}


# ── SOUL.md helpers ───────────────────────────────────────────────────────────

def _soul_path() -> Path:
    local_app_data = (
        os.environ.get("LOCALAPPDATA")
        or os.path.expandvars("%LOCALAPPDATA%")
        or str(Path.home() / "AppData" / "Local")
    )
    return Path(local_app_data) / "hermes" / "SOUL.md"


def _read_soul() -> str:
    p = _soul_path()
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _upsert_soul_note(session_id: int, session_title: str, content: str) -> None:
    """Insert or replace the tagged block for this session in SOUL.md."""
    p = _soul_path()
    if not p.exists():
        logger.warning("SOUL.md not found at %s — skipping upsert", p)
        return

    start_tag = f"<!-- SESSION:{session_id} -->"
    end_tag   = f"<!-- /SESSION:{session_id} -->"
    block     = f"{start_tag}\n**{session_title}**\n{content.strip()}\n{end_tag}"

    current = p.read_text(encoding="utf-8")

    if start_tag in current:
        pattern = re.escape(start_tag) + r".*?" + re.escape(end_tag)
        updated = re.sub(pattern, block, current, flags=re.DOTALL)
    else:
        marker = "## Ghi chú từ các session training"
        if marker in current:
            idx     = current.index(marker) + len(marker)
            updated = current[:idx] + "\n" + block + "\n" + current[idx:]
        else:
            updated = current.rstrip() + f"\n\n{marker}\n{block}\n"

    p.write_text(updated, encoding="utf-8")
    logger.info("SOUL.md upserted for session %s at %s", session_id, p)


# ── Summarise on Pass ─────────────────────────────────────────────────────────

async def _summarise_pass(
    session_id: int,
    session_title: str,
    history: list[dict],
    ws: WebSocket,
) -> None:
    """
    Papa bấm Pass → đúc kết hội thoại, upsert vào SOUL.md, thông báo client.
    """
    try:
        convo_lines = [
            f"{'Papa' if m['role'] == 'user' else 'Xanax'}: {m['content']}"
            for m in history
            if m["role"] in ("user", "assistant")
        ]
        if not convo_lines:
            return

        convo = "\n".join(convo_lines)
        soul  = _read_soul()
        live_context = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))

        prompt = (
            f'Dưới đây là đoạn hội thoại training giữa Papa và Xanax '
            f'về chủ đề "{session_title}":\n\n'
            f"{convo}\n\n"
            "Hãy đúc kết thành các điều quan trọng Xanax đã học hoặc được nhắc nhở "
            "trong session này. Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần đúc kết, không thêm lời dẫn hay giải thích."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        summary = await hermes.complete_with_context(messages)
        if not summary:
            return

        await update_training_session(session_id, result_notes=summary)
        _upsert_soul_note(session_id, session_title, summary)

        await _send(ws, {"type": "notes_updated", "content": summary})
        logger.info("Pass summary complete for session %s", session_id)

    except Exception:
        logger.exception("_summarise_pass failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Đúc kết thất bại"})


# ── Analyse on Fail ───────────────────────────────────────────────────────────

async def _analyse_fail(
    session_id: int,
    session_title: str,
    history: list[dict],
    ws: WebSocket,
) -> None:
    """
    Papa bấm Fail → phân tích điểm chưa ổn, lưu vào result_notes.
    KHÔNG cập nhật SOUL.md — đây là bài học từ thất bại để cải thiện sau.
    """
    try:
        convo_lines = [
            f"{'Papa' if m['role'] == 'user' else 'Xanax'}: {m['content']}"
            for m in history
            if m["role"] in ("user", "assistant")
        ]
        if not convo_lines:
            return

        convo = "\n".join(convo_lines)
        soul  = _read_soul()
        live_context = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))

        prompt = (
            f'Session training "{session_title}" đã được đánh dấu là FAIL.\n\n'
            f'Hội thoại:\n{convo}\n\n'
            "Hãy phân tích:\n"
            "1. Xanax đã làm gì chưa đúng hoặc chưa đủ trong session này?\n"
            "2. Cần cải thiện điều gì để session tương tự sẽ đạt Pass?\n"
            "Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần phân tích, không thêm lời dẫn."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        analysis = await hermes.complete_with_context(messages)
        if not analysis:
            return

        await update_training_session(session_id, result_notes=analysis)

        await _send(ws, {"type": "failure_analysed", "content": analysis})
        logger.info("Fail analysis complete for session %s", session_id)

    except Exception:
        logger.exception("_analyse_fail failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Phân tích thất bại"})


# ── Improve from fail feedback ────────────────────────────────────────────────

async def _improve_from_fail(
    session_id: int,
    session_title: str,
    feedback: str,
    ws: WebSocket,
) -> None:
    """
    Papa góp ý sau khi fail → Xanax đúc kết từ fail + góp ý → upsert vào SOUL.md.
    """
    try:
        session = await get_training_session(session_id)
        if not session:
            return

        soul          = _read_soul()
        live_context  = await _build_live_context()
        system_content = "\n\n".join(filter(None, [soul, live_context]))
        prev_analysis = session.get("result_notes", "")

        prompt = (
            f'Session training "{session_title}" đã fail. '
            f'Phân tích trước đó:\n{prev_analysis}\n\n'
            f'Papa góp ý thêm:\n{feedback}\n\n'
            "Dựa vào cả phân tích và góp ý của Papa, hãy đúc kết thành các điều "
            "Xanax cần ghi nhớ và cải thiện để hoàn thiện bản thân. "
            "Viết ngắn gọn, súc tích, dùng gạch đầu dòng. "
            "Chỉ trả lời phần đúc kết, không thêm lời dẫn."
        )

        messages: list[dict] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        improvement = await hermes.complete_with_context(messages)
        if not improvement:
            return

        await update_training_session(session_id, result_notes=improvement)
        _upsert_soul_note(session_id, session_title, improvement)

        await _send(ws, {"type": "notes_updated", "content": improvement})
        logger.info("Improve-from-fail complete for session %s", session_id)

    except Exception:
        logger.exception("_improve_from_fail failed for session %s", session_id)
        await _send(ws, {"type": "error", "message": "Đúc kết từ góp ý thất bại"})


# ── WebSocket handler ─────────────────────────────────────────────────────────

async def _send(ws: WebSocket, data: dict) -> None:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


@router.websocket("/ws/training")
async def websocket_training(websocket: WebSocket):
    await websocket.accept()
    logger.info("Training WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            # ── Action: pass / fail ───────────────────────────────────────────
            action = data.get("action")
            if action in ("summarise_pass", "summarise_fail", "improve_from_fail"):
                session_id = data.get("session_id")
                if not session_id:
                    await _send(websocket, {"type": "error", "message": "Missing session_id"})
                    continue

                session = await get_training_session(int(session_id))
                if not session:
                    await _send(websocket, {"type": "error", "message": "Session not found"})
                    continue

                if action == "summarise_pass":
                    history = await get_training_messages(int(session_id))
                    await _send(websocket, {"type": "status", "status": "summarising"})
                    asyncio.create_task(
                        _summarise_pass(int(session_id), session["title"], history, websocket)
                    )
                elif action == "summarise_fail":
                    history = await get_training_messages(int(session_id))
                    await _send(websocket, {"type": "status", "status": "analysing"})
                    asyncio.create_task(
                        _analyse_fail(int(session_id), session["title"], history, websocket)
                    )
                else:  # improve_from_fail
                    feedback = data.get("feedback", "").strip()
                    if not feedback:
                        await _send(websocket, {"type": "error", "message": "Góp ý trống"})
                        continue
                    await _send(websocket, {"type": "status", "status": "improving"})
                    asyncio.create_task(
                        _improve_from_fail(int(session_id), session["title"], feedback, websocket)
                    )
                continue

            # ── Chat message ──────────────────────────────────────────────────
            message             = data.get("message", "").strip()
            training_session_id = data.get("training_session_id")

            if not message:
                await _send(websocket, {"type": "error", "message": "Empty message"})
                continue
            if not training_session_id:
                await _send(websocket, {"type": "error", "message": "Missing training_session_id"})
                continue

            session = await get_training_session(int(training_session_id))
            if not session:
                await _send(websocket, {"type": "error", "message": "Training session not found"})
                continue

            # Persist user message
            await add_training_message(int(training_session_id), "user", message)

            # Buổi dạy có học viên: chính nhân viên đó trả lời, bằng model và
            # soul của nó. Không đi qua đường Xanax phía dưới, và đặc biệt không
            # phân tích [[XANAX:...]] — học viên không được cầm công cụ.
            if session.get("agent_id"):
                agent = await get_agent_config(int(session["agent_id"]))
                if not agent:
                    await _send(websocket, {
                        "type": "error",
                        "message": "Học viên của buổi dạy này đã bị xoá khỏi danh sách nhân viên.",
                    })
                    continue
                history = await get_training_messages(int(training_session_id))
                try:
                    try:
                        allowed_tools = json.loads(session.get("allowed_tools_json") or "[]")
                    except Exception:
                        allowed_tools = []
                    reply = await _stream_student(
                        websocket, agent, history, session.get("project_id"),
                        int(training_session_id), allowed_tools)
                    if reply.strip():
                        await add_training_message(
                            int(training_session_id), "assistant", reply.strip()
                        )
                    await _send(websocket, {"type": "done"})
                except Exception as e:
                    logger.exception("Student stream error for session %s", training_session_id)
                    await _send(websocket, {"type": "error", "message": str(e)})
                continue

            # Build context: SOUL.md + live DB snapshot → full history
            soul         = _read_soul()
            live_context = await _build_live_context()
            history      = await get_training_messages(int(training_session_id))

            system_content = "\n\n".join(filter(None, [soul, live_context]))
            messages: list[dict] = []
            if system_content:
                messages.append({"role": "system", "content": system_content})
            for m in history:
                messages.append({"role": m["role"], "content": m["content"]})

            # Stream main response
            await _send(websocket, {"type": "status", "status": "thinking"})
            assistant_chunks: list[str] = []

            try:
                async for chunk in hermes.stream_with_context(messages):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        break
                    await _send(websocket, {"type": "chunk", "content": chunk})
                    assistant_chunks.append(chunk)

                full_response = "".join(assistant_chunks)

                # Execute any embedded tool calls before persisting
                tool_calls = _parse_tool_calls(full_response)
                tool_results: list[dict] = []
                for call in tool_calls:
                    result = await _execute_tool_call(call)
                    tool_results.append(result)
                    logger.info("Tool executed: %s → %s", call['action'], result)

                # Strip [[XANAX:...]] blocks from the stored/displayed text
                clean_response = _TOOL_RE.sub('', full_response).strip()

                if clean_response:
                    await add_training_message(
                        int(training_session_id), "assistant", clean_response
                    )

                if tool_results:
                    await _send(websocket, {"type": "tool_executed",
                                            "clean_text": clean_response,
                                            "results": tool_results})

                await _send(websocket, {"type": "done"})

            except Exception as e:
                logger.exception("Training stream error for session %s", training_session_id)
                await _send(websocket, {"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info("Training WebSocket disconnected")
    except Exception as e:
        logger.exception("Training WebSocket error")
        try:
            await _send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
