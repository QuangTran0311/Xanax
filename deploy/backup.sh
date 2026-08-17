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

# Cấu hình đẩy backup ra ngoài VPS. Không có file này thì bỏ qua bước off-site.
BACKUP_ENV="${BACKUP_ENV:-/etc/xanax/backup.env}"
if [[ -r "$BACKUP_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$BACKUP_ENV"
fi
: "${OFFSITE_REMOTE:=}"
: "${OFFSITE_KEEP_DAYS:=30}"
: "${RCLONE_BWLIMIT:=}"
: "${RCLONE_CONFIG:=/root/.config/rclone/rclone.conf}"
export RCLONE_CONFIG

NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"

DB_PATH="$APP_ROOT/backend/xanax.db"
DATA_DIR="$APP_ROOT/backend/data"
ENV_FILE="$APP_ROOT/backend/.env"

STAGING_DIR=""
TEMP_ARCHIVE=""
# Đặt thành 1 khi archive local đã hoàn tất, để cleanup phân biệt được
# "backup hỏng" với "backup xong nhưng không đẩy ra ngoài được".
LOCAL_BACKUP_DONE=0

# xanax-notify tự nuốt mọi lỗi của nó, nhưng vẫn bọc thêm một lớp: máy chưa cài
# script cảnh báo thì backup phải chạy bình thường, không phải chết vì thiếu nó.
notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

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
        # Mã 75 là "local xong, off-site hỏng" và đã tự gửi cảnh báo riêng, chi
        # tiết hơn, ở push_offsite; gửi thêm ở đây chỉ tổ trùng tin nhắn.
        if (( code != 75 )); then
            local local_state='Không có bản backup mới nào được tạo.'
            if (( LOCAL_BACKUP_DONE == 1 )); then
                local_state='Bản backup local ĐÃ tạo xong; lỗi xảy ra ở bước sau đó.'
            fi
            notify crit 'Backup Xanax THẤT BẠI' \
                "Script thoát với mã $code trên $APP_ROOT.
$local_state
Xem log: journalctl -u xanax-backup.service -n 50"
        fi
    fi
}
trap cleanup EXIT

for command_name in sqlite3 tar gzip mktemp find sort date install cp mv rm stat basename du; do
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

# `.backup` dùng SQLite backup API để tạo snapshot nhất quán dù app vẫn đang ghi.
# Khi WAL đang bật, API tự gộp cả dữ liệu trong xanax.db-wal vào xanax.db của bản
# sao. Vì vậy archive chỉ cần file database này; không thêm -wal/-shm và không đổi
# lệnh dưới đây thành `cp`.
sqlite3 -cmd '.timeout 10000' "$DB_PATH" \
    ".backup '$STAGING_DIR/backend/xanax.db'" \
    || fail 74 "SQLite backup thất bại."

cp -a -- "$DATA_DIR" "$STAGING_DIR/backend/data"
cp -p -- "$ENV_FILE" "$STAGING_DIR/backend/.env"

TEMP_ARCHIVE="$archive.tmp"
tar -C "$STAGING_DIR" -czf "$TEMP_ARCHIVE" backend \
    || fail 74 "Không đóng gói được backup."
mv -- "$TEMP_ARCHIVE" "$archive"
# Xóa khỏi biến TRƯỚC khi đi tiếp: trap cleanup xóa file trỏ bởi TEMP_ARCHIVE, mà
# từ đây trở đi đường dẫn đó chính là archive thật.
TEMP_ARCHIVE=""
LOCAL_BACKUP_DONE=1

# ── Đẩy ra ngoài VPS ───────────────────────────────────────────────────────
# Backup nằm cùng ổ với dữ liệu gốc thì không chống được hỏng ổ hay mất VPS.
#
# Hàm này CỐ Ý không được phép giết script: nó chạy trong `if ! push_offsite`
# nên `set -e` không áp dụng cho các lệnh bên trong, và bản backup local đã hoàn
# tất ở trên vẫn được giữ, phần dọn bản cũ phía dưới vẫn chạy.
push_offsite() {
    # `r2crypt:` và `r2crypt:thu-muc/` đều hợp lệ; chỉ thêm dấu / khi còn thiếu.
    local remote_path="$OFFSITE_REMOTE"
    [[ "$remote_path" == *: || "$remote_path" == */ ]] || remote_path="$remote_path/"

    local -a rclone_opts=(
        --config "$RCLONE_CONFIG"
        --retries 3
        --low-level-retries 10
        --contimeout 30s
        --timeout 5m
    )
    if [[ -n "$RCLONE_BWLIMIT" ]]; then
        rclone_opts+=(--bwlimit "$RCLONE_BWLIMIT")
    fi

    printf 'Đang đẩy backup lên %s ...\n' "$remote_path"
    if ! rclone "${rclone_opts[@]}" copyto "$archive" "$remote_path$archive_name"; then
        OFFSITE_ERROR='rclone copyto thất bại (mạng, credential hoặc quota).'
        return 1
    fi

    # Upload "thành công" mà file rỗng hoặc cụt là kịch bản tệ nhất: tưởng có
    # backup nhưng không có. Đối chiếu kích thước thay vì tin vào mã thoát.
    local remote_size
    remote_size="$(rclone "${rclone_opts[@]}" size --json "$remote_path$archive_name" 2>/dev/null \
        | tr -d ' \n' | sed -n 's/.*"bytes":\([0-9]*\).*/\1/p')"
    local local_size
    local_size="$(stat -c '%s' "$archive" 2>/dev/null)"

    if [[ -z "$remote_size" ]]; then
        OFFSITE_ERROR='Đẩy xong nhưng không đọc lại được kích thước bản trên cloud.'
        return 1
    fi
    if [[ "$remote_size" != "$local_size" ]]; then
        OFFSITE_ERROR="Kích thước lệch: local $local_size byte, cloud $remote_size byte."
        return 1
    fi
    printf 'Đã xác minh bản trên cloud: %s byte.\n' "$remote_size"

    # Dọn bản cũ trên cloud theo TUỔI. Lỗi ở bước này không làm hỏng backup —
    # cùng lắm là tốn thêm dung lượng lưu trữ — nên chỉ cảnh báo trong log.
    if [[ "$OFFSITE_KEEP_DAYS" =~ ^[1-9][0-9]*$ ]]; then
        rclone "${rclone_opts[@]}" delete --min-age "${OFFSITE_KEEP_DAYS}d" \
            --include 'xanax-backup-*.tar.gz' "$remote_path" \
            || printf 'Cảnh báo: không dọn được bản cũ trên cloud.\n' >&2
    fi
    return 0
}

archive_name="$(basename -- "$archive")"
OFFSITE_ERROR=''
OFFSITE_STATUS='bỏ qua (chưa cấu hình OFFSITE_REMOTE)'

if [[ -n "$OFFSITE_REMOTE" ]]; then
    if ! command -v rclone >/dev/null 2>&1; then
        OFFSITE_ERROR='Đã cấu hình OFFSITE_REMOTE nhưng máy không có rclone.'
    elif [[ ! -r "$RCLONE_CONFIG" ]]; then
        OFFSITE_ERROR="Không đọc được cấu hình rclone: $RCLONE_CONFIG"
    elif ! push_offsite; then
        : "${OFFSITE_ERROR:=Đẩy off-site thất bại không rõ nguyên nhân.}"
    fi

    if [[ -n "$OFFSITE_ERROR" ]]; then
        OFFSITE_STATUS="THẤT BẠI — $OFFSITE_ERROR"
    else
        OFFSITE_STATUS="đã đẩy lên $OFFSITE_REMOTE"
    fi
fi

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
printf 'Off-site: %s\n' "$OFFSITE_STATUS"

# Thành công thì im lặng — cảnh báo chỉ có giá trị khi nó hiếm. Việc "backup đã
# chạy đúng giờ hay chưa" do xanax-backup-freshness lo, không phải tin nhắn mỗi ngày.
if [[ -n "$OFFSITE_ERROR" ]]; then
    archive_size="$(du -h -- "$archive" 2>/dev/null | cut -f1)"
    notify crit 'Backup Xanax chưa ra khỏi VPS' \
        "Bản local ĐÃ tạo xong và vẫn dùng được:
  $archive ($archive_size)

Nhưng bước đẩy ra ngoài thất bại:
  $OFFSITE_ERROR

Chừng nào chưa sửa, mất VPS là mất luôn dữ liệu.
Chạy tay để xem lỗi đầy đủ: sudo /usr/local/sbin/xanax-backup"
    # Mã riêng để phân biệt với "backup hỏng hoàn toàn"; cleanup dựa vào mã này
    # để không gửi tin nhắn thứ hai.
    exit 75
fi
