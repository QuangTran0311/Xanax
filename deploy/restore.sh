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

for command_name in tar gzip systemctl curl mktemp grep chown chmod date install mkdir mv rm; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail 69 "Thiếu lệnh phụ thuộc: $command_name"
done

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

printf 'Sắp GHI ĐÈ dữ liệu của %s bằng:\n  %s\n' "$SERVICE_NAME" "$archive"
printf 'Service sẽ bị dừng; database, data và .env hiện tại sẽ được thay thế.\n'
printf 'Gõ chính xác "KHOI PHUC" để tiếp tục: '
read -r confirmation
if [[ "$confirmation" != "KHOI PHUC" ]]; then
    printf 'Đã hủy, chưa thay đổi dữ liệu.\n'
    exit 0
fi

extract_dir="$WORK_DIR/extracted"
mkdir -p "$extract_dir"
tar --no-same-owner --no-same-permissions -xzf "$archive" -C "$extract_dir" \
    || fail 74 "Không giải nén được archive."

systemctl stop "$SERVICE_NAME" \
    || fail 70 "Không dừng được $SERVICE_NAME"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
rollback_dir="$ROLLBACK_ROOT/pre-restore-$timestamp"
install -d -m 0700 "$rollback_dir"

# Giữ dữ liệu cũ để còn đường quay lại nếu bản restore không khởi động được.
for item in xanax.db data .env; do
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

systemctl start "$SERVICE_NAME" \
    || fail 70 "Không khởi động được $SERVICE_NAME; dữ liệu cũ còn ở $rollback_dir"

if ! curl --fail --silent --show-error --retry 15 --retry-delay 2 \
    --retry-connrefused "$HEALTH_URL" >/dev/null; then
    fail 70 "Health check thất bại; dữ liệu cũ còn ở $rollback_dir"
fi

printf 'Restore hoàn tất; health check đạt: %s\n' "$HEALTH_URL"
printf 'Bản trước restore được giữ tại: %s\n' "$rollback_dir"
printf 'Chỉ xóa thư mục đó sau khi đã nghiệm thu dữ liệu.\n'
