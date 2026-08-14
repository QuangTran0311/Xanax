#!/usr/bin/env bash
# Backup thủ công: sudo /usr/local/sbin/xanax-backup
# Cron: 17 2 * * * root /usr/local/sbin/xanax-backup >>/var/log/xanax-backup.log 2>&1
# systemd timer: đặt ExecStart=/usr/local/sbin/xanax-backup trong oneshot service
# và OnCalendar=*-*-* 02:17:00 trong timer (mẫu đầy đủ ở deploy/README.md).
# Backup chưa từng khôi phục thử trên máy tách biệt thì CHƯA được tính là backup.

set -euo pipefail
umask 077

KEEP_BACKUPS="${KEEP_BACKUPS:-14}"
APP_ROOT="${APP_ROOT:-/opt/xanax}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/xanax}"

DB_PATH="$APP_ROOT/backend/xanax.db"
DATA_DIR="$APP_ROOT/backend/data"
ENV_FILE="$APP_ROOT/backend/.env"

STAGING_DIR=""
TEMP_ARCHIVE=""

fail() {
    local code="$1"
    shift
    printf 'LỖI: %s\n' "$*" >&2
    exit "$code"
}

cleanup() {
    local code=$?
    if [[ -n "$STAGING_DIR" && -d "$STAGING_DIR" ]]; then
        rm -rf -- "$STAGING_DIR"
    fi
    if [[ -n "$TEMP_ARCHIVE" && -f "$TEMP_ARCHIVE" ]]; then
        rm -f -- "$TEMP_ARCHIVE"
    fi
    if (( code != 0 )); then
        printf 'Backup thất bại (mã %d).\n' "$code" >&2
    fi
}
trap cleanup EXIT

for command_name in sqlite3 tar gzip mktemp find sort date install cp mv rm; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail 69 "Thiếu lệnh phụ thuộc: $command_name"
done

[[ "$KEEP_BACKUPS" =~ ^[1-9][0-9]*$ ]] \
    || fail 64 "KEEP_BACKUPS phải là số nguyên dương."
[[ -n "$APP_ROOT" && "$APP_ROOT" != "/" ]] \
    || fail 64 "APP_ROOT không hợp lệ."
[[ -f "$DB_PATH" ]] || fail 66 "Không thấy database: $DB_PATH"
[[ -d "$DATA_DIR" ]] || fail 66 "Không thấy thư mục dữ liệu: $DATA_DIR"
[[ -f "$ENV_FILE" ]] || fail 66 "Không thấy file môi trường: $ENV_FILE"

install -d -m 0700 "$BACKUP_DIR" \
    || fail 73 "Không tạo được thư mục backup: $BACKUP_DIR"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
archive="$BACKUP_DIR/xanax-backup-$timestamp.tar.gz"
[[ ! -e "$archive" ]] || fail 73 "File backup đã tồn tại: $archive"

STAGING_DIR="$(mktemp -d "$BACKUP_DIR/.xanax-backup.XXXXXX")" \
    || fail 73 "Không tạo được thư mục tạm trong $BACKUP_DIR"
install -d -m 0700 "$STAGING_DIR/backend"

# .backup dùng SQLite API để tạo snapshot nhất quán dù app vẫn đang ghi database.
sqlite3 -cmd '.timeout 10000' "$DB_PATH" \
    ".backup '$STAGING_DIR/backend/xanax.db'" \
    || fail 74 "SQLite backup thất bại."

cp -a -- "$DATA_DIR" "$STAGING_DIR/backend/data"
cp -p -- "$ENV_FILE" "$STAGING_DIR/backend/.env"

TEMP_ARCHIVE="$archive.tmp"
tar -C "$STAGING_DIR" -czf "$TEMP_ARCHIVE" backend \
    || fail 74 "Không đóng gói được backup."
mv -- "$TEMP_ARCHIVE" "$archive"
TEMP_ARCHIVE=""

# Tên chứa timestamp UTC nên sort ngược cũng chính là mới nhất trước.
mapfile -t backups < <(
    find "$BACKUP_DIR" -maxdepth 1 -type f \
        -name 'xanax-backup-*.tar.gz' -printf '%p\n' | sort -r
)
for ((index = KEEP_BACKUPS; index < ${#backups[@]}; index++)); do
    rm -f -- "${backups[$index]}"
done

printf 'Backup hoàn tất: %s\n' "$archive"
printf 'Đang giữ tối đa %s bản gần nhất trong %s\n' "$KEEP_BACKUPS" "$BACKUP_DIR"
