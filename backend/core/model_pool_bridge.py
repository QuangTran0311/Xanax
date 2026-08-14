"""
Model Pool Bridge — OpenAI-compatible caller for the model pool.

Supports any OpenAI-compatible provider (9router, OpenAI, Anthropic via proxy, Groq, etc.).
Tracks usage per model per day and enforces daily request/token limits.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Literal

import httpx

from hub.database import (
    get_model_pool_entry,
    get_model_usage_today,
    record_model_usage,
    record_model_usage_hourly,
    record_model_call_log,
)

logger = logging.getLogger("xanax.model_pool_bridge")

# Các api_style chạy bằng tiến trình CLI (gói thuê bao) thay vì HTTP tới provider.
# Entry kiểu này không dùng base_url/api_key — xác thực nằm trong thư mục tài
# khoản của CLI (cột cli_config_dir), nên không có key nào để rò rỉ.
CLI_API_STYLES = ("claude_cli", "codex_cli")

# Chỉ hai kiểu này truyền được tools[] theo JSON Schema xuống model (xem
# stream_from_pool). Kỹ năng loại 'api'/'mcp'/'builtin' của nhân viên đều thành
# tool, nên nhân viên nào sống bằng kỹ năng đó thì BẮT BUỘC phải chạy trên một
# trong hai kiểu này.
TOOL_CAPABLE_API_STYLES = ("openai_compat", "openai_native")


def _can_call_tools(entry: dict, skill_ids: list[int] | None) -> bool:
    """Model này có thật sự gọi được công cụ của nhân viên không.

    `claude_cli` gọi được nhờ cầu nối MCP (mcp_servers/xanax_skills.py), nhưng
    chỉ khi biết nhân viên có kỹ năng nào — không có skill_ids thì không dựng
    được cấu hình MCP. `codex_cli` chưa có cầu nối nên vẫn nằm ngoài.
    """
    api_style = entry.get("api_style") or "openai_compat"
    if api_style in TOOL_CAPABLE_API_STYLES:
        return True
    return api_style == "claude_cli" and bool(skill_ids)


class LimitExceededError(Exception):
    """Raised when a model's daily limit has been reached."""


async def _check_daily_limits(entry: dict) -> None:
    """Kiểm tra hạn mức ngày của một model pool entry."""
    today = await get_model_usage_today(entry["id"])
    max_req = entry.get("max_requests_per_day", 0)
    max_tok = entry.get("max_tokens_per_day", 0)
    if max_req and today["request_count"] >= max_req:
        raise LimitExceededError(
            f"Model '{entry['name']}' đã đạt giới hạn {max_req} request/ngày"
        )
    if max_tok and (today["tokens_input"] + today["tokens_output"]) >= max_tok:
        raise LimitExceededError(
            f"Model '{entry['name']}' đã đạt giới hạn {max_tok} token/ngày"
        )


async def iter_usable_pool_entries(
    model_pool_ids: list[int],
) -> AsyncIterator[dict]:
    """Duyệt model theo đúng thứ tự ưu tiên của nhân viên.

    Bỏ qua entry đã xoá, đã tắt, dữ liệu id cũ không hợp lệ hoặc đã chạm hạn
    mức ngày. Danh sách rỗng kết thúc bình thường để caller tự quyết định cách
    thông báo cho người dùng.
    """
    for raw_id in model_pool_ids or []:
        try:
            model_pool_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        entry = await get_model_pool_entry(model_pool_id)
        if not entry or not entry.get("enabled"):
            continue
        try:
            await _check_daily_limits(entry)
        except LimitExceededError as exc:
            logger.info("Bỏ qua model pool %s vì đã chạm hạn mức ngày: %s", model_pool_id, exc)
            continue
        yield entry


async def stream_from_pool(
    model_pool_id: int,
    messages: list[dict],
    tools: list[dict] | None = None,
    skill_ids: list[int] | None = None,
    tool_filter: dict[int, list[str]] | None = None,
    *,
    usage_policy: Literal["production", "experiment"] = "production",
    usage_out: dict | None = None,
) -> AsyncIterator[str]:
    """
    Stream a completion from the model pool entry identified by model_pool_id.

    Yields text chunks. Raises LimitExceededError if daily limits are exceeded.
    Mặc định kiểm hạn mức và ghi usage như trước. ``usage_policy="experiment"``
    chỉ bỏ hai side effect đó; mọi nhánh provider/CLI và cách stream vẫn dùng
    nguyên cơ chế này. ``usage_out`` nhận bản sao số token cuối cùng để runner
    thí nghiệm lưu vào bảng riêng.
    """
    if usage_policy not in ("production", "experiment"):
        raise ValueError(f"usage_policy không hợp lệ: {usage_policy}")
    entry = await get_model_pool_entry(model_pool_id)
    if not entry:
        raise ValueError(f"Model pool entry {model_pool_id} not found")
    if not entry.get("enabled"):
        raise ValueError(f"Model '{entry['name']}' is disabled")

    if usage_policy == "production":
        await _check_daily_limits(entry)

    api_style = entry.get("api_style") or "openai_compat"
    base_url = entry["base_url"].rstrip("/")
    api_key  = entry["api_key"]
    model_id = entry["model_id"]

    tokens_in  = _estimate_tokens(messages)
    usage_state = {"tokens_in": tokens_in, "tokens_out": 0, "tokens_cache": 0}
    chunks: list[str] = []

    try:
        if api_style in ("openai_compat", "openai_native"):
            agen = _stream_openai(base_url, api_key, model_id, messages, usage_state, tools)
        elif api_style in CLI_API_STYLES:
            if tools and not (api_style == "claude_cli" and skill_ids):
                logger.warning(
                    "Model %s chạy qua CLI; CLI có bộ công cụ riêng nên không nhận tools[] theo JSON Schema. Bỏ qua tools.",
                    model_id,
                )
            agen = _stream_cli(api_style, model_id, messages, usage_state, entry, skill_ids,
                               tool_filter)
        elif api_style == "anthropic_native":
            if tools:
                logger.warning(
                    "Model %s uses anthropic_native; built-in tool calling is not supported yet. Continuing without tools.",
                    model_id,
                )
            agen = _stream_anthropic(base_url, api_key, model_id, messages, usage_state)
        elif api_style == "gemini_native":
            if tools:
                logger.warning(
                    "Model %s uses gemini_native; built-in tool calling is not supported yet. Continuing without tools.",
                    model_id,
                )
            agen = _stream_gemini(base_url, api_key, model_id, messages, usage_state)
        else:
            raise ValueError(f"api_style không hợp lệ: {api_style}")
        async for delta in agen:
            chunks.append(delta)
            yield delta
    except LimitExceededError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error("Model pool HTTP %s for model %s: %s", e.response.status_code, model_id, e)
        raise
    except Exception:
        logger.exception("Model pool stream failed for model %s", model_id)
        raise
    finally:
        if usage_out is not None:
            usage_out.clear()
            usage_out.update(usage_state)
        if usage_policy == "production":
            try:
                await record_model_usage(model_pool_id, usage_state["tokens_in"], usage_state["tokens_out"], usage_state["tokens_cache"])
                await record_model_usage_hourly(model_pool_id, usage_state["tokens_in"], usage_state["tokens_out"], usage_state["tokens_cache"])
                await record_model_call_log(model_pool_id, usage_state["tokens_in"], usage_state["tokens_out"], usage_state["tokens_cache"])
            except Exception:
                logger.exception("Failed to record model usage")


_IMAGE_MODEL_KEYWORDS = ("dall-e", "dall_e", "image-gen", "imagen", "flux", "ideogram", "midjourney", "sdxl", "stable-diffusion")


def _is_image_model(model_id: str) -> bool:
    lower = model_id.lower()
    return any(kw in lower for kw in _IMAGE_MODEL_KEYWORDS)


async def stream_from_agent_models(
    model_pool_ids: list[int],
    messages: list[dict],
    tools: list[dict] | None = None,
    skill_ids: list[int] | None = None,
    tool_filter: dict[int, list[str]] | None = None,
) -> AsyncIterator[str]:
    """Thử lần lượt các model theo đúng thứ tự ưu tiên đã cấu hình cho nhân viên
    (tab Nhân sự). Nếu 1 model lỗi trước khi có nội dung đầu tiên (hết quota,
    lỗi kết nối, bị vô hiệu hoá...) thì tự động chuyển sang model kế tiếp trong
    danh sách. Đã bắt đầu nhận nội dung thì không đổi model giữa chừng.

    Khi có `tools`, model không gọi được công cụ sẽ bị BỎ QUA chứ không phải
    dùng-rồi-lặng-lẽ-bỏ-tools. Sự cố thật: nhân viên đăng Facebook (kỹ năng loại
    'api') được gán toàn model CLI; tool bị bỏ nên không có request nào tới
    Facebook, nhưng nhân viên vẫn sinh ra chữ và bước quy trình báo "Đã chạy
    xong". Người dùng chỉ phát hiện khi mở fanpage ra xem.
    """
    last_err: Exception | None = None
    skipped_no_tools: list[str] = []
    for raw_id in model_pool_ids or []:
        try:
            entry = await anext(iter_usable_pool_entries([raw_id]), None)
        except Exception as exc:
            logger.warning(
                "Không thể kiểm tra model pool %s, chuyển sang model kế tiếp: %s",
                raw_id,
                exc,
            )
            last_err = exc
            continue
        if entry is None:
            continue

        if tools and not _can_call_tools(entry, skill_ids):
            skipped_no_tools.append(f"{entry['name']} ({entry.get('api_style')})")
            logger.info(
                "Bỏ qua model %s vì nhân viên cần gọi công cụ mà kiểu kết nối này không hỗ trợ",
                entry["name"],
            )
            continue

        pid = entry["id"]
        gen = stream_from_pool(pid, messages, tools, skill_ids, tool_filter)
        try:
            first_chunk = await gen.__anext__()
        except StopAsyncIteration:
            continue
        except Exception as exc:
            logger.warning("Model pool %s lỗi, chuyển sang model kế tiếp trong danh sách ưu tiên: %s", pid, exc)
            last_err = exc
            continue
        yield first_chunk
        async for chunk in gen:
            yield chunk
        return
    if skipped_no_tools:
        raise RuntimeError(
            "Nhân viên này có kỹ năng cần gọi công cụ (loại 'api'/'mcp'), nhưng mọi model "
            "được gán đều không hỗ trợ tool-calling: " + ", ".join(skipped_no_tools)
            + ". Hãy gán thêm cho nhân viên này một model kiểu 'Qua Subscription' hoặc "
            "'Qua Provider API chính chủ' (OpenAI-compatible). Model chạy qua CLI gói thuê "
            "bao không gọi được công cụ nên không làm được việc này."
        )
    raise last_err or RuntimeError("Không có model nào trong danh sách ưu tiên của nhân viên khả dụng")


async def _stream_openai(
    base_url: str,
    api_key: str,
    model_id: str,
    messages: list[dict],
    usage_state: dict,
    tools: list[dict] | None = None,
    _tool_round: int = 0,
) -> AsyncIterator[str]:
    """Stream response from OpenAI-compatible API."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model_id, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    tool_call_parts: dict[int, dict] = {}
    finish_reason: str | None = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers=headers,
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
                    # Try to read usage from final chunk (some providers send it)
                    usage = chunk_data.get("usage") or {}
                    if usage:
                        usage_state["tokens_in"]  = usage.get("prompt_tokens", usage_state["tokens_in"])
                        usage_state["tokens_out"] = usage.get("completion_tokens", usage_state["tokens_out"])
                        cache_details = usage.get("prompt_tokens_details") or {}
                        usage_state["tokens_cache"] = cache_details.get("cached_tokens", usage.get("cached_tokens", usage_state["tokens_cache"]))
                    choice = chunk_data.get("choices", [{}])[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        usage_state["tokens_out"] += _estimate_tokens_text(content)
                        yield content
                    for fragment in delta.get("tool_calls") or []:
                        index = int(fragment.get("index", 0))
                        current = tool_call_parts.setdefault(index, {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        })
                        if fragment.get("id"):
                            current["id"] = fragment["id"]
                        function = fragment.get("function") or {}
                        if function.get("name"):
                            current["function"]["name"] += function["name"]
                        if function.get("arguments"):
                            current["function"]["arguments"] += function["arguments"]
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

    if not tool_call_parts:
        return

    from core.hermes.tool_registry import tool_registry
    from core.skill_tools import record_tool_invocation

    # Tên tool thật sự được cấp cho lượt này, suy từ chính schema đã gửi lên model.
    granted = {
        (t.get("function") or {}).get("name") or t.get("name")
        for t in (tools or [])
    }
    tool_calls = []
    tool_messages = []
    for index in sorted(tool_call_parts):
        call = tool_call_parts[index]
        call["id"] = call["id"] or f"tool_call_{_tool_round}_{index}"
        name = call["function"]["name"]
        raw_args = call["function"]["arguments"] or "{}"
        tool_calls.append(call)
        # Ghi sổ TRƯỚC khi chạy: một lời gọi có xảy ra là sự thật, bất kể nó
        # thành công hay ném lỗi. Ghi sau khối try thì lần gọi hỏng sẽ biến mất
        # khỏi sổ và bước lại trông như "chưa hề gọi".
        record_tool_invocation(name)
        try:
            # Chỉ cho gọi đúng những tool đã cấp cho lượt này. Registry là kho
            # CHUNG của cả hệ thống, nên không chặn ở đây thì model nêu tên tool
            # nào cũng chạy được — kể cả tool của nhân viên khác, kể cả tool đăng
            # bài thật trong một buổi dạy chỉ định cho phép cắt ảnh.
            if name not in granted:
                raise PermissionError(
                    f"Lượt này không được cấp công cụ '{name}'. "
                    f"Chỉ có: {', '.join(sorted(granted)) or '(không có)'}"
                )
            args = json.loads(raw_args)
            if not isinstance(args, dict):
                raise ValueError("tool arguments must be a JSON object")
            result = await tool_registry.call(name, args)
            content = json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning("Tool call %s failed: %s", name or "<missing>", exc)
            content = json.dumps(
                {"success": False, "error": str(exc), "tool": name},
                ensure_ascii=False,
            )
        tool_messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "name": name,
            "content": content,
        })

    follow_up_messages = [
        *messages,
        {"role": "assistant", "content": None, "tool_calls": tool_calls},
        *tool_messages,
    ]
    next_tools = tools if _tool_round + 1 < 3 else None
    async for text in _stream_openai(
        base_url,
        api_key,
        model_id,
        follow_up_messages,
        usage_state,
        next_tools,
        _tool_round + 1,
    ):
        yield text


async def _stream_cli(
    api_style: str,
    model_id: str,
    messages: list[dict],
    usage_state: dict,
    entry: dict,
    skill_ids: list[int] | None = None,
    tool_filter: dict[int, list[str]] | None = None,
) -> AsyncIterator[str]:
    """Stream qua CLI của gói thuê bao — không đụng tới provider bên thứ 3.

    CLI tự báo số token thật trong sự kiện kết thúc, nên `usage_state` được ghi
    đè bằng số đo thật thay vì ước lượng theo ký tự ở `stream_from_pool`.
    """
    from core.cli_provider import stream_claude_cli, stream_codex_cli

    config_dir = (entry.get("cli_config_dir") or "").strip() or None

    if api_style == "claude_cli":
        # Kỹ năng của nhân viên đi xuống qua MCP (xem mcp_servers/xanax_skills.py).
        async for text in stream_claude_cli(
            model_id, messages, usage_state, config_dir, skill_ids=skill_ids,
            tool_filter=tool_filter,
        ):
            yield text
        return

    async for text in stream_codex_cli(model_id, messages, usage_state, config_dir):
        yield text


async def _stream_anthropic(
    base_url: str,
    api_key: str,
    model_id: str,
    messages: list[dict],
    usage_state: dict,
) -> AsyncIterator[str]:
    """Stream response from Anthropic Messages API."""
    system_text = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    chat_messages = [m for m in messages if m.get("role") != "system"]
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {"model": model_id, "max_tokens": 4096, "messages": chat_messages, "stream": True}
    if system_text:
        payload["system"] = system_text

    current_event = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{base_url}/v1/messages", headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    continue
                if not line.startswith("data: "):
                    continue
                try:
                    chunk = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if current_event == "content_block_delta":
                    text = chunk.get("delta", {}).get("text", "")
                    if text:
                        usage_state["tokens_out"] += _estimate_tokens_text(text)
                        yield text
                elif current_event == "message_start":
                    usage = chunk.get("message", {}).get("usage", {})
                    usage_state["tokens_in"] = usage.get("input_tokens", usage_state["tokens_in"])
                    usage_state["tokens_cache"] = (
                        usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                    )
                elif current_event == "message_delta":
                    usage = chunk.get("usage", {})
                    if "output_tokens" in usage:
                        usage_state["tokens_out"] = usage["output_tokens"]


async def _stream_gemini(
    base_url: str,
    api_key: str,
    model_id: str,
    messages: list[dict],
    usage_state: dict,
) -> AsyncIterator[str]:
    """Stream response from Google Gemini API."""
    contents, system_parts = [], []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m["content"])
            continue
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
    payload = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

    url = f"{base_url}/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers={"content-type": "application/json"}, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    chunk = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                candidates = chunk.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    if text:
                        usage_state["tokens_out"] += _estimate_tokens_text(text)
                        yield text
                usage_meta = chunk.get("usageMetadata")
                if usage_meta:
                    usage_state["tokens_in"] = usage_meta.get("promptTokenCount", usage_state["tokens_in"])
                    usage_state["tokens_out"] = usage_meta.get("candidatesTokenCount", usage_state["tokens_out"])
                    usage_state["tokens_cache"] = usage_meta.get("cachedContentTokenCount", usage_state["tokens_cache"])


async def test_model_connection(model_pool_id: int) -> dict:
    """Send a minimal request to verify the model endpoint is reachable."""
    entry = await get_model_pool_entry(model_pool_id)
    if not entry:
        return {"ok": False, "error": "Entry not found"}

    base_url = entry["base_url"].rstrip("/")
    api_key  = entry["api_key"]
    model_id = entry["model_id"]
    headers  = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    api_style_pre = entry.get("api_style") or "openai_compat"
    if api_style_pre in CLI_API_STYLES:
        # Không có HTTP nào để thử — chạy thẳng CLI một câu ngắn. Đây cũng là
        # phép kiểm "gói còn đăng nhập không", vì CLI hết phiên sẽ báo lỗi ở đây.
        probe = [{"role": "user", "content": "Trả lời đúng 2 từ: đang hoạt động"}]
        usage_state = {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0}
        try:
            reply = "".join(
                [chunk async for chunk in _stream_cli(api_style_pre, model_id, probe, usage_state, entry)]
            )
            if not reply.strip():
                return {"ok": False, "error": "CLI chạy xong nhưng không trả về chữ nào"}
            return {"ok": True, "reply": reply.strip()[:100]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            api_style = entry.get("api_style") or "openai_compat"
            if api_style == "anthropic_native":
                headers = {"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}
                payload = {"model": model_id, "max_tokens": 5, "messages": [{"role": "user", "content": "Hi"}]}
                r = await client.post(f"{base_url}/v1/messages", headers=headers, json=payload)
                r.raise_for_status()
                reply = (r.json().get("content") or [{}])[0].get("text", "")
                return {"ok": True, "reply": reply[:100]}
            elif api_style == "gemini_native":
                url = f"{base_url}/v1beta/models/{model_id}:generateContent?key={api_key}"
                payload = {"contents": [{"role": "user", "parts": [{"text": "Hi"}]}]}
                r = await client.post(url, headers={"content-type": "application/json"}, json=payload)
                r.raise_for_status()
                data = r.json()
                parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [{}])
                reply = parts[0].get("text", "") if parts else ""
                return {"ok": True, "reply": reply[:100]}
            elif _is_image_model(model_id):
                # Image generation models: test via /images/generations with tiny 256x256
                from core.image_gen import _build_image_url
                payload = {
                    "model": model_id,
                    "prompt": "a white circle on black background",
                    "n": 1,
                }
                r = await client.post(
                    _build_image_url(base_url),
                    headers=headers,
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
                item = (data.get("data") or [{}])[0]
                has_image = bool(item.get("b64_json") or item.get("url"))
                return {"ok": True, "reply": "Image generation OK" if has_image else "Responded but no image data"}
            else:
                payload = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                    "stream": False,
                }
                r = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                r.raise_for_status()
                reply = (
                    r.json().get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {"ok": True, "reply": reply[:100]}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def _estimate_tokens(messages: list[dict]) -> int:
    """Very rough token estimate: 1 token ≈ 4 chars."""
    total = sum(len(m.get("content", "")) for m in messages)
    return max(1, total // 4)


def _estimate_tokens_text(text: str) -> int:
    return max(0, len(text) // 4)
