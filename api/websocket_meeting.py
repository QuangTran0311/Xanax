"""
Meeting Room WebSocket — multi-agent real-time discussion, điều phối bởi Xanax.

Xanax (không phải 1 nhân viên trong agent_configs — dùng chung persona/model với
trợ lý chính, xem core/hermes_bridge.py + core/soul_sync.py) luôn là người trả lời
CEO đầu tiên khi chưa ai đang giữ lượt trao đổi. Dựa vào nội dung CEO nhắn, Xanax
tự quyết định gọi trưởng phòng / nhân viên nào ra trả lời (tối thiểu, tránh gọi cả
phòng ban hay người không liên quan gây tốn token) — xem `_xanax_orchestrate`.

CEO cũng có thể @TênNhânViên để gọi thẳng người đó, bỏ qua bước Xanax cân nhắc
(rẻ hơn, chủ đích rõ ràng — xem `_extract_mentions`).

Một khi 1 nhân viên đã được gọi ra (qua @mention hoặc Xanax mời), người đó "giữ
lượt" — các tin nhắn tiếp theo KHÔNG cần tag lại tên vẫn do đúng người này trả
lời liên tục, không bị Xanax giành lại giữa chừng (xem biến `active_agent_id`).
CEO chỉ cần gọi tên "Xanax" trong tin nhắn, hoặc @tag 1 nhân viên khác, để lấy
lại quyền điều phối / đổi người đang giữ lượt.

Client → Server:
  { "type": "user_message", "content": "...", "targets": [1, 2] }  -- targets (tuỳ chọn): agent_config IDs
                                                                       được suy ra từ @mention phía client;
                                                                       rỗng/không có = để Xanax tự quyết định
  { "type": "end_meeting" }

Server → Client:
  { "type": "history", "messages": [...] }
  { "type": "user_message", "sender": "user", "content": "..." }
  { "type": "agent_thinking", "agent": "name", "agent_id": N, "color": "...", "department": "..." }
  { "type": "agent_chunk",   "agent": "name", "agent_id": N, "color": "...", "department": "...", "content": "..." }
  { "type": "agent_done",    "agent": "name", "agent_id": N, "department": "..." }
  { "type": "participants_updated", "participants": [...] }
  { "type": "meeting_ended", "draft_minutes": "..." }
  { "type": "error", "message": "..." }
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.agent_soul import read_soul, sync_agent_soul
from core.hermes_bridge import hermes
from hub.database import (
    add_meeting_message, get_agent_configs_by_ids,
    get_meeting, get_meeting_messages, update_meeting,
    list_departments, list_agent_configs, get_skill,
    list_projects, list_work_items,
    list_workflow_tasks, get_workflow_task,
)

logger = logging.getLogger("xanax.ws.meeting")
router = APIRouter()

XANAX_AGENT_ID = 0
XANAX_NAME = "Xanax"
XANAX_AVATAR = "🧭"

# Tiền tố "[Tên]: " mà model đôi khi bịa ra ở đầu câu trả lời (bắt chước format lịch sử) —
# dùng để cắt bỏ khỏi stream trước khi hiện lên UI (bong bóng chat đã có tên/avatar riêng).
_LEADING_SPEAKER_RE = re.compile(r"^\s*\[[^\]\n]{1,40}\]\s*:\s*")


async def _build_skills_content(agent: dict) -> str:
    """Ghép nội dung các skill đã gắn cho nhân viên (tab Kỹ năng) vào system prompt —
    giống hệt luồng quy trình (xem api/websocket_workflow.py) để 1 skill có tác dụng như
    nhau dù chạy trong quy trình hay trong phòng họp. Trước đây phòng họp bỏ qua hoàn
    toàn skills_json nên skill gắn cho nhân viên không hề có tác dụng khi họp."""
    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        skill_ids = []
    parts = []
    for sid in skill_ids:
        skill = await get_skill(sid)
        if skill:
            content = json.loads(skill.get("config_json") or "{}").get("content", "")
            if content:
                parts.append(content)
    return "\n\n---\n".join(parts)


async def _build_agent_tools(agent: dict) -> list[dict]:
    """Tool schema cho skill đã gắn cho nhân viên — dùng CHUNG hàm với luồng quy
    trình để một skill có tác dụng như nhau dù chạy ở đâu.

    Trước đây phòng họp có bản sao riêng chỉ xử lý skill loại 'builtin', bỏ qua
    im lặng cả 'api' lẫn 'mcp'. Hệ quả: nhân viên được gắn skill API/MCP vào họp
    thì không có tool nào, và vì model vẫn được yêu cầu làm việc đó nên nó bịa ra
    kết quả. Gọi thẳng bản của websocket_workflow để hai luồng không thể lệch
    nhau lần nữa.
    """
    try:
        skill_ids = json.loads(agent.get("skills_json") or "[]")
    except Exception:
        skill_ids = []
    if not skill_ids:
        return []

    from api.websocket_workflow import _build_agent_tools as _build_tools_shared

    schemas = await _build_tools_shared(skill_ids)
    return schemas


async def _department_head_context(agent: dict) -> str:
    """Nếu nhân viên này là TRƯỞNG PHÒNG của 1 phòng ban, ghép thêm dữ liệu thực tế về
    nhân viên trong phòng + công việc đang được giao cho từng người + lịch sử chạy quy
    trình gần đây của từng người, để trưởng phòng trả lời có căn cứ (không bịa) khi CEO
    hỏi về tình hình nhân sự/công việc/lịch sử làm việc của phòng ban. Trước đây trưởng
    phòng chỉ thấy được work_items đang active, không truy xuất được run history — chỉ có
    Xanax mới có quyền đó, khiến trưởng phòng phải từ chối trả lời và bảo CEO hỏi Xanax."""
    departments = await list_departments()
    dept = next((d for d in departments if d.get("head_agent_id") == agent["id"]), None)
    if not dept:
        return ""

    all_agents = await list_agent_configs()
    members = [a for a in all_agents if a.get("department_id") == dept["id"]]
    member_ids = {m["id"] for m in members}

    lines = [f"**[DỮ LIỆU THỰC TẾ — Phòng {dept['name']}, bạn là trưởng phòng]**", "Nhân viên trong phòng:"]
    for m in members:
        tag = " (chính bạn)" if m["id"] == agent["id"] else ""
        lines.append(f"- {m['name']} — {m['role']}{tag}")

    lines.append("\nCông việc đang được giao cho nhân viên trong phòng:")
    found = False
    for p in await list_projects():
        for it in await list_work_items(p["id"]):
            if it.get("assigned_agent_id") in member_ids:
                lines.append(
                    f"- [{it['status']}] {it['title']} — giao cho {it.get('agent_name', '?')} "
                    f"(dự án: {p['name']}, priority: {it.get('priority', '')})"
                )
                found = True
    if not found:
        lines.append("- (chưa có việc nào được giao cho ai trong phòng)")

    # Lịch sử chạy quy trình đã qua (không chỉ work_items đang active) — trưởng phòng quản
    # lý nhân sự thì phải nắm được cả việc nhân viên ĐÃ làm trước đây, không chỉ việc đang
    # active. Trước đây chỉ Xanax mới truy xuất được run history, trưởng phòng không có.
    lines.append("\nLịch sử chạy quy trình gần đây của nhân viên trong phòng:")
    from hub.database import list_agent_run_history
    history_found = False
    for m in members:
        runs = await list_agent_run_history(m["id"], limit=5)
        for r in runs:
            verdict = f", đánh giá: {r['pass_fail']}" if r.get("pass_fail") else ""
            when = r.get("completed_at") or r.get("created_at") or ""
            lines.append(f"- {m['name']} — [{r.get('status', '')}] {r.get('task_name', '?')} lúc {when}{verdict}")
            history_found = True
    if not history_found:
        lines.append("- (chưa có lịch sử chạy quy trình nào)")

    lines.append("\nDùng đúng dữ liệu trên khi Papa hỏi về nhân sự/công việc trong phòng, không suy đoán/bịa.")
    return "\n".join(lines)


async def _stream_agent(ws: WebSocket, agent: dict, messages: list[dict]) -> str:
    """Call LLM with agent persona, stream chunks to client, return full response."""
    persona_prompt = agent["system_prompt"] or (
        f"You are {agent['name']}, working as {agent['role']}. "
        "Respond concisely and helpfully in the context of the meeting."
    )
    skills_content = await _build_skills_content(agent)
    dept_context = await _department_head_context(agent)
    # soul.md riêng của nhân viên (xem core/agent_soul.py) — mô phỏng lại SOUL.md của
    # Hermes/Xanax nhưng thu hẹp về đúng 1 người: mô tả/tính cách + dữ liệu thực tế +
    # bài học ĐẠT/KHÔNG ĐẠT từ các lần làm việc trước, để nhân viên tự cải thiện.
    await sync_agent_soul(agent)
    soul_content = read_soul(agent["id"])
    # Lịch sử hội thoại format "[Tên]: nội dung" (xem conv_context) khiến model dễ bắt
    # chước tự thêm tiền tố "[TênMình]: " vào đầu câu trả lời của chính mình — thừa và
    # xấu vì UI đã hiển thị sẵn tên người nói ở avatar/header rồi.
    system_prompt = "\n\n".join(filter(None, [
        persona_prompt,
        skills_content,
        dept_context,
        soul_content,
        # Hàng phòng thủ cuối: dù routing có sai (CEO tag thẳng tên nhân viên trong câu lệnh
        # chạy quy trình chẳng hạn), nhân viên vẫn không được bịa kết quả. Lịch sử hội thoại
        # có sẵn kết quả của lần chạy trước nên model rất dễ chép lại thành "kết quả mới".
        "Bạn KHÔNG có quyền chạy quy trình hay tác vụ tự động — chỉ Xanax kích hoạt được. "
        "Nếu Papa yêu cầu bạn chạy một quy trình/tác vụ, hãy nói thẳng là cần Xanax kích hoạt "
        "và đề nghị Papa nhờ Xanax. TUYỆT ĐỐI không thông báo là đã chạy, đang chạy, hay đã "
        "xong, và không bịa ra kết quả — kể cả khi trong lịch sử phía trên đã có kết quả của "
        "một lần chạy trước đó; kết quả cũ KHÔNG phải kết quả của lần Papa vừa yêu cầu.",
        f"Bạn LÀ {agent['name']} ({agent['role']}). Luôn trả lời với tư cách chính bạn, xưng "
        "hô ở ngôi thứ nhất (con/tôi/mình). TUYỆT ĐỐI không đóng vai Xanax hay bất kỳ nhân "
        "viên nào khác, không nói về bản thân ở ngôi thứ ba, không tổng hợp/điều phối thay "
        "Xanax. Lịch sử phía trên ghi theo dạng \"[Tên]: nội dung\" chỉ để bạn biết ai đã nói "
        f"gì — KHÔNG thêm tiền tố \"[{agent['name']}]: \" hay bất kỳ \"[Tên]: \" nào vào đầu "
        "câu trả lời, chỉ trả lời trực tiếp nội dung của riêng bạn.",
    ]))

    await ws.send_json({
        "type": "agent_thinking",
        "agent": agent["name"],
        "agent_id": agent["id"],
        "color": agent["avatar_color"],
        "department": agent.get("department_name"),
    })

    llm_messages = [{"role": "system", "content": system_prompt}] + messages

    # Model đôi khi vẫn bắt chước lịch sử "[Tên]: ..." mà bịa tiền tố tên (vd "[Xanax]: ")
    # ngay đầu câu. Bong bóng chat đã hiển thị tên/avatar riêng nên tiền tố này thừa và gây
    # hiểu nhầm. Đệm phần đầu stream lại, cắt bỏ tiền tố "[Tên]: " trước khi hiện ra UI.
    _prefix_state = {"buf": "", "done": False}

    async def _emit_chunk(text: str) -> None:
        await ws.send_json({
            "type": "agent_chunk",
            "agent": agent["name"],
            "agent_id": agent["id"],
            "color": agent["avatar_color"],
            "department": agent.get("department_name"),
            "content": text,
        })

    async def _emit(delta: str) -> None:
        if _prefix_state["done"]:
            await _emit_chunk(delta)
            return
        _prefix_state["buf"] += delta
        buf = _prefix_state["buf"]
        m = _LEADING_SPEAKER_RE.match(buf)
        if m:  # đã thấy trọn "[Tên]: " -> bỏ nó, xả phần còn lại
            _prefix_state["done"] = True
            remainder = buf[m.end():]
            _prefix_state["buf"] = ""
            if remainder:
                await _emit_chunk(remainder)
            return
        stripped = buf.lstrip()
        # Đầu câu không phải "[" (không có tiền tố), hoặc đệm đã quá dài mà chưa khớp -> xả hết
        if (stripped and not stripped.startswith("[")) or len(buf) > 45:
            _prefix_state["done"] = True
            _prefix_state["buf"] = ""
            await _emit_chunk(buf)

    async def _flush_pending() -> None:
        if not _prefix_state["done"] and _prefix_state["buf"]:
            await _emit_chunk(_prefix_state["buf"])
            _prefix_state["buf"] = ""
            _prefix_state["done"] = True

    # Model lấy từ danh sách ưu tiên đã cấu hình cho nhân viên (tab Nhân sự), tự fallback
    # sang model kế tiếp nếu model đầu gặp sự cố — giống hệt luồng workflow (xem
    # api/websocket_workflow.py). Trước đây phòng họp chỉ dùng agent["model"] (cột đơn,
    # không phản ánh đúng model_pool_ids_json) nên luôn rơi về hermes.model mặc định.
    try:
        model_pool_ids: list[int] = json.loads(agent.get("model_pool_ids_json") or "[]")
    except Exception:
        model_pool_ids = []

    full_response = ""
    try:
        if model_pool_ids:
            from core.model_pool_bridge import stream_from_agent_models
            agent_tools = await _build_agent_tools(agent)
            try:
                agent_skill_ids = json.loads(agent.get("skills_json") or "[]")
            except Exception:
                agent_skill_ids = []
            async for delta in stream_from_agent_models(
                model_pool_ids, llm_messages, tools=agent_tools or None,
                skill_ids=agent_skill_ids,
            ):
                full_response += delta
                await _emit(delta)
        else:
            model = agent["model"] or hermes.model
            payload = {"model": model, "messages": llm_messages, "stream": True}
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{hermes.base_url}/chat/completions",
                    headers=hermes._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            delta = (
                                chunk_data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                full_response += delta
                                await _emit(delta)
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        await _flush_pending()  # xả nốt phần đầu còn đệm nếu câu trả lời ngắn/chưa khớp prefix
    except Exception as e:
        logger.exception("Agent %s stream failed", agent["name"])
        full_response = f"[Error: {e}]"
        await _emit_chunk(full_response)

    await ws.send_json({
        "type": "agent_done",
        "agent": agent["name"],
        "agent_id": agent["id"],
        "department": agent.get("department_name"),
    })
    return full_response


def _extract_mentions(content: str, all_agents: list[dict]) -> list[int]:
    """CEO gõ @TênNhânViên -> gọi thẳng người đó, bỏ qua bước Xanax cân nhắc."""
    lower = content.lower()
    return [a["id"] for a in all_agents if a.get("name") and f"@{a['name'].lower()}" in lower]


def _extract_named_agents(content: str, all_agents: list[dict], present_ids: list[int]) -> list[int]:
    """CEO nhắc thẳng TÊN nhân viên ĐANG Ở TRONG phòng họp (không cần gõ @) -> chính người
    đó trả lời, không để Xanax giành lượt. Đây là điều CEO trực giác mong đợi: gọi tên ai
    đang họp thì đúng người đó lên tiếng. Chỉ khớp tên như 1 từ nguyên vẹn (word boundary).

    Quan trọng: chỉ tính người ĐANG có mặt. Nếu phòng họp trống (hoặc người được nhắc chưa
    vào phòng) thì KHÔNG tạo target -> mọi câu hỏi mặc định về Xanax điều phối, kể cả khi
    CEO có nhắc thẳng tên. Muốn gọi người chưa có mặt vào thì để Xanax mời, hoặc @mention."""
    present = set(present_ids)
    lower = content.lower()
    found = []
    for a in all_agents:
        if a["id"] not in present:
            continue
        name = (a.get("name") or "").lower()
        if name and re.search(r"\b" + re.escape(name) + r"\b", lower):
            found.append(a["id"])
    return found


_DISMISS_KEYWORDS = ("đuổi", "kick", "loại", "cho rời", "mời ra", "cho ra khỏi", "ra khỏi phòng", "remove", "dismiss")


def _extract_dismiss_targets(content: str, current_participants: list[dict]) -> list[int]:
    """CEO gõ lệnh đuổi kèm tên 1 nhân viên ĐANG có mặt trong phòng -> đuổi thẳng ngay,
    không chờ Xanax quyết định qua JSON (dismiss_agents). Bắt buộc phải xử lý xác định
    (deterministic) chứ không thể chỉ dựa vào JSON của Xanax, vì 2 lỗi từng gặp:
    (1) nếu nhân viên đó đang giữ lượt trao đổi (active_agent_id), tin nhắn "đuổi X" không
    tag "xanax"/@người khác sẽ bị route thẳng tới chính X — X tự nhận là đã rời phòng
    (hallucination) mà state phòng họp không hề đổi; (2) kể cả khi route đúng tới Xanax,
    model đôi khi xác nhận bằng lời trong "reply" nhưng quên đưa id vào "dismiss_agents",
    nên participants_updated không được gửi mà lời xác nhận vẫn hiển thị cho CEO."""
    lower = content.lower()
    if not any(k in lower for k in _DISMISS_KEYWORDS):
        return []
    return [a["id"] for a in current_participants if a.get("name") and a["name"].lower() in lower]


_SUMMON_KEYWORDS = ("mời", "gọi", "đưa", "triệu tập", "tham gia", "thêm", "vào đây",
                    "vào phòng", "vào họp", "vào cuộc họp", "invite", "add", "call in")


def _extract_summon_targets(content: str, all_agents: list[dict], departments: list[dict]) -> list[int]:
    """CEO ra lệnh mời/gọi/đưa ai đó VÀO phòng họp -> thêm thẳng người đó ngay, không phụ
    thuộc việc Xanax có bỏ đúng id vào call_agents hay không (Xanax nhiều lần nói "đã mời X
    vào" nhưng call_agents lại rỗng nên chẳng ai được thêm — xem bug CEO báo). Khớp theo:
    (a) tên nhân viên cụ thể, hoặc (b) "trưởng phòng <tên phòng>" -> trưởng phòng phòng đó.
    Chỉ kích hoạt khi câu có từ khoá triệu tập rõ ràng để tránh khớp nhầm."""
    lower = content.lower()
    if not any(k in lower for k in _SUMMON_KEYWORDS):
        return []
    ids: list[int] = []
    for a in all_agents:
        name = (a.get("name") or "").lower()
        if name and re.search(r"\b" + re.escape(name) + r"\b", lower):
            ids.append(a["id"])
    # "trưởng phòng marketing", "phòng marketing"... -> trưởng phòng của phòng ban được nhắc tên
    for d in departments:
        dname = (d.get("name") or "").lower()
        if dname and dname in lower and d.get("head_agent_id"):
            ids.append(d["head_agent_id"])
    return list(dict.fromkeys(ids))


async def _build_roster_text() -> str:
    """Danh sách phòng ban (kèm trưởng phòng) + nhân viên, cho Xanax biết ai đang có
    trong công ty để quyết định gọi ai ra trả lời."""
    departments = await list_departments()
    agents = await list_agent_configs()
    by_dept: dict[int | None, list[dict]] = {}
    for a in agents:
        by_dept.setdefault(a.get("department_id"), []).append(a)

    lines = []
    for d in departments:
        members = by_dept.pop(d["id"], [])
        head = f" (Trưởng phòng: {d['head_agent_name']}, id={d['head_agent_id']})" if d.get("head_agent_name") else " (chưa có trưởng phòng)"
        member_txt = ", ".join(f"{m['name']} (id={m['id']}, vai trò: {m['role']})" for m in members) or "(chưa có nhân viên)"
        lines.append(f"- Phòng {d['name']}{head}: {member_txt}")

    unassigned = by_dept.pop(None, [])
    if unassigned:
        member_txt = ", ".join(f"{m['name']} (id={m['id']}, vai trò: {m['role']})" for m in unassigned)
        lines.append(f"- (Chưa gán phòng ban): {member_txt}")

    return "\n".join(lines) if lines else "(chưa có phòng ban/nhân viên nào)"


def _strip_hallucinated_continuation(text: str, agent_names: list[str]) -> str:
    """Lịch sử hội thoại được format kiểu '[Tên]: nội dung' để phân biệt người nói
    (xem conv_context) — model đôi khi bắt chước format này: (a) TỰ BỊA tiếp lời của
    người khác ngay trong câu trả lời của Xanax (vd Xanax nói xong rồi viết luôn hộ
    '[Prozac]: ...') thay vì dừng lại và để `call_agents` gọi người đó trả lời riêng,
    hoặc (b) tự thêm tiền tố tên chính mình ở đầu câu (vd '[Xanax]: Vâng...'), thừa vì
    UI đã hiển thị tên người nói ở avatar/header rồi. Dọn cả 2 trường hợp."""
    if not text:
        return text
    names = sorted(set(n for n in agent_names if n) | {XANAX_NAME}, key=len, reverse=True)
    if not names:
        return text.strip()
    name_group = "|".join(re.escape(n) for n in names)
    # (a) tiếp lời người khác giữa chừng — cắt tại đó
    continuation = re.search(r"\n\s*\[(?:%s)\]\s*:" % name_group, text)
    if continuation:
        text = text[:continuation.start()]
    # (b) tự gắn tiền tố tên ngay đầu câu — bỏ tiền tố, giữ lại nội dung
    text = re.sub(r"^\s*\[(?:%s)\]\s*:\s*" % name_group, "", text)
    return text.strip()


# Chỉ Xanax mới kích hoạt được quy trình/tác vụ (qua "run_workflows" trong
# _xanax_orchestrate). Nhân viên KHÔNG có đường nào chạy chúng — nên mọi câu lệnh
# chạy quy trình bắt buộc phải đi qua Xanax, kể cả khi CEO đang trò chuyện dở với
# một nhân viên. Bug đã gặp: lần đầu "chạy quy trình X" thì Xanax điều phối và
# quy trình chạy thật; lần thứ hai, do active_agent_id đã trỏ vào nhân viên vừa
# được gọi ra, câu lệnh bị route thẳng cho nhân viên đó — họ không chạy được gì
# nhưng thấy trong lịch sử có sẵn kết quả lần trước nên bịa ra kết quả tương tự.
_WF_VERB = (
    r"(?:chạy|chay|gọi|goi|kích\s*hoạt|kich\s*hoat|khởi\s*động|khoi\s*dong"
    r"|thực\s*thi|thuc\s*thi|thực\s*hiện|thuc\s*hien|trigger|run|execute)"
)
_WF_NOUN = r"(?:quy\s*trình|quy\s*trinh|tác\s*vụ|tac\s*vu|workflow|task)"
_RUN_WORKFLOW_RE = re.compile(
    rf"{_WF_VERB}\b[^.\n]{{0,40}}?\b{_WF_NOUN}|{_WF_NOUN}\b[^.\n]{{0,40}}?\b{_WF_VERB}",
    re.IGNORECASE,
)


def _is_workflow_command(content: str) -> bool:
    """Câu này có phải lệnh chạy quy trình/tác vụ không.

    Cố tình bắt rộng: nhận nhầm chỉ khiến Xanax xử lý câu đó thay vì nhân viên
    (Xanax vẫn gọi lại nhân viên qua call_agents được) — rẻ. Bỏ sót thì nhân viên
    bịa kết quả cho một quy trình chưa hề chạy — đắt.
    """
    return bool(_RUN_WORKFLOW_RE.search(content or ""))


# Dấu hiệu Xanax đang KHẲNG ĐỊNH đã chạy, chứ không phải hứa sẽ chạy hay hỏi lại.
_WF_DONE_MARK_RE = re.compile(
    r"\b(?:đã|da|vừa|vua|rồi|roi|xong|đang|dang)\b", re.IGNORECASE
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Câu đang KỂ LẠI một lần chạy trước (thường là để báo hỏng), không phải khẳng
# định vừa kích hoạt cái mới.
_WF_REPORT_RE = re.compile(
    r"\b(?:lỗi|loi|thất\s*bại|that\s*bai|fail|error|dừng|dung\s*lai|"
    r"không\s*thành\s*công|khong\s*thanh\s*cong|chưa\s*xong|chua\s*xong)\b",
    re.IGNORECASE,
)


def _claims_workflow_ran(reply: str) -> bool:
    """Câu trả lời này có KHẲNG ĐỊNH vừa kích hoạt quy trình không.

    Xét theo từng câu chứ không theo cả đoạn: một đoạn thường vừa hỏi vừa kể, và
    dấu hoàn thành của câu này dễ bị ghép nhầm với động từ của câu kia.

    Hai loại câu bị loại vì chúng KHÔNG phải lời khẳng định:

    - **Câu hỏi.** "Papa muốn con kích hoạt lại quy trình không, hay để Papa xử
      lý phần ảnh trước rồi chạy lại sau?" — đủ cả động từ, danh từ lẫn chữ
      "rồi", nhưng đang xin ý kiến.
    - **Câu báo hỏng.** "Quy trình 'Đăng bài lên fanpage' vừa chạy bị lỗi ở bước
      tạo ảnh." — chủ ngữ là quy trình chứ không phải Xanax; đây là kể lại lần
      chạy trước có thật, đính chính vào đó là sai.

    Chỗ này cố tình thà BỎ SÓT hơn là báo nhầm: bỏ sót thì quay lại đúng hành vi
    cũ, còn đính chính một lời Xanax chưa hề nói sẽ làm người dùng mất tin vào
    chính cơ chế đính chính.
    """
    for sentence in _SENTENCE_SPLIT_RE.split(reply or ""):
        sentence = sentence.strip()
        if not sentence or sentence.endswith("?") or _WF_REPORT_RE.search(sentence):
            continue
        if _RUN_WORKFLOW_RE.search(sentence) and _WF_DONE_MARK_RE.search(sentence):
            return True
    return False


# Dấu hiệu Xanax đang HỨA sẽ chạy, chưa khẳng định đã chạy.
_WF_PROMISE_RE = re.compile(
    r"\b(?:sẽ|se|sắp|sap)\b|\bđể\s+con\b|\bde\s+con\b", re.IGNORECASE
)


def _promises_workflow_run(reply: str) -> bool:
    """Câu trả lời này có HỨA sẽ kích hoạt quy trình không.

    Tách riêng khỏi _claims_workflow_ran vì đây là kiểu hỏng khác: Xanax không
    nói dối về quá khứ, nó hứa về tương lai rồi không có lượt nào để thực hiện.
    Quan sát thật: "Dạ, con sẽ kích hoạt quy trình 'Đăng bài lên fanpage' với
    chủ đề 'móc khóa con khỉ' ngay ạ." — run_workflows rỗng, không gì chạy, và
    vì đây không phải lời khẳng định nên không bị đính chính. CEO phải hỏi lại
    "đã kích hoạt chưa" mới lòi ra.

    Chỉ xét khi CEO thật sự vừa bảo chạy (xem `asked_to_run`), nên một lời hứa
    có điều kiện hợp lệ ("con sẽ chạy sau khi Papa duyệt") cũng không bị hiểu
    sai — ghi chú đính kèm chỉ nêu TRẠNG THÁI THẬT, không quy kết ai nói dối.
    """
    for sentence in _SENTENCE_SPLIT_RE.split(reply or ""):
        sentence = sentence.strip()
        if not sentence or sentence.endswith("?") or _WF_REPORT_RE.search(sentence):
            continue
        if _RUN_WORKFLOW_RE.search(sentence) and _WF_PROMISE_RE.search(sentence):
            return True
    return False


# Lời Xanax nói chỉ là chữ do model sinh ra; thứ thật sự chạy quy trình là mảng
# "run_workflows". Prompt đã dặn "không nói là đã chạy nếu để run_workflows rỗng",
# nhưng dặn không phải là ép: model vẫn nói "con đã chạy lại quy trình #14 rồi"
# với mảng rỗng, và người dùng ngồi chờ một quy trình chưa hề khởi động. Câu xác
# nhận thật luôn do _run_workflows_from_meeting sinh ra, không bao giờ do model.
_FALSE_CLAIM_NOTE = (
    "⚠️ Đính chính tự động: Xanax nói đã chạy nhưng thực tế CHƯA có quy trình nào được "
    "kích hoạt. Hãy nhắc lại kèm tên quy trình và chủ đề — ví dụ: "
    '"chạy quy trình Đăng bài lên fanpage với chủ đề móc khóa cỏ 4 lá".'
)


# Lời hứa suông khác lời nói dối, nên ghi chú cũng phải khác: chỉ nêu trạng
# thái thật, không quy kết. Xanax có thể đang hứa hợp lệ ("con sẽ chạy sau khi
# Papa duyệt"), và câu dưới đây vẫn đúng trong cả hai trường hợp.
_EMPTY_PROMISE_NOTE = (
    "⚠️ Trạng thái thật: lượt này CHƯA có quy trình nào được kích hoạt — trên đây mới "
    "là dự định. Nếu Papa muốn chạy ngay, nhắc lại kèm tên quy trình và chủ đề."
)


def _guard_false_run_claim(reply: str, run_workflows: list, asked_to_run: bool = True) -> str:
    """Gắn đính chính khi lời nói không khớp việc đã làm.

    `asked_to_run` = lượt này CEO có thật sự bảo chạy quy trình không. Nếu không,
    Xanax nhắc tới một quy trình đang chạy là chuyện bình thường — nó kể lại lần
    kích hoạt trước chứ không nhận công. Đã đính chính oan đúng kiểu đó: CEO hỏi
    cách HUỶ quy trình, Xanax đáp "quy trình #14 vừa được kích hoạt và đang chạy"
    (đúng sự thật), và bị dán thêm "thực tế CHƯA có quy trình nào được kích hoạt".

    Đính chính được nối thẳng vào lời Xanax (thay vì gửi riêng) để nó cũng đi vào
    lịch sử hội thoại — nếu không, lượt sau Xanax đọc lại vẫn tưởng mình đã chạy
    và tiếp tục báo cáo tiến độ của một quy trình không tồn tại.
    """
    if run_workflows or not asked_to_run:
        return reply
    if _claims_workflow_ran(reply):
        note = _FALSE_CLAIM_NOTE
    elif _promises_workflow_run(reply):
        note = _EMPTY_PROMISE_NOTE
    else:
        return reply
    return f"{reply}\n\n{note}" if reply else note


_ORCH_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

# Xanax biết HAI phương ngữ để kích hoạt quy trình. Chat huấn luyện dùng marker
# [[XANAX:trigger_workflow|...]] (xem api/websocket_training.py); phòng họp dùng
# trường "run_workflows" trong JSON. Model học marker từ nội dung session
# training được nhét vào base_context, nên trong phòng họp nó vẫn viết marker
# vào giữa "reply" và để "run_workflows" rỗng.
#
# Hậu quả quan sát được: quy trình KHÔNG chạy, marker hiện nguyên văn ra màn
# hình, và vì lời Xanax được lưu vào meeting_messages nên lượt sau nó đọc lại
# lịch sử của chính mình, thấy marker, rồi bắt chước tiếp — một vòng lặp tự
# củng cố. Ba tin nhắn trong DB đã dính đúng kiểu này.
#
# Nên ở đây coi marker là cách viết TƯƠNG ĐƯƠNG với run_workflows: quy nó về
# cùng một chỗ để việc thật sự xảy ra, thay vì bắt model phải nhớ đúng phương
# ngữ. Prompt vẫn dặn dùng JSON; đây là lưới đỡ, không phải lời mời dùng marker.
_TRIGGER_MARKER_RE = re.compile(
    r"\[\[XANAX:trigger_workflow\|([^\]]*)\]\]", re.IGNORECASE
)
# Mọi marker khác (save_note, create_work_item...) phòng họp không thực hiện
# được. Vẫn phải gỡ khỏi lời nói: để nguyên thì người dùng đọc được một chuỗi
# kỹ thuật vô nghĩa, và nó lại trôi vào lịch sử nuôi tiếp vòng lặp trên.
_ANY_MARKER_RE = re.compile(r"\[\[XANAX:[^\]]*\]\]", re.IGNORECASE)


def _extract_trigger_markers(reply: str) -> tuple[str, list[dict]]:
    """Tách marker trong lời nói thành (lời đã sạch, danh sách quy trình cần chạy)."""
    runs: list[dict] = []
    for m in _TRIGGER_MARKER_RE.finditer(reply or ""):
        params: dict[str, str] = {}
        for part in m.group(1).split("|"):
            if "=" in part:
                k, _, v = part.partition("=")
                params[k.strip().lower()] = v.strip()
        task_id = params.get("task_id", "")
        if task_id.lstrip("-").isdigit():
            runs.append({"task_id": int(task_id), "input": params.get("input", "")})

    cleaned = _ANY_MARKER_RE.sub("", reply or "")
    # Gỡ marker thường để lại dòng trống thừa và dấu hai chấm cụt ở cuối câu
    # dẫn ("Để con kích hoạt ngay bây giờ:"), nên dọn luôn cho lời nói gọn.
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    cleaned = re.sub(r":\s*$", ".", cleaned)
    return cleaned, runs


def _parse_orchestrator_json(raw: str) -> dict:
    m = _ORCH_JSON_RE.search(raw or "")
    if m:
        try:
            data = json.loads(m.group(0))
            reply, marker_runs = _extract_trigger_markers(str(data.get("reply") or ""))
            runs = [
                {"task_id": int(item["task_id"]), "input": str(item.get("input") or "")}
                for item in (data.get("run_workflows") or [])
                if isinstance(item, dict) and str(item.get("task_id", "")).lstrip("-").isdigit()
            ]
            # Marker chỉ bù vào khi model quên điền run_workflows. Nếu nó viết cả
            # hai thì hai bên nói cùng một việc — cộng dồn sẽ chạy quy trình hai lần.
            seen = {(r["task_id"], r["input"]) for r in runs}
            runs += [r for r in marker_runs if (r["task_id"], r["input"]) not in seen]
            return {
                "reply": reply,
                "call_agents": [int(x) for x in (data.get("call_agents") or []) if str(x).lstrip("-").isdigit()],
                "dismiss_agents": [int(x) for x in (data.get("dismiss_agents") or []) if str(x).lstrip("-").isdigit()],
                "run_workflows": runs,
            }
        except Exception:
            pass
    # Fallback: model không trả JSON hợp lệ -> coi cả câu trả lời là lời Xanax nói, không gọi ai
    reply, marker_runs = _extract_trigger_markers(raw or "")
    return {"reply": reply, "call_agents": [], "dismiss_agents": [], "run_workflows": marker_runs}


async def _soul_and_live_context() -> str:
    """SOUL.md + snapshot DB real-time — cùng ngữ cảnh mà Xanax dùng ở nơi khác
    (xem api/websocket_training.py, README.md mục 'Live Context Injection').
    Không có phần này, Xanax trong phòng họp sẽ không biết gì về dự án/quyết
    định/lịch sử công ty — chỉ còn lại 1 cái tên suông."""
    from api.websocket_training import _read_soul, _build_live_context
    soul = _read_soul()
    live_context = await _build_live_context()
    return "\n\n".join(filter(None, [soul, live_context]))


# Các client đang mở phòng họp: meeting_id -> set hàm gửi. Dùng để đẩy thông báo
# phát sinh ngoài luồng chat (vd: quy trình chạy nền dừng lại chờ CEO duyệt) tới
# đúng cuộc họp, thay vì chỉ ghi vào DB rồi đợi CEO tự tải lại trang.
_meeting_clients: dict[int, set] = {}


async def push_meeting_notice(meeting_id: int, content: str) -> None:
    """Hiện ngay một thông báo hệ thống cho những ai đang mở cuộc họp này.

    Chỉ lo phần hiển thị realtime — bên gọi chịu trách nhiệm lưu vào lịch sử họp,
    để người vào sau vẫn đọc được.
    """
    for send in list(_meeting_clients.get(meeting_id) or ()):
        try:
            await send({"type": "system_notice", "content": content})
        except Exception:
            logger.debug("Client phòng họp %s đã ngắt, bỏ qua", meeting_id)


async def push_meeting_progress(meeting_id: int, payload: dict) -> None:
    """Phát tiến độ một lần chạy quy trình tới người đang mở cuộc họp.

    Cố tình KHÔNG lưu DB: tiến độ thay đổi liên tục, lưu hết sẽ rác lịch sử họp.
    Chỉ mốc cuối (xong/lỗi/huỷ) mới được bên gọi ghi lại thành tin nhắn.
    """
    for send in list(_meeting_clients.get(meeting_id) or ()):
        try:
            await send(payload)
        except Exception:
            logger.debug("Client phòng họp %s đã ngắt, bỏ qua tiến độ", meeting_id)


def wf_noun(kind: str, cap: bool = False) -> str:
    """'company' = quy trình (luồng phối hợp đầy đủ), 'automation' = tác vụ (một
    việc tự động đơn lẻ). Cột kind trong workflow_tasks chính là ranh giới này —
    xem wfNoun() ở dashboard/taskrunner.html, hai nơi phải gọi giống nhau."""
    noun = "tác vụ" if kind == "automation" else "quy trình"
    return noun.capitalize() if cap else noun


async def _build_workflow_roster_text() -> str:
    """Danh sách đang bật, TÁCH RIÊNG quy trình và tác vụ, kèm id.

    Xanax không có cách nào khác để biết task_id. Và nếu gộp chung một danh sách
    thì nó không phân biệt được "chạy quy trình X" với "chạy tác vụ X" — hai thứ
    hoàn toàn khác nhau và ở đây còn trùng tên nhau.
    """
    try:
        tasks = await list_workflow_tasks()
    except Exception:
        logger.exception("Không đọc được danh sách quy trình/tác vụ cho phòng họp")
        return ""
    active = [t for t in tasks if t.get("status") == "active"]
    if not active:
        return "(Chưa có quy trình/tác vụ nào đang bật)"

    def _section(kind: str, title: str) -> str:
        rows = [t for t in active if (t.get("kind") or "automation") == kind]
        if not rows:
            return f"{title}: (chưa có cái nào đang bật)"
        lines = [
            f"- id={t['id']} · {t['name']}" + (f" — {t['description']}" if t.get("description") else "")
            for t in rows
        ]
        return title + ":\n" + "\n".join(lines)

    return "\n\n".join([
        _section("company", "QUY TRÌNH (luồng phối hợp nhiều bước, thường gọi tới các tác vụ con)"),
        _section("automation", "TÁC VỤ (một việc tự động đơn lẻ)"),
    ])


async def _run_workflows_from_meeting(
    meeting_id: int, project_id: int | None, requests: list[dict],
) -> list[str]:
    """Chạy các quy trình Xanax vừa quyết định gọi, mỗi cái kèm chủ đề riêng.

    Chạy nền nên node chờ duyệt sẽ nhắn ngược lại đúng cuộc họp này
    (xem _notify_approval_needed trong api/websocket_workflow.py).

    Không cần tham số `ws`: thông báo đi qua `push_meeting_notice`, vốn phát cho
    MỌI client đang mở cuộc họp này chứ không riêng người vừa gõ lệnh.
    """
    from api.websocket_workflow import execute_workflow_headless

    notes: list[str] = []
    for item in requests:
        try:
            task_id = int(item.get("task_id") or 0)
        except (TypeError, ValueError):
            continue
        if not task_id:
            continue
        task = await get_workflow_task(task_id)
        if not task:
            notes.append(f"Không tìm thấy quy trình/tác vụ #{task_id}.")
            continue
        # Gọi đúng tên loại trong câu xác nhận: quy trình #14 và tác vụ #13 ở đây
        # trùng tên nhau, nếu chỉ nói tên thì chọn nhầm cũng không ai phát hiện ra.
        noun = wf_noun(task.get("kind") or "automation")
        if task.get("status") != "active":
            notes.append(f'{noun.capitalize()} "{task["name"]}" đang tắt — hãy bật trước khi chạy.')
            continue
        topic = str(item.get("input") or "").strip()
        asyncio.create_task(execute_workflow_headless(
            task_id, user_input=topic, triggered_by="meeting_chat",
            project_id=project_id, meeting_id=meeting_id,
        ))
        notes.append(
            f'Đã kích hoạt {noun} "{task["name"]}" (#{task_id})'
            + (f' với chủ đề: "{topic}".' if topic else " — không có chủ đề kèm theo.")
        )
    # Gửi dưới danh nghĩa HỆ THỐNG, không phải Xanax. Câu này do code sinh ra sau
    # khi quy trình đã thật sự khởi động, nên nó là bằng chứng máy móc. Để nó mang
    # tên Xanax thì nó trông y hệt lời model tự nói — mà model thì từng nói "đã
    # chạy rồi nha Papa" trong khi không chạy gì. Tách tên ra để nhìn là biết
    # dòng nào là sự thật máy ghi, dòng nào là lời nhân viên.
    for note in notes:
        await add_meeting_message(meeting_id, "Hệ thống", "system", note)
        await push_meeting_notice(meeting_id, note)
    return notes


async def _xanax_orchestrate(conv_context: list[dict], participant_ids: list[int]) -> dict:
    """Gọi LLM đóng vai Xanax để quyết định: tự trả lời gì, và có cần gọi
    trưởng phòng/nhân viên nào ra trả lời tiếp không. Luôn trả JSON."""
    base_context = await _soul_and_live_context()
    roster = await _build_roster_text()
    workflow_roster = await _build_workflow_roster_text()

    # Trạng thái hiện diện THẬT của phòng họp, nêu rõ theo tên để Xanax không bịa rằng có
    # nhân viên đang họp khi phòng thực chất trống (bug CEO báo: dropdown=0 nhưng Xanax bảo
    # nhân viên đang có mặt). Đây là nguồn sự thật duy nhất về ai đang ở trong phòng.
    present_agents = await get_agent_configs_by_ids(participant_ids)
    if present_agents:
        present_txt = ", ".join(f"{a['name']} (id={a['id']})" for a in present_agents)
    else:
        present_txt = "(KHÔNG có nhân viên nào — trong phòng chỉ có Xanax và Papa)"

    meeting_instructions = (
        "Bạn đang ở trong phòng họp AI của Papa (CEO), đóng vai trò trợ lý giám sát kiêm điều phối viên.\n\n"
        f"Danh sách phòng ban và nhân viên hiện có:\n{roster}\n\n"
        f"NHÂN VIÊN ĐANG THỰC SỰ CÓ MẶT trong phòng họp lúc này: {present_txt}\n"
        "Đây là sự thật về hiện diện. Khi Papa hỏi 'X có trong phòng họp không' → chỉ trả lời CÓ nếu X "
        "nằm trong danh sách đang có mặt ở trên; nếu không thì trả lời KHÔNG (và hỏi Papa có muốn mời họ "
        "vào không). TUYỆT ĐỐI không bịa rằng 1 nhân viên đang có mặt khi họ không có trong danh sách đó. "
        "Nếu trong \"reply\" bạn nói sẽ mời/gọi 1 nhân viên vào phòng, thì BẮT BUỘC phải đưa đúng id của "
        "họ vào \"call_agents\" — nếu để trống thì họ sẽ KHÔNG thực sự vào phòng, gây mâu thuẫn lời nói.\n\n"
        "Nhiệm vụ của bạn khi Papa nhắn tin trong phòng họp:\n"
        "1. Nếu Papa hỏi/thảo luận công việc liên quan đến 1 PHÒNG BAN cụ thể → gọi TRƯỞNG PHÒNG của "
        "phòng ban đó ra trả lời (không gọi cả phòng ban).\n"
        "2. Nếu Papa hỏi/thảo luận công việc liên quan đến 1 NHÂN VIÊN cụ thể → gọi đúng nhân viên đó ra.\n"
        "3. Nếu không liên quan đến ai cụ thể (chào hỏi, hỏi chung, điều phối) → tự bạn trả lời, KHÔNG gọi "
        "thêm ai.\n"
        "4. TUYỆT ĐỐI không gọi nhiều nhân viên không liên quan cùng lúc — gây tốn token vô ích.\n"
        "5. Nếu 1 nhân viên đang có mặt nhưng không còn liên quan đến chủ đề đang bàn, có thể cho họ rời "
        "phòng (dismiss_agents).\n"
        "6. QUAN TRỌNG: \"reply\" CHỈ được là lời của CHÍNH bạn (Xanax). TUYỆT ĐỐI không tự viết hộ, đoán "
        "trước, hay giả lập câu trả lời của bất kỳ nhân viên nào khác trong \"reply\" — kể cả khi bạn vừa "
        "quyết định gọi họ ra qua call_agents. Người đó sẽ tự trả lời ở lượt riêng của họ, ngay sau lời bạn. "
        "Không viết các dòng dạng \"[Tên nhân viên]: ...\" trong reply của bạn.\n\n"
        "7. Papa có thể yêu cầu CHẠY một quy trình hoặc một tác vụ. Đây là hai loại KHÁC NHAU, "
        "phải phân biệt rõ:\n"
        "   · QUY TRÌNH = luồng phối hợp nhiều bước, thường gọi các tác vụ con và có bước duyệt.\n"
        "   · TÁC VỤ = một việc tự động đơn lẻ, chỉ làm đúng phần việc của nó.\n"
        f"{workflow_roster}\n\n"
        "Quy tắc chọn, áp dụng THEO THỨ TỰ, dừng ngay khi có kết luận:\n"
        "   1. Papa nói rõ \"quy trình ...\" → CHỈ được chọn id trong nhóm QUY TRÌNH.\n"
        "   2. Papa nói rõ \"tác vụ ...\" → CHỈ được chọn id trong nhóm TÁC VỤ.\n"
        "   3. Papa nói chung chung mà phần 'Ghi chú từ các session training' trong identity của bạn "
        "đã có quy tắc phân biệt áp dụng được cho chính trường hợp này → ÁP DỤNG quy tắc đó và tự "
        "chọn, KHÔNG hỏi lại. Đây là điều Papa đã đích thân dạy bạn, hỏi lại thứ đã được dạy là làm "
        "phiền Papa. Khi chọn theo quy tắc đã học, nói rõ trong \"reply\" là bạn chọn loại nào và dựa "
        "vào đâu, để Papa sửa được nếu bạn hiểu sai.\n"
        "   4. Chỉ khi đã xét hết 1–3 mà vẫn không suy ra được (Papa nói chung chung, có cả quy trình "
        "lẫn tác vụ cùng tên, và không có quy tắc đã học nào áp dụng được) → hỏi lại Papa muốn chạy "
        "quy trình hay tác vụ, KHÔNG tự đoán bừa.\n"
        "   5. Nếu tên Papa nói khớp nhiều mục trong CÙNG một nhóm → đọc rõ từng lựa chọn kèm id và "
        "hỏi Papa chọn cái nào.\n"
        "Mỗi mục kèm \"input\" là chủ đề/nội dung Papa muốn — lấy từ chính lời Papa nói. Nếu Papa "
        "chưa nói rõ chủ đề thì ĐỪNG tự bịa: để \"run_workflows\" rỗng và hỏi lại Papa muốn chủ đề "
        "gì. TUYỆT ĐỐI không nói là đã chạy nếu bạn để \"run_workflows\" rỗng — nói và làm phải "
        "khớp nhau.\n\n"
        "Trả lời DUY NHẤT bằng JSON đúng format sau, không thêm bất kỳ text nào khác ngoài JSON:\n"
        '{"reply": "...", "call_agents": [id,...], "dismiss_agents": [id,...], '
        '"run_workflows": [{"task_id": N, "input": "chủ đề"}]}\n'
        '- "reply": lời Xanax nói trong phòng họp (luôn phải có, kể cả khi gọi nhân viên ra thì cũng nên '
        'có 1 câu ngắn dẫn dắt, vd "Để tôi mời trưởng phòng Marketing vào trao đổi.", KHÔNG viết tiếp lời '
        "của người khác)\n"
        '- "call_agents": danh sách id nhân viên cần gọi vào (mảng rỗng nếu không cần gọi ai)\n'
        '- "dismiss_agents": danh sách id nhân viên đang có mặt nhưng cần cho rời phòng (mảng rỗng nếu '
        "không có)\n"
        '- "run_workflows": danh sách quy trình cần kích hoạt ngay (mảng rỗng nếu Papa không yêu cầu '
        "chạy quy trình nào)"
    )
    system_prompt = "\n\n".join(filter(None, [base_context, meeting_instructions]))
    raw = await hermes.complete_with_context([{"role": "system", "content": system_prompt}] + conv_context)
    return _parse_orchestrator_json(raw)


async def _sync_participants(ws: WebSocket, meeting_id: int, participant_ids: list[int]) -> None:
    await update_meeting(meeting_id, participants_json=json.dumps(participant_ids))
    agents = await get_agent_configs_by_ids(participant_ids)
    await ws.send_json({
        "type": "participants_updated",
        "participants": [
            {"id": a["id"], "name": a["name"], "role": a["role"], "color": a["avatar_color"],
             "department": a.get("department_name")} for a in agents
        ],
    })


async def _generate_draft_minutes(meeting_id: int) -> str:
    """Xanax tự tổng hợp toàn bộ nội dung họp thành biên bản nháp — CEO xem/sửa rồi
    mới chốt qua endpoint finalize (POST /meetings/{id}/finalize)."""
    messages = await get_meeting_messages(meeting_id)
    if not messages:
        return ""
    transcript = "\n".join(f"{m['sender']}: {m['content']}" for m in messages)
    base_context = await _soul_and_live_context()
    minutes_instructions = (
        "Bạn là Xanax. Hãy tổng hợp nội dung cuộc họp dưới đây thành 1 biên bản cuộc họp ngắn gọn, "
        "rõ ràng bằng tiếng Việt, gồm: (1) Nội dung chính đã trao đổi, (2) Các quyết định/kết luận, "
        "(3) Việc cần làm tiếp theo và nhân viên/phòng ban phụ trách (nếu có). Chỉ trả về nội dung biên "
        "bản, không thêm lời dẫn."
    )
    system_prompt = "\n\n".join(filter(None, [base_context, minutes_instructions]))
    draft = await hermes.complete_with_context([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript},
    ])
    return draft.strip()


@router.websocket("/ws/meeting/{meeting_id}")
async def meeting_ws(ws: WebSocket, meeting_id: int):
    await ws.accept()

    meeting = await get_meeting(meeting_id)
    if not meeting:
        await ws.send_json({"type": "error", "message": "Meeting not found"})
        await ws.close()
        return

    # Đăng ký để nhận thông báo phát sinh ngoài luồng chat (xem push_meeting_notice)
    _meeting_clients.setdefault(meeting_id, set()).add(ws.send_json)

    # Send history
    history = await get_meeting_messages(meeting_id)
    await ws.send_json({"type": "history", "messages": history})

    # Track conversation context for LLM
    conv_context: list[dict] = [
        {"role": msg["sender_type"] if msg["sender_type"] == "user" else "assistant",
         "content": f"[{msg['sender']}]: {msg['content']}"}
        for msg in history
    ]
    # Nhân viên đang "giữ lượt" trao đổi trực tiếp với CEO — Papa hỏi tiếp không cần
    # tag lại tên vẫn tiếp tục do đúng người này trả lời, không bị Xanax giành lại.
    active_agent_id: int | None = None

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "user_message":
                content = data.get("content", "").strip()
                if not content:
                    continue

                await add_meeting_message(meeting_id, "user", "user", content)
                await ws.send_json({"type": "user_message", "sender": "user", "content": content})
                conv_context.append({"role": "user", "content": content})

                meeting_now = await get_meeting(meeting_id)
                participant_ids: list[int] = json.loads(meeting_now.get("participants_json", "[]"))
                all_agents = await list_agent_configs()

                target_ids: list[int] = data.get("targets") or []
                if not target_ids:
                    target_ids = _extract_mentions(content, all_agents)
                addresses_xanax = bool(re.search(r"\bxanax\b", content, re.IGNORECASE))
                is_workflow_command = _is_workflow_command(content)
                # Không có @mention nhưng CEO nhắc thẳng tên nhân viên ĐANG có mặt -> vẫn cho
                # đúng người đó trả lời (xem _extract_named_agents), khớp trực giác "gọi tên
                # ai đang họp thì người đó lên tiếng". Phòng trống -> không ai được nhắc thành
                # target -> câu hỏi mặc định về Xanax điều phối.
                #
                # QUAN TRỌNG: bỏ qua bước này nếu CEO đã nhắc/tag "Xanax" trong CHÍNH câu này —
                # nếu không, câu như "@Xanax tại sao prozac không có ..." sẽ bị nhánh này vồ lấy
                # vì "prozac" khớp tên 1 nhân viên đang có mặt, khiến Prozac trả lời thay vì
                # Xanax dù CEO đã tag thẳng Xanax. Nhắc tên nhân viên khác chỉ để HỎI Xanax VỀ
                # người đó, không phải đang gọi người đó ra trả lời.
                # Lệnh chạy quy trình cũng không được để nhánh này vồ: "chạy quy trình lên bài
                # của Prozac" có nhắc tên nhân viên đang họp, nhưng người chạy được quy trình
                # chỉ có Xanax — để Prozac trả lời là chắc chắn ra kết quả bịa.
                if not target_ids and not addresses_xanax and not is_workflow_command:
                    target_ids = _extract_named_agents(content, all_agents, participant_ids)

                # Lệnh đuổi tường minh ("đuổi X", "kick X"...) áp dụng ngay, không chờ Xanax
                # quyết định — xem docstring _extract_dismiss_targets. Phải xử lý TRƯỚC khi xét
                # active_agent_id, nếu không tin nhắn sẽ bị route thẳng tới đúng người đang bị đuổi.
                current_participants = [a for a in all_agents if a["id"] in participant_ids]
                forced_dismiss_ids = _extract_dismiss_targets(content, current_participants)
                if forced_dismiss_ids:
                    participant_ids = [aid for aid in participant_ids if aid not in forced_dismiss_ids]
                    await _sync_participants(ws, meeting_id, participant_ids)
                    if active_agent_id in forced_dismiss_ids:
                        active_agent_id = None
                    # "prozac ra khỏi phòng" vừa khớp lệnh đuổi vừa khớp tên -> đừng để nhánh
                    # target_ids bên dưới gọi lại đúng người vừa bị đuổi vào trả lời.
                    target_ids = [aid for aid in target_ids if aid not in forced_dismiss_ids]

                # Lệnh mời/gọi/đưa ai đó VÀO phòng ("đưa trưởng phòng marketing vào đây"...) áp
                # dụng ngay: thêm thật người đó vào participant_ids (dropdown cập nhật đúng),
                # KHÔNG phụ thuộc call_agents của Xanax (hay bị rỗng dù Xanax nói "đã mời").
                #
                # CHỈ thêm vào phòng — KHÔNG gộp vào target_ids/call ngay người đó trả lời. Quy
                # tắc CEO đặt ra: nhân viên chỉ được trả lời khi (1) ĐÃ có mặt trong phòng VÀ
                # (2) được nhắc/tag tên. Người vừa được mời vào ở CHÍNH câu này chưa thoả điều
                # kiện (1) tại thời điểm gõ câu, nên lượt trả lời của câu này vẫn thuộc về Xanax
                # (đi tiếp xuống nhánh else bên dưới) — Xanax tự xác nhận đã mời, không cần người
                # mới vào phải lên tiếng ngay. Từng bị bug: gộp vào target_ids khiến agent vừa
                # được mời bị gọi trả lời ngay trong lượt này, và do lịch sử hội thoại có sẵn câu
                # "[Xanax]: Dạ, con mời ... vào phòng họp ngay ạ." nên model của agent đó bắt
                # chước lặp lại y hệt câu này rồi mới tự giới thiệu, nghe như đang đóng vai Xanax.
                if not forced_dismiss_ids:
                    departments = await list_departments()
                    summon_ids = _extract_summon_targets(content, all_agents, departments)
                    if summon_ids:
                        valid_ids = {a["id"] for a in all_agents}
                        new_ids = [i for i in summon_ids if i in valid_ids and i not in participant_ids]
                        if new_ids:
                            participant_ids = participant_ids + new_ids
                            await _sync_participants(ws, meeting_id, participant_ids)

                if target_ids:
                    # CEO đã chỉ đích danh (qua @mention) -> gọi thẳng, bỏ qua bước Xanax cân nhắc
                    valid_ids = {a["id"] for a in all_agents}
                    call_ids = [aid for aid in target_ids if aid in valid_ids]
                    new_ids = [aid for aid in call_ids if aid not in participant_ids]
                    if new_ids:
                        participant_ids = participant_ids + new_ids
                        await _sync_participants(ws, meeting_id, participant_ids)
                    if call_ids:
                        active_agent_id = call_ids[-1]
                elif (not addresses_xanax and active_agent_id and active_agent_id in participant_ids
                      and not is_workflow_command):
                    # CEO đang tiếp tục trao đổi với nhân viên đã gọi ra trước đó, không tag lại tên
                    # -> vẫn đúng người này trả lời tiếp, không cần Xanax cân nhắc lại (đỡ tốn token).
                    # Trừ lệnh chạy quy trình: chỉ Xanax kích hoạt được, xem _is_workflow_command.
                    call_ids = [active_agent_id]
                else:
                    # Hiện bong bóng "đang xử lý" của Xanax NGAY khi bắt đầu cân nhắc điều phối
                    # (bước _xanax_orchestrate là 1 lần gọi LLM có độ trễ) để CEO thấy Xanax
                    # đang làm việc giống các nhân viên khác, thay vì im lặng rồi hiện đáp án.
                    await ws.send_json({"type": "agent_thinking", "agent": XANAX_NAME,
                                         "agent_id": XANAX_AGENT_ID, "color": XANAX_AVATAR})
                    decision = await _xanax_orchestrate(conv_context, participant_ids)
                    reply = _strip_hallucinated_continuation(decision["reply"], [a["name"] for a in all_agents])
                    reply = _guard_false_run_claim(
                        reply, decision.get("run_workflows") or [],
                        asked_to_run=is_workflow_command,
                    )
                    if reply:
                        await ws.send_json({"type": "agent_chunk", "agent": XANAX_NAME,
                                             "agent_id": XANAX_AGENT_ID, "color": XANAX_AVATAR, "content": reply})
                        await ws.send_json({"type": "agent_done", "agent": XANAX_NAME, "agent_id": XANAX_AGENT_ID})
                        await add_meeting_message(meeting_id, XANAX_NAME, "agent", reply)
                        conv_context.append({"role": "assistant", "content": f"[{XANAX_NAME}]: {reply}"})
                    else:
                        # Xanax không tự nói gì (chỉ mời nhân viên khác ra) -> gỡ bong bóng "đang
                        # xử lý" để không kẹt lại trạng thái thinking mãi trên UI.
                        await ws.send_json({"type": "agent_cancelled", "agent_id": XANAX_AGENT_ID})

                    if decision.get("run_workflows"):
                        meeting_row = await get_meeting(meeting_id)
                        notes = await _run_workflows_from_meeting(
                            meeting_id, (meeting_row or {}).get("project_id"),
                            decision["run_workflows"],
                        )
                        for note in notes:
                            conv_context.append({"role": "assistant", "content": f"[Hệ thống]: {note}"})

                    valid_ids = {a["id"] for a in all_agents}
                    dismiss_ids = {aid for aid in decision["dismiss_agents"] if aid in participant_ids}
                    call_ids = [aid for aid in decision["call_agents"] if aid in valid_ids]
                    new_ids = [aid for aid in call_ids if aid not in participant_ids]

                    if dismiss_ids or new_ids:
                        participant_ids = [aid for aid in participant_ids if aid not in dismiss_ids] + new_ids
                        await _sync_participants(ws, meeting_id, participant_ids)
                    active_agent_id = call_ids[0] if call_ids else None

                for agent in (await get_agent_configs_by_ids(call_ids) if call_ids else []):
                    response = await _stream_agent(ws, agent, conv_context)
                    if response:
                        # Chỉ dọn phần lưu lại/đưa vào context tương lai — chunk đã stream ra
                        # UI ở live turn này không thể thu hồi, nhưng tránh lỗi lặp lại ở lượt sau.
                        clean_response = _strip_hallucinated_continuation(response, [a["name"] for a in all_agents])
                        await add_meeting_message(meeting_id, agent["name"], "agent", clean_response)
                        conv_context.append({
                            "role": "assistant",
                            "content": f"[{agent['name']}]: {clean_response}",
                        })

            elif msg_type == "end_meeting":
                from datetime import datetime, timezone
                await update_meeting(
                    meeting_id,
                    status="ended",
                    ended_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                )
                draft = await _generate_draft_minutes(meeting_id)
                if draft:
                    await update_meeting(meeting_id, draft_minutes=draft)
                await ws.send_json({"type": "meeting_ended", "draft_minutes": draft})
                break

    except WebSocketDisconnect:
        logger.info("Meeting %d client disconnected", meeting_id)
    except Exception:
        logger.exception("Meeting %d WS error", meeting_id)
    finally:
        clients = _meeting_clients.get(meeting_id)
        if clients:
            clients.discard(ws.send_json)
            if not clients:
                _meeting_clients.pop(meeting_id, None)
