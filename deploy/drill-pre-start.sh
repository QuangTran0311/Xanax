#!/usr/bin/env bash
# Chạy bởi restore.sh qua PRE_START_HOOK, chỉ trong lúc diễn tập.
# Thời điểm: dữ liệu đã vào đúng chỗ, service CHƯA khởi động.
#
# TẠI SAO CẦN: lúc khởi động, api/routes/workflow.py::restore_schedules() đọc
# database và đăng ký lại toàn bộ cron workflow đang bật. Bản diễn tập dùng đúng
# database của production, nên nếu để nguyên thì nó sẽ tự chạy workflow thật —
# gọi Claude/Codex CLI, đốt token, và ghi ra ngoài. Diễn tập phải là quan sát
# viên, không được hành động.
#
# Vô hiệu hóa lịch ở BẢN SAO, không bao giờ đụng tới database production.

set -euo pipefail

BACKEND_DIR="${BACKEND_DIR:?PRE_START_HOOK phải được restore.sh gọi kèm BACKEND_DIR}"
db="$BACKEND_DIR/xanax.db"

[[ -f "$db" ]] || {
    printf 'drill-pre-start: không thấy %s\n' "$db" >&2
    exit 1
}

# Rào chắn cuối cùng: nếu vì lý do gì đó hook này được gọi trên database
# production thì dừng ngay. Tắt lịch của production là một sự cố thật sự.
case "$(readlink -f -- "$db")" in
    /opt/xanax/backend/*)
        printf 'drill-pre-start: TỪ CHỐI chạy trên database production (%s)\n' "$db" >&2
        exit 1
        ;;
esac

# Bảng có thể chưa tồn tại nếu archive quá cũ — không coi đó là lỗi.
if sqlite3 "$db" \
    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_tasks';" \
    | grep -q 1
then
    disabled="$(sqlite3 "$db" \
        "UPDATE workflow_tasks SET schedule_enabled = 0 WHERE schedule_enabled = 1;
         SELECT changes();")"
    printf 'drill-pre-start: đã tắt lịch của %s workflow trong bản diễn tập.\n' "$disabled"
else
    printf 'drill-pre-start: không có bảng workflow_tasks, bỏ qua.\n'
fi
