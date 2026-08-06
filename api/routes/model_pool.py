"""API Routes — Model Pool CRUD, stats, and connection test."""
import logging

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from hub.database import (
    create_model_pool_entry, list_model_pool, get_model_pool_entry,
    update_model_pool_entry, delete_model_pool_entry,
    get_model_usage_today, get_top_models_usage, get_model_usage_range,
    get_model_usage_hourly_range, get_model_call_log_for_date,
)
from core.xlsx_report import build_cost_report_xlsx

router = APIRouter()
logger = logging.getLogger("xanax.routes.model_pool")

_VN_OFFSET_HOURS = 7  # Việt Nam không có DST — offset cố định quanh năm


def _local_now():
    """Giờ hiện tại theo giờ Việt Nam (UTC+7) — phải khớp với hub.database._local_now()
    để ranh giới ngày/tuần/tháng của báo cáo chi phí đồng bộ với lúc usage được ghi nhận."""
    from datetime import datetime, timedelta
    return datetime.utcnow() + timedelta(hours=_VN_OFFSET_HOURS)

CATEGORIES = {"general", "coding", "creative", "fast", "analysis"}


class ModelPoolCreate(BaseModel):
    name: str = Field(..., min_length=1)
    provider: str = Field("9router")
    api_style: str = Field("openai_compat")
    model_id: str = Field(..., min_length=1)
    base_url: str = Field("")
    api_key: str = Field("")
    # Chỉ dùng cho api_style claude_cli/codex_cli: thư mục tài khoản của CLI.
    # Để trống = tài khoản mặc định (~/.claude, ~/.codex).
    cli_config_dir: str = Field("")
    category: str = Field("general")
    max_requests_per_day: int = Field(0, ge=0)
    max_tokens_per_day: int = Field(0, ge=0)
    price_input_per_1m: float = Field(0, ge=0)
    price_cache_per_1m: float = Field(0, ge=0)
    price_output_per_1m: float = Field(0, ge=0)
    currency: str = Field("USD")


class ModelPoolUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_style: str | None = None
    model_id: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    cli_config_dir: str | None = None
    category: str | None = None
    max_requests_per_day: int | None = None
    max_tokens_per_day: int | None = None
    price_input_per_1m: float | None = None
    price_cache_per_1m: float | None = None
    price_output_per_1m: float | None = None
    currency: str | None = None
    enabled: bool | None = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_models(enabled_only: bool = False):
    models = await list_model_pool(enabled_only=enabled_only)
    # Attach today's usage to each entry
    result = []
    for m in models:
        usage = await get_model_usage_today(m["id"])
        result.append({**m, "usage_today": usage})
    return {"models": result}


@router.post("", status_code=201)
async def create_model(body: ModelPoolCreate):
    entry_id = await create_model_pool_entry(
        name=body.name,
        provider=body.provider,
        api_style=body.api_style,
        model_id=body.model_id,
        base_url=body.base_url,
        api_key=body.api_key,
        cli_config_dir=body.cli_config_dir,
        category=body.category,
        max_requests_per_day=body.max_requests_per_day,
        max_tokens_per_day=body.max_tokens_per_day,
        price_input_per_1m=body.price_input_per_1m,
        price_cache_per_1m=body.price_cache_per_1m,
        price_output_per_1m=body.price_output_per_1m,
        currency=body.currency,
    )
    entry = await get_model_pool_entry(entry_id)
    return entry


@router.get("/stats")
async def pool_stats(limit: int = 10):
    top = await get_top_models_usage(limit=limit)
    return {"top_models": top}


@router.get("/cost/summary")
async def cost_summary():
    """Quy đổi token đã dùng (hôm nay) ra chi phí ước tính theo giá đã cấu hình cho mỗi model."""
    models = await list_model_pool()
    rows = []
    total_by_currency: dict[str, float] = {}
    for m in models:
        usage = await get_model_usage_today(m["id"])
        cost = (
            (usage.get("tokens_input", 0) / 1_000_000) * m.get("price_input_per_1m", 0)
            + (usage.get("tokens_output", 0) / 1_000_000) * m.get("price_output_per_1m", 0)
        )
        currency = m.get("currency") or "USD"
        rows.append({
            "id": m["id"], "name": m["name"], "model_id": m["model_id"],
            "currency": currency, "tokens_input": usage.get("tokens_input", 0),
            "tokens_output": usage.get("tokens_output", 0),
            "requests": usage.get("request_count", 0),
            "estimated_cost": round(cost, 4),
        })
        total_by_currency[currency] = total_by_currency.get(currency, 0) + cost
    return {
        "models": rows,
        "totals": {k: round(v, 4) for k, v in total_by_currency.items()},
    }


# ── Cost Report Helpers ────────────────────────────────────────────────────

def _resolve_date_range(period: str, date_from: str | None, date_to: str | None) -> tuple[str, str]:
    from datetime import timedelta
    today = _local_now().date()
    if date_to is None:
        date_to = today.isoformat()
    if date_from is None:
        span_days = {"day": 30, "week": 84, "month": 365}[period]
        date_from = (today - timedelta(days=span_days)).isoformat()
    return date_from, date_to


def _bucket_range(date_str: str, period: str) -> tuple[str, str, str]:
    """Trả về (bucket_key, bucket_from, bucket_to). bucket_key dùng để nhóm/sắp xếp
    ổn định; bucket_from/bucket_to (YYYY-MM-DD) là ngày đầu/cuối thực tế của kỳ —
    tuần tính từ thứ 2 đến chủ nhật (ISO), tháng tính từ ngày 1 đến ngày cuối tháng."""
    from datetime import datetime, timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    if period == "day":
        return date_str, date_str, date_str
    if period == "week":
        week_start = d - timedelta(days=d.weekday())  # Thứ 2
        week_end = week_start + timedelta(days=6)      # Chủ nhật
        iso_year, iso_week, _ = d.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        return key, week_start.isoformat(), week_end.isoformat()
    # month
    month_start = d.replace(day=1)
    next_month = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    month_end = next_month - timedelta(days=1)
    key = d.strftime("%Y-%m")
    return key, month_start.isoformat(), month_end.isoformat()


def _bucket_and_cost(raw_rows: list[dict], period: str) -> list[dict]:
    """Nhóm các dòng model_usage theo (model_pool_id, bucket) rồi tính tiền."""
    buckets: dict[tuple, dict] = {}
    for r in raw_rows:
        bucket, bucket_from, bucket_to = _bucket_range(r["date"], period)
        key = (r["model_pool_id"], bucket)
        agg = buckets.setdefault(key, {
            "model_pool_id": r["model_pool_id"], "name": r["name"],
            "model_id": r["model_id_str"], "provider": r["provider"],
            "category": r["category"], "currency": r["currency"] or "USD",
            "bucket": bucket, "bucket_from": bucket_from, "bucket_to": bucket_to,
            "period": period,
            "request_count": 0, "tokens_input": 0, "tokens_cache": 0, "tokens_output": 0,
            "price_input_per_1m": r["price_input_per_1m"],
            "price_cache_per_1m": r["price_cache_per_1m"],
            "price_output_per_1m": r["price_output_per_1m"],
        })
        agg["request_count"] += r["request_count"]
        agg["tokens_input"]  += r["tokens_input"]
        agg["tokens_cache"]  += r["tokens_cache"]
        agg["tokens_output"] += r["tokens_output"]
    out = []
    for agg in buckets.values():
        cost = (
            agg["tokens_input"]  / 1_000_000 * agg["price_input_per_1m"]
            + agg["tokens_cache"] / 1_000_000 * agg["price_cache_per_1m"]
            + agg["tokens_output"]/ 1_000_000 * agg["price_output_per_1m"]
        )
        agg["estimated_cost"] = round(cost, 4)
        out.append(agg)
    out.sort(key=lambda r: (r["bucket_from"], r["name"]))
    return out


def _totals_by_currency(raw_rows: list[dict]) -> dict[str, float]:
    """Tổng chi phí theo currency, không nhóm theo kỳ — dùng cho các mốc tổng cố định
    (từ trước đến giờ / tuần này / tháng này)."""
    totals: dict[str, float] = {}
    for r in raw_rows:
        cost = (
            r["tokens_input"]  / 1_000_000 * r["price_input_per_1m"]
            + r["tokens_cache"] / 1_000_000 * r["price_cache_per_1m"]
            + r["tokens_output"]/ 1_000_000 * r["price_output_per_1m"]
        )
        cur = r["currency"] or "USD"
        totals[cur] = totals.get(cur, 0) + cost
    return {k: round(v, 4) for k, v in totals.items()}


def _bucket_and_cost_hourly(raw_rows: list[dict], date: str) -> list[dict]:
    """Nhóm các dòng model_usage_hourly theo (model_pool_id, hour 0-23) rồi tính tiền."""
    buckets: dict[tuple, dict] = {}
    for r in raw_rows:
        key = (r["model_pool_id"], r["hour"])
        agg = buckets.setdefault(key, {
            "model_pool_id": r["model_pool_id"], "name": r["name"],
            "model_id": r["model_id_str"], "provider": r["provider"],
            "category": r["category"], "currency": r["currency"] or "USD",
            "hour": r["hour"], "date": date,
            "request_count": 0, "tokens_input": 0, "tokens_cache": 0, "tokens_output": 0,
            "price_input_per_1m": r["price_input_per_1m"],
            "price_cache_per_1m": r["price_cache_per_1m"],
            "price_output_per_1m": r["price_output_per_1m"],
        })
        agg["request_count"] += r["request_count"]
        agg["tokens_input"]  += r["tokens_input"]
        agg["tokens_cache"]  += r["tokens_cache"]
        agg["tokens_output"] += r["tokens_output"]
    out = []
    for agg in buckets.values():
        cost = (
            agg["tokens_input"]  / 1_000_000 * agg["price_input_per_1m"]
            + agg["tokens_cache"] / 1_000_000 * agg["price_cache_per_1m"]
            + agg["tokens_output"]/ 1_000_000 * agg["price_output_per_1m"]
        )
        agg["estimated_cost"] = round(cost, 4)
        out.append(agg)
    out.sort(key=lambda r: (r["hour"], r["name"]))
    return out


# ── Cost Report Endpoints ──────────────────────────────────────────────────

@router.get("/cost/report")
async def cost_report(period: str = "day", date_from: str | None = None, date_to: str | None = None):
    """Chi phí theo model, nhóm theo ngày/tuần/tháng, kèm chi tiết token
    input/cache/output. Trả về cả bảng chi tiết (rows) và tổng theo currency."""
    if period not in {"day", "week", "month"}:
        raise HTTPException(400, "period phải là day, week hoặc month")
    date_from, date_to = _resolve_date_range(period, date_from, date_to)
    raw = await get_model_usage_range(date_from, date_to)
    rows = _bucket_and_cost(raw, period)
    totals_by_currency: dict[str, float] = {}
    for r in rows:
        totals_by_currency[r["currency"]] = totals_by_currency.get(r["currency"], 0) + r["estimated_cost"]
    return {
        "period": period, "date_from": date_from, "date_to": date_to,
        "rows": rows,
        "totals": {k: round(v, 4) for k, v in totals_by_currency.items()},
    }


@router.get("/cost/report-hourly")
async def cost_report_hourly(date: str | None = None):
    """Chi phí theo giờ (0h-23h) trong 1 ngày cụ thể, kèm chi tiết theo model.
    Dùng cho biểu đồ xu hướng khi chọn 'theo ngày'."""
    if date is None:
        date = _local_now().strftime("%Y-%m-%d")
    raw = await get_model_usage_hourly_range(date)
    rows = _bucket_and_cost_hourly(raw, date)
    totals_by_currency: dict[str, float] = {}
    for r in rows:
        totals_by_currency[r["currency"]] = totals_by_currency.get(r["currency"], 0) + r["estimated_cost"]
    return {
        "date": date,
        "rows": rows,
        "totals": {k: round(v, 4) for k, v in totals_by_currency.items()},
    }


@router.get("/cost/report-calls")
async def cost_report_calls(date: str | None = None):
    """Chi tiết từng LƯỢT GỌI model trong 1 ngày cụ thể, kèm thời gian chính xác
    (khác với /cost/report vốn chỉ tổng theo ngày/tuần/tháng) — dùng để tra cứu
    ngay chi phí của 1 lượt chạy cụ thể."""
    if date is None:
        date = _local_now().strftime("%Y-%m-%d")
    raw = await get_model_call_log_for_date(date)
    calls = []
    for r in raw:
        cost = (
            r["tokens_input"]  / 1_000_000 * r["price_input_per_1m"]
            + r["tokens_cache"] / 1_000_000 * r["price_cache_per_1m"]
            + r["tokens_output"]/ 1_000_000 * r["price_output_per_1m"]
        )
        calls.append({
            "called_at": r["called_at"], "model_pool_id": r["model_pool_id"],
            "name": r["name"], "currency": r["currency"] or "USD",
            "tokens_input": r["tokens_input"], "tokens_cache": r["tokens_cache"],
            "tokens_output": r["tokens_output"], "estimated_cost": round(cost, 4),
        })
    return {"date": date, "calls": calls}


@router.get("/cost/overview")
async def cost_overview():
    """3 mốc tổng chi phí cố định (không phụ thuộc period đang chọn trên UI):
    từ trước đến giờ, tuần này (thứ 2 → chủ nhật), tháng này (ngày 1 → ngày cuối tháng)."""
    from datetime import timedelta
    today = _local_now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    next_month = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    month_end = next_month - timedelta(days=1)

    today_raw = await get_model_usage_range(today.isoformat(), today.isoformat())
    all_time_raw = await get_model_usage_range("2000-01-01", today.isoformat())
    week_raw = await get_model_usage_range(week_start.isoformat(), week_end.isoformat())
    month_raw = await get_model_usage_range(month_start.isoformat(), month_end.isoformat())

    return {
        "today": {"totals": _totals_by_currency(today_raw), "date": today.isoformat()},
        "all_time": _totals_by_currency(all_time_raw),
        "this_week": {
            "totals": _totals_by_currency(week_raw),
            "date_from": week_start.isoformat(), "date_to": week_end.isoformat(),
        },
        "this_month": {
            "totals": _totals_by_currency(month_raw),
            "date_from": month_start.isoformat(), "date_to": month_end.isoformat(),
        },
    }


@router.get("/cost/export.xlsx")
async def cost_export_xlsx(period: str = "day", date_from: str | None = None, date_to: str | None = None):
    if period not in {"day", "week", "month"}:
        raise HTTPException(400, "period phải là day, week hoặc month")
    date_from, date_to = _resolve_date_range(period, date_from, date_to)
    raw = await get_model_usage_range(date_from, date_to)
    rows = _bucket_and_cost(raw, period)
    xlsx_bytes = build_cost_report_xlsx(rows, period, date_from, date_to)
    filename = f"xanax-cost-report-{period}-{date_from}_to_{date_to}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{entry_id}")
async def get_model(entry_id: int):
    entry = await get_model_pool_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Model not found")
    usage = await get_model_usage_today(entry_id)
    return {**entry, "usage_today": usage}


@router.patch("/{entry_id}")
async def update_model(entry_id: int, body: ModelPoolUpdate):
    entry = await get_model_pool_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Model not found")
    kwargs = {}
    for field_name in body.model_fields_set:
        val = getattr(body, field_name)
        if field_name == "enabled":
            kwargs[field_name] = 1 if val else 0
        else:
            kwargs[field_name] = val
    if kwargs:
        await update_model_pool_entry(entry_id, **kwargs)
    updated = await get_model_pool_entry(entry_id)
    usage = await get_model_usage_today(entry_id)
    return {**updated, "usage_today": usage}


@router.delete("/{entry_id}", status_code=204)
async def delete_model(entry_id: int):
    if not await delete_model_pool_entry(entry_id):
        raise HTTPException(404, "Model not found")


@router.post("/{entry_id}/test")
async def test_model(entry_id: int):
    from core.model_pool_bridge import test_model_connection
    entry = await get_model_pool_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Model not found")
    result = await test_model_connection(entry_id)
    return result
