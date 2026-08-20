"""Xuất báo cáo thí nghiệm ablation dạng Excel sẵn để đưa vào luận văn."""
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from core.experiment_runner import CONDITIONS
from core.xlsx_report import _BORDER, _HEADER_FILL, _HEADER_FONT, _TITLE_FONT


_NONE = "—"
_CONDITION_LABELS = {
    "khong_soul": "Không nạp tầng tri thức (đối chứng)",
    "soul_nhan_vien": "Soul nhân viên",
    "them_ky_nang": "Thêm phụ lục kỹ năng",
    "day_du": "Đầy đủ ba tầng tri thức",
}
_LAYER_ROWS = (
    ("soul_nhan_vien", "Soul nhân viên", "soul_nhan_vien − khong_soul"),
    ("phu_luc_ky_nang", "Phụ lục kỹ năng", "them_ky_nang − soul_nhan_vien"),
    ("soul_du_an", "Soul dự án", "day_du − them_ky_nang"),
    ("tong_day_du_vs_doi_chung", "Tổng cộng", "day_du − khong_soul"),
)


def _shown(value):
    return _NONE if value is None or value == "" else value


def _start_table(ws, title: str, columns: list[str]) -> int:
    header_row = _start_table_at(ws, title, columns, 1)
    ws.freeze_panes = "A4"
    return header_row


def _start_table_at(ws, title: str, columns: list[str], title_row: int) -> int:
    ws.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=len(columns))
    title_cell = ws.cell(title_row, 1, title)
    title_cell.font = _TITLE_FONT
    title_cell.alignment = Alignment(horizontal="center")

    header_row = title_row + 2
    for column, label in enumerate(columns, start=1):
        cell = ws.cell(header_row, column, label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return header_row


def _write_row(ws, row_number: int, values: list, *, bold: bool = False) -> None:
    for column, value in enumerate(values, start=1):
        cell = ws.cell(row_number, column, _shown(value))
        cell.border = _BORDER
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if bold:
            cell.font = Font(bold=True)


def _set_widths(ws, widths: list[float]) -> None:
    for column, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(column)].width = width


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration(started_at, completed_at) -> str:
    started = _parse_time(started_at)
    completed = _parse_time(completed_at)
    if started is None or completed is None:
        return _NONE
    try:
        seconds = max(0, round((completed - started).total_seconds()))
    except TypeError:
        return _NONE
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _method_description(summary: dict) -> str:
    stddev = {
        "sample_n_minus_1": "độ lệch chuẩn mẫu (n−1)",
    }.get(summary.get("stddev_method"), str(summary.get("stddev_method") or _NONE))
    population = {
        "answered_only": "chỉ tính lượt answered",
    }.get(summary.get("score_population"), str(summary.get("score_population") or _NONE))
    effect_size = {
        "cohens_d_pooled": "Cohen's d với độ lệch chuẩn gộp",
    }.get(summary.get("effect_size_method"), str(summary.get("effect_size_method") or _NONE))
    confidence_method = {
        "welch_t_two_sided_95": "t Welch hai phía",
    }.get(
        summary.get("delta_confidence_method"),
        str(summary.get("delta_confidence_method") or _NONE),
    )
    level = summary.get("delta_confidence_level")
    confidence = f"{float(level) * 100:g}%" if isinstance(level, (int, float)) else _NONE
    minimum = _shown(summary.get("minimum_answered"))
    return (
        f"{stddev} · khoảng tin cậy {confidence} bằng {confidence_method} · "
        f"bảng chính {population}, Bảng 1B tính mọi lượt đã chấm · "
        f"ngưỡng tối thiểu {minimum} lượt trong mỗi quần thể · {effect_size} · "
        "thứ tự chạy được xáo ngẫu nhiên · "
        "giám khảo chấm mù trên mã ẩn danh"
    )


def _environment_sheet(wb: Workbook, experiment: dict, summary: dict, config: dict) -> None:
    ws = wb.active
    ws.title = "Moi truong"
    header_row = _start_table(ws, "MÔI TRƯỜNG THÍ NGHIỆM", ["Hạng mục", "Giá trị"])

    agent = config.get("agent") or {}
    project = config.get("project") or None
    benchmark = config.get("benchmark") or {}
    measured = config.get("measured_model") or {}
    judge = config.get("judge_model") or {}
    test_cases = benchmark.get("test_cases")
    case_count = len(test_cases) if isinstance(test_cases, list) else 0

    rows = [
        ("Tên thí nghiệm", experiment.get("name")),
        ("Nhân viên AI được đo", agent.get("name") or experiment.get("agent_name")),
    ]
    if project:
        rows.append(("Dự án", project.get("name") if isinstance(project, dict) else project))
    rows.extend([
        ("Bộ đề", benchmark.get("name") or experiment.get("benchmark_name")),
        ("Số đề", case_count),
        ("Model bị đo - tên", measured.get("name") or experiment.get("measured_model_name")),
        ("Model bị đo - model_id", measured.get("model_id") or experiment.get("measured_model_id")),
        ("Model bị đo - provider", measured.get("provider")),
        ("Model bị đo - api_style", measured.get("api_style")),
        ("Model giám khảo - tên", judge.get("name") or experiment.get("judge_model_name")),
        ("Model giám khảo - model_id", judge.get("model_id") or experiment.get("judge_model_id")),
        ("Model giám khảo - provider", judge.get("provider")),
        ("Model giám khảo - api_style", judge.get("api_style")),
        ("Số lần lặp mỗi điều kiện", config.get("repetitions", experiment.get("repetitions"))),
        ("Tổng số lượt", experiment.get("total_trials")),
        ("Số lượt đã chấm", experiment.get("scored_trials")),
        ("Thời điểm bắt đầu", experiment.get("started_at")),
        ("Thời điểm kết thúc", experiment.get("completed_at")),
        ("Tổng thời gian chạy (giờ:phút:giây)", _duration(
            experiment.get("started_at"), experiment.get("completed_at")
        )),
        ("Phương pháp", _method_description(summary)),
    ])
    for row_number, values in enumerate(rows, start=header_row + 1):
        _write_row(ws, row_number, list(values))
        ws.cell(row_number, 1).font = Font(bold=True)
    _set_widths(ws, [36, 105])
    ws.auto_filter.ref = f"A{header_row}:B{header_row + len(rows)}"


def _condition_comparison_sheet(wb: Workbook, summary: dict) -> None:
    ws = wb.create_sheet("Bang 1 - So sanh dieu kien")
    columns = [
        "Điều kiện", "Điểm trung bình", "Độ lệch chuẩn", "n",
        "Δ so với đối chứng", "Biên tin cậy 95%",
        "Phân biệt được với nhiễu", "Cohen's d",
    ]
    header_row = _start_table(ws, "BẢNG 1 - SO SÁNH ĐIỀU KIỆN", columns)
    by_condition = {row.get("condition"): row for row in summary.get("conditions", [])}
    means = [row.get("mean") for row in by_condition.values() if row.get("mean") is not None]
    best_mean = max(means) if means else None

    row_number = header_row + 1
    for condition in CONDITIONS:
        row = by_condition.get(condition, {})
        stats_reliable = row.get("stats_reliable") is not False
        values = [
            _CONDITION_LABELS[condition], row.get("mean"), row.get("stddev"), row.get("n"),
            row.get("delta_vs_control"), row.get("delta_confidence_margin_95"),
            ("Có" if row.get("delta_distinguishable") else "Không")
            if stats_reliable else _NONE,
            row.get("cohens_d") if stats_reliable else _NONE,
        ]
        _write_row(ws, row_number, values, bold=best_mean is not None and row.get("mean") == best_mean)
        for column in (2, 3, 5, 6, 8):
            if isinstance(ws.cell(row_number, column).value, (int, float)):
                ws.cell(row_number, column).number_format = "0.0000"
        row_number += 1

    unreliable_notes = [
        f"{_CONDITION_LABELS.get(row.get('condition'), row.get('condition', _NONE))}: "
        f"{row.get('unreliable_reason')}"
        for row in summary.get("conditions", [])
        if row.get("stats_reliable") is False and row.get("unreliable_reason")
    ]
    note_row = row_number + 1
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=len(columns))
    note = ws.cell(note_row, 1)
    note.value = (
        "Ghi chú độ tin cậy: " + "; ".join(unreliable_notes)
        if unreliable_notes else "Ghi chú độ tin cậy: mọi điều kiện đều đạt ngưỡng mẫu."
    )
    note.font = Font(italic=True)
    note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[note_row].height = max(30, 15 * (1 + len(unreliable_notes) // 2))

    full_population_columns = [
        "Điều kiện", "Điểm TB", "Độ lệch chuẩn", "n", "Δ so với đối chứng",
    ]
    full_title_row = note_row + 2
    full_header_row = _start_table_at(
        ws,
        "BẢNG 1B - ĐỐI CHIẾU QUẦN THỂ ĐẦY ĐỦ (mọi lượt đã chấm)",
        full_population_columns,
        full_title_row,
    )
    full_row_number = full_header_row + 1
    for condition in CONDITIONS:
        row = by_condition.get(condition, {}).get("all_scored") or {}
        _write_row(ws, full_row_number, [
            _CONDITION_LABELS[condition], row.get("mean"), row.get("stddev"), row.get("n"),
            row.get("delta_vs_control"),
        ])
        for column in (2, 3, 5):
            if isinstance(ws.cell(full_row_number, column).value, (int, float)):
                ws.cell(full_row_number, column).number_format = "0.0000"
        full_row_number += 1

    explanation_row = full_row_number + 1
    ws.merge_cells(
        start_row=explanation_row, start_column=1,
        end_row=explanation_row, end_column=len(full_population_columns),
    )
    explanation = ws.cell(explanation_row, 1)
    explanation.value = (
        "Giải thích: Bảng 1 chỉ tính lượt classified answered; Bảng 1B không lọc "
        "classification và giữ mọi lượt có điểm để lộ rõ ảnh hưởng của chính sách lọc."
    )
    explanation.font = Font(italic=True)
    explanation.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[explanation_row].height = 36
    _set_widths(ws, [38, 18, 18, 10, 22, 21, 30, 16])
    ws.auto_filter.ref = f"A{header_row}:H{row_number - 1}"


def _layer_contribution_sheet(wb: Workbook, summary: dict) -> None:
    ws = wb.create_sheet("Bang 2 - Dong gop tung tang")
    header_row = _start_table(
        ws, "BẢNG 2 - ĐÓNG GÓP TỪNG TẦNG", ["Tầng tri thức", "Δ điểm", "So sánh"]
    )
    contributions = summary.get("layer_contributions") or {}
    for offset, (key, label, comparison) in enumerate(_LAYER_ROWS, start=1):
        row_number = header_row + offset
        _write_row(
            ws, row_number, [label, contributions.get(key), comparison],
            bold=key == "tong_day_du_vs_doi_chung",
        )
        if isinstance(ws.cell(row_number, 2).value, (int, float)):
            ws.cell(row_number, 2).number_format = "0.0000"
    _set_widths(ws, [28, 16, 42])
    ws.auto_filter.ref = f"A{header_row}:C{header_row + len(_LAYER_ROWS)}"


def _behavior_sheet(wb: Workbook, summary: dict) -> None:
    ws = wb.create_sheet("Bang 3 - Hanh vi")
    columns = [
        "Điều kiện", "Tổng lượt đã chấm", "Lượt answered", "Lượt clarify",
        "Tỷ lệ clarify", "Lượt conflict", "Tỷ lệ conflict",
    ]
    header_row = _start_table(ws, "BẢNG 3 - HÀNH VI", columns)
    by_condition = {row.get("condition"): row for row in summary.get("conditions", [])}
    row_number = header_row + 1
    for condition in CONDITIONS:
        row = by_condition.get(condition, {})
        _write_row(ws, row_number, [
            _CONDITION_LABELS[condition], row.get("total_n"), row.get("n"),
            row.get("clarify_n"), row.get("clarify_rate"),
            row.get("conflict_n"), row.get("conflict_rate"),
        ])
        for column in (5, 7):
            if isinstance(ws.cell(row_number, column).value, (int, float)):
                ws.cell(row_number, column).number_format = "0.0%"
        row_number += 1

    note_row = row_number + 1
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=len(columns))
    note = ws.cell(note_row, 1)
    note.value = (
        "Ghi chú: Lượt conflict KHÔNG bị tính thành điểm 0, vì làm vậy sẽ phạt đúng hành vi "
        "cần giữ — agent phát hiện đề bài đá luật đã được dạy và hỏi lại thay vì âm thầm vi phạm."
    )
    note.font = Font(italic=True)
    note.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[note_row].height = 42
    _set_widths(ws, [38, 22, 18, 17, 18, 18, 18])
    ws.auto_filter.ref = f"A{header_row}:G{row_number - 1}"


def _short_prompt(value) -> str:
    text = str(value or "")
    return text if len(text) <= 120 else text[:119] + "…"


def _case_sheet(wb: Workbook, summary: dict) -> None:
    ws = wb.create_sheet("Bang 4 - Tung de")
    columns = [
        "Đề", "Nội dung đề", "Điều kiện", "Điểm trung bình",
        "Độ lệch chuẩn", "n", "Δ so với đối chứng",
    ]
    header_row = _start_table(ws, "BẢNG 4 - KẾT QUẢ TỪNG ĐỀ", columns)
    row_number = header_row + 1
    for case in summary.get("cases", []):
        by_condition = {row.get("condition"): row for row in case.get("conditions", [])}
        means = [row.get("mean") for row in by_condition.values() if row.get("mean") is not None]
        best_mean = max(means) if means else None
        case_index = case.get("case_index")
        case_label = case_index + 1 if isinstance(case_index, int) else case_index
        for condition in CONDITIONS:
            row = by_condition.get(condition, {})
            _write_row(ws, row_number, [
                case_label, _short_prompt(case.get("prompt")), _CONDITION_LABELS[condition],
                row.get("mean"), row.get("stddev"), row.get("n"), row.get("delta_vs_control"),
            ], bold=best_mean is not None and row.get("mean") == best_mean)
            for column in (4, 5, 7):
                if isinstance(ws.cell(row_number, column).value, (int, float)):
                    ws.cell(row_number, column).number_format = "0.0000"
            row_number += 1
    _set_widths(ws, [10, 65, 38, 18, 18, 10, 22])
    if row_number > header_row + 1:
        ws.auto_filter.ref = f"A{header_row}:G{row_number - 1}"


def _warning_text(warning) -> str:
    if not isinstance(warning, dict):
        return str(warning)
    if warning.get("message"):
        return str(warning["message"])
    if warning.get("code") == "insufficient_answered":
        condition = _CONDITION_LABELS.get(warning.get("condition"), warning.get("condition", _NONE))
        return (
            f"{condition}: chỉ có {warning.get('answered_n', _NONE)} lượt answered; "
            f"ngưỡng tối thiểu là {warning.get('minimum_answered', _NONE)}."
        )
    return json.dumps(warning, ensure_ascii=False, sort_keys=True)


def _warnings_sheet(wb: Workbook, warnings: list) -> None:
    ws = wb.create_sheet("Canh bao")
    header_row = _start_table(ws, "CẢNH BÁO", ["STT", "Nội dung cảnh báo"])
    for offset, warning in enumerate(warnings, start=1):
        _write_row(ws, header_row + offset, [offset, _warning_text(warning)])
    _set_widths(ws, [10, 110])
    ws.auto_filter.ref = f"A{header_row}:B{header_row + len(warnings)}"


def build_experiment_report_xlsx(
    experiment: dict, summary: dict, config_snapshot: dict,
) -> bytes:
    """Tạo workbook báo cáo; dữ liệu thiếu luôn hiện thành dấu gạch ngang để không bị hiểu là 0."""
    wb = Workbook()
    # Tên sheet cố ý không dấu vì một số bản Excel/Office xử lý tên sheet có dấu không nhất quán.
    _environment_sheet(wb, experiment, summary, config_snapshot or {})
    _condition_comparison_sheet(wb, summary)
    _layer_contribution_sheet(wb, summary)
    _behavior_sheet(wb, summary)
    _case_sheet(wb, summary)
    warnings = summary.get("warnings") or []
    if warnings:
        _warnings_sheet(wb, warnings)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
