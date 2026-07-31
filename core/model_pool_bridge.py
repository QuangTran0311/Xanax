"""
Model Pool Bridge — OpenAI-compatible caller for the model pool.

Supports any OpenAI-compatible provider (9router, OpenAI, Anthropic via proxy, Groq, etc.).
Tracks usage per model per day and enforces daily request/token limits.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from hub.database import (
    get_model_pool_entry,
    get_model_usage_today,
    record_model_usage,
    record_model_usage_hourly,
    record_model_call_log,
)

logger = logging.getLogger("xanax.model_pool_bridge")


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
) -> AsyncIterator[str]:
    """
    Stream a completion from the model pool entry identified by model_pool_id.

    Yields text chunks. Raises LimitExceededError if daily limits are exceeded.
    Tracks usage (request count + tokens) automatically.
    """
    entry = await get_model_pool_entry(model_pool_id)
    if not entry:
        raise ValueError(f"Model pool entry {model_pool_id} not found")
    if not entry.get("enabled"):
        raise ValueError(f"Model '{entry['name']}' is disabled")

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
) -> AsyncIterator[str]:
    """Thử lần lượt các model theo đúng thứ tự ưu tiên đã cấu hình cho nhân viên
    (tab Nhân sự). Nếu 1 model lỗi trước khi có nội dung đầu tiên (hết quota,
    lỗi kết nối, bị vô hiệu hoá...) thì tự động chuyển sang model kế tiếp trong
    danh sách. Đã bắt đầu nhận nội dung thì không đổi model giữa chừng.
    """
    last_err: Exception | None = None
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

        pid = entry["id"]
        gen = stream_from_pool(pid, messages, tools)
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

    tool_calls = []
    tool_messages = []
    for index in sorted(tool_call_parts):
        call = tool_call_parts[index]
        call["id"] = call["id"] or f"tool_call_{_tool_round}_{index}"
        name = call["function"]["name"]
        raw_args = call["function"]["arguments"] or "{}"
        tool_calls.append(call)
        try:
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
