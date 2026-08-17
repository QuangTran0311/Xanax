#!/usr/bin/env bash
# Khôi phục có phá dữ liệu hiện tại; script chỉ tiếp tục khi gõ đúng KHOI PHUC.
# Dùng: sudo /usr/local/sbin/xanax-restore /var/backups/xanax/xanax-backup-....tar.gz

set -euo pipefail
umask 077

APP_ROOT="${APP_ROOT:-/opt/xanax}"
SERVICE_NAME="${SERVICE_NAME:-xanax.service}"
SERVICE_USER="${SERVICE_USER:-xanax}"
SERVICE_GROUP="${SERVICE_GROUP:-xanax}"
ROLLBACK_ROOT="${ROLLBACK_ROOT:-/var/backups/xanax}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/api/health}"

# ── Rào chắn chống restore nhầm vào production ─────────────────────────────
# APP_ROOT và SERVICE_NAME đều có giá trị mặc định trỏ vào production. Quên set
# biến khi diễn tập là ghi đè thẳng lên dữ liệu thật. Vì vậy script bắt buộc
# phải biết nó đang chạy ở chế độ nào, và hai biến trên phải khớp cặp.
#
#   production — restore thật vào $PRODUCTION_APP_ROOT / $PRODUCTION_SERVICE
#   drill      — diễn tập, CẤM chạm vào cả hai thứ đó
XANAX_RESTORE_MODE="${XANAX_RESTORE_MODE:-production}"
PRODUCTION_APP_ROOT="${PRODUCTION_APP_ROOT:-/opt/xanax}"
PRODUCTION_SERVICE="${PRODUCTION_SERVICE:-xanax.service}"

# Chỉ có tác dụng ở chế độ drill; production luôn phải gõ tay để xác nhận.
XANAX_RESTORE_ASSUME_YES="${XANAX_RESTORE_ASSUME_YES:-0}"

# Lệnh tùy chọn chạy bằng root sau khi dữ liệu đã vào đúng chỗ và đã đặt quyền,
# nhưng TRƯỚC khi service khởi động. Dùng cho diễn tập: tắt lịch chạy workflow
# trong bản sao để nó không tự gọi CLI như production.
PRE_START_HOOK="${PRE_START_HOOK:-}"

WORK_DIR=""

fail() {
    local code="$1"
    shift
    printf 'LỖI: %s\n' "$*" >&2
    exit "$code"
}

cleanup() {
    local code=$?
    if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
        rm -rf -- "$WORK_DIR"
    fi
    if (( code != 0 )); then
        printf 'Restore thất bại (mã %d). Kiểm tra: journalctl -u %s -n 100\n' \
            "$code" "$SERVICE_NAME" >&2
    fi
}
trap cleanup EXIT

[[ $# -eq 1 ]] || fail 64 "Cách dùng: $0 <file-backup.tar.gz>"
[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 77 "Phải chạy restore bằng root (sudo)."
[[ -n "$APP_ROOT" && "$APP_ROOT" != "/" ]] || fail 64 "APP_ROOT không hợp lệ."

for command_name in tar gzip systemctl curl mktemp grep chown chmod date install mkdir mv rm readlink; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail 69 "Thiếu lệnh phụ thuộc: $command_name"
done

# So sánh theo đường dẫn đã phân giải symlink: /opt/xanax và một symlink trỏ vào
# nó phải bị coi là cùng một chỗ, nếu không rào chắn có thể lách qua được.
resolve_path() {
    readlink -f -- "$1" 2>/dev/null || printf '%s' "$1"
}
app_root_resolved="$(resolve_path "$APP_ROOT")"
production_root_resolved="$(resolve_path "$PRODUCTION_APP_ROOT")"

# Viết bằng `if` chứ không phải `[[ ... ]] && x=1`: dưới `set -e`, một phép so
# sánh sai ở cấp cao nhất sẽ giết luôn script.
is_production_root=0
if [[ "$app_root_resolved" == "$production_root_resolved" ]]; then
    is_production_root=1
fi
is_production_service=0
if [[ "$SERVICE_NAME" == "$PRODUCTION_SERVICE" ]]; then
    is_production_service=1
fi

case "$XANAX_RESTORE_MODE" in
    production)
        # Cả hai phải cùng là production. Lệch một nửa nghĩa là người chạy đang
        # nhầm lẫn ở đâu đó — ví dụ set APP_ROOT sang bản diễn tập nhưng quên
        # SERVICE_NAME, và script sẽ dừng production để restore vào chỗ khác.
        if (( is_production_root != is_production_service )); then
            fail 64 "APP_ROOT và SERVICE_NAME không khớp cặp.
  APP_ROOT      = $APP_ROOT (production: $PRODUCTION_APP_ROOT)
  SERVICE_NAME  = $SERVICE_NAME (production: $PRODUCTION_SERVICE)
Restore vào chỗ khác production thì đặt XANAX_RESTORE_MODE=drill."
        fi
        if (( is_production_root == 0 )); then
            fail 64 "Chế độ production nhưng APP_ROOT không phải $PRODUCTION_APP_ROOT.
Nếu bản cài thật nằm ở nơi khác, đặt cả PRODUCTION_APP_ROOT và PRODUCTION_SERVICE."
        fi
        ;;
    drill)
        if (( is_production_root == 1 )); then
            fail 64 "Chế độ drill nhưng APP_ROOT trỏ vào production ($app_root_resolved).
Diễn tập phải dùng thư mục riêng, ví dụ /opt/xanax-drill."
        fi
        if (( is_production_service == 1 )); then
            fail 64 "Chế độ drill nhưng SERVICE_NAME là service production ($SERVICE_NAME).
Diễn tập phải dùng unit riêng, ví dụ xanax-drill.service."
        fi
        ;;
    *)
        fail 64 "XANAX_RESTORE_MODE phải là 'production' hoặc 'drill', đang là '$XANAX_RESTORE_MODE'."
        ;;
esac

archive="$1"
[[ -f "$archive" ]] || fail 66 "Không thấy file backup: $archive"
backend_dir="$APP_ROOT/backend"
[[ -d "$backend_dir" ]] || fail 66 "Không thấy backend: $backend_dir"

WORK_DIR="$(mktemp -d "$APP_ROOT/.xanax-restore.XXXXXX")" \
    || fail 73 "Không tạo được thư mục tạm trong $APP_ROOT"
archive_list="$WORK_DIR/archive.list"
tar -tzf "$archive" >"$archive_list" \
    || fail 65 "Archive hỏng hoặc không phải gzip tar hợp lệ."

# Chỉ nhận layout do backup.sh tạo và chặn đường dẫn thoát khỏi thư mục giải nén.
if grep -Eq '(^/|(^|/)\.\.(/|$))' "$archive_list"; then
    fail 65 "Archive chứa đường dẫn không an toàn."
fi
grep -Fxq 'backend/xanax.db' "$archive_list" \
    || fail 65 "Archive thiếu backend/xanax.db"
grep -Fxq 'backend/.env' "$archive_list" \
    || fail 65 "Archive thiếu backend/.env"
grep -Fxq 'backend/data/' "$archive_list" \
    || fail 65 "Archive thiếu backend/data/"

if [[ "$XANAX_RESTORE_MODE" == "drill" ]]; then
    confirm_word='DIEN TAP'
else
    confirm_word='KHOI PHUC'
fi

printf 'Chế độ: %s\n' "$XANAX_RESTORE_MODE"
printf 'Sắp GHI ĐÈ dữ liệu của %s tại %s bằng:\n  %s\n' \
    "$SERVICE_NAME" "$APP_ROOT" "$archive"
printf 'Service sẽ bị dừng; database, data và .env hiện tại sẽ được thay thế.\n'

# Chuỗi xác nhận khác nhau theo chế độ để việc gõ "KHOI PHUC" không trở thành
# phản xạ từ những lần diễn tập.
if [[ "$XANAX_RESTORE_MODE" == "drill" && "$XANAX_RESTORE_ASSUME_YES" == "1" ]]; then
    printf 'Bỏ qua xác nhận (diễn tập tự động).\n'
else
    printf 'Gõ chính xác "%s" để tiếp tục: ' "$confirm_word"
    read -r confirmation
    if [[ "$confirmation" != "$confirm_word" ]]; then
        printf 'Đã hủy, chưa thay đổi dữ liệu.\n'
        exit 0
    fi
fi

extract_dir="$WORK_DIR/extracted"
mkdir -p "$extract_dir"
tar --no-same-owner --no-same-permissions -xzf "$archive" -C "$extract_dir" \
    || fail 74 "Không giải nén được archive."

# Ở chế độ drill, unit có thể chưa từng được cài — lần diễn tập đầu tiên dựng
# mọi thứ từ đầu. Không có unit thì không có gì để dừng.
if [[ "$XANAX_RESTORE_MODE" == "drill" ]] \
    && ! systemctl cat "$SERVICE_NAME" >/dev/null 2>&1; then
    printf 'Chưa có unit %s; bỏ qua bước dừng service.\n' "$SERVICE_NAME"
else
    systemctl stop "$SERVICE_NAME" \
        || fail 70 "Không dừng được $SERVICE_NAME"
fi

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
rollback_dir="$ROLLBACK_ROOT/pre-restore-$timestamp"
install -d -m 0700 "$rollback_dir"

# Giữ dữ liệu cũ để còn đường quay lại nếu bản restore không khởi động được.
#
# `xanax.db-wal` và `xanax.db-shm` phải được dọn cùng lúc với database. Bản
# restore do sqlite3 `.backup` tạo ra là file hoàn chỉnh, không có WAL đi kèm;
# để sót WAL của database CŨ nằm lại cạnh database MỚI thì lần mở tiếp theo
# SQLite sẽ ghép nhầm hai thứ vào nhau và làm hỏng dữ liệu vừa khôi phục.
# (Hiện app chưa bật WAL nên thường không có hai file này — dọn sẵn để ngày bật
# WAL không phải nhớ lại chuyện này.)
for item in xanax.db xanax.db-wal xanax.db-shm data .env; do
    if [[ -e "$backend_dir/$item" ]]; then
        mv -- "$backend_dir/$item" "$rollback_dir/$item"
    fi
done

mv -- "$extract_dir/backend/xanax.db" "$backend_dir/xanax.db"
mv -- "$extract_dir/backend/data" "$backend_dir/data"
mv -- "$extract_dir/backend/.env" "$backend_dir/.env"

chown "$SERVICE_USER:$SERVICE_GROUP" "$backend_dir/xanax.db" "$backend_dir/.env"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$backend_dir/data"
chmod 0600 "$backend_dir/xanax.db" "$backend_dir/.env"
chmod -R u+rwX,go-rwx "$backend_dir/data"

# Dữ liệu đã đúng chỗ và đúng quyền, service thì chưa chạy — đây là cửa sổ duy
# nhất để sửa nội dung database trước khi app kịp đọc nó.
if [[ -n "$PRE_START_HOOK" ]]; then
    printf 'Chạy PRE_START_HOOK: %s\n' "$PRE_START_HOOK"
    if ! APP_ROOT="$APP_ROOT" BACKEND_DIR="$backend_dir" \
        bash -c "$PRE_START_HOOK"; then
        fail 70 "PRE_START_HOOK thất bại; service chưa khởi động, dữ liệu cũ còn ở $rollback_dir"
    fi
fi

systemctl start "$SERVICE_NAME" \
    || fail 70 "Không khởi động được $SERVICE_NAME; dữ liệu cũ còn ở $rollback_dir"

if ! curl --fail --silent --show-error --retry 15 --retry-delay 2 \
    --retry-connrefused "$HEALTH_URL" >/dev/null; then
    fail 70 "Health check thất bại; dữ liệu cũ còn ở $rollback_dir"
fi

printf 'Restore hoàn tất; health check đạt: %s\n' "$HEALTH_URL"
printf 'Bản trước restore được giữ tại: %s\n' "$rollback_dir"
printf 'Chỉ xóa thư mục đó sau khi đã nghiệm thu dữ liệu.\n'
