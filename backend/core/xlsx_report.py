"""Builds a styled .xlsx financial-style report for model-pool cost data."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_TITLE_FONT = Font(bold=True, size=14)
_THIN = Side(style="thin", color="CCCCCC")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

_COLUMNS = [
    ("bucket", "Kỳ"), ("name", "Model"), ("provider", "Provider"),
    ("request_count", "Số request"), ("tokens_input", "Token vào"),
    ("tokens_cache", "Token cache"), ("tokens_output", "Token ra"),
    ("estimated_cost", "Chi phí ước tính"), ("currency", "Tiền tệ"),
]


def build_cost_report_xlsx(rows: list[dict], period: str, date_from: str, date_to: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Chi phi model"

    ws.merge_cells("A1:I1")
    ws["A1"] = "BÁO CÁO CHI PHÍ VẬN HÀNH MODEL — XANAX"
    ws["A1"].font = _TITLE_FONT
    ws["A1"].alignment = Alignment(horizontal="center")

    period_label = {"day": "Theo ngày", "week": "Theo tuần", "month": "Theo tháng"}.get(period, period)
    ws.merge_cells("A2:I2")
    ws["A2"] = f"Kỳ báo cáo: {period_label} | Từ {date_from} đến {date_to}"
    ws["A2"].alignment = Alignment(horizontal="center")

    header_row = 4
    for col_idx, (_, label) in enumerate(_COLUMNS, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center")

    totals_by_currency: dict[str, float] = {}
    r_idx = header_row + 1
    for row in rows:
        for col_idx, (key, _) in enumerate(_COLUMNS, start=1):
            cell = ws.cell(row=r_idx, column=col_idx, value=row.get(key))
            cell.border = _BORDER
        totals_by_currency[row["currency"]] = totals_by_currency.get(row["currency"], 0) + row["estimated_cost"]
        r_idx += 1

    r_idx += 1
    for currency, total in totals_by_currency.items():
        ws.cell(row=r_idx, column=1, value=f"TỔNG ({currency})").font = Font(bold=True)
        cell = ws.cell(row=r_idx, column=8, value=round(total, 4))
        cell.font = Font(bold=True)
        r_idx += 1

    for col_idx in range(1, len(_COLUMNS) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 16

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
