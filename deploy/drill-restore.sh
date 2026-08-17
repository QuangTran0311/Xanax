#!/usr/bin/env bash
# Diễn tập khôi phục. Cài thành: /usr/local/sbin/xanax-drill-restore
#
#   sudo xanax-drill-restore              # lấy bản mới nhất TRÊN CLOUD
#   sudo xanax-drill-restore --local      # lấy bản mới nhất ở /var/backups/xanax
#   sudo xanax-drill-restore --keep       # xong không dọn, để vào xem tận nơi
#   sudo xanax-drill-restore --teardown   # chỉ dọn bản diễn tập cũ rồi thoát
#
# "Backup chưa từng khôi phục thử thì chưa được tính là backup." Script này biến
# câu đó thành việc chạy được lặp lại, thay vì một lời hứa.
#
# ── NGUYÊN TẮC AN TOÀN ────────────────────────────────────────────────────
# Dữ liệu dạy AI trong database này là thứ không tái tạo được. Vì vậy diễn tập
# KHÔNG BAO GIỜ được chạm vào production. Cụ thể:
#
#   1. Chỉ ĐỌC production: file duy nhất được mở là /opt/xanax/.venv/bin/python
#      (interpreter) và database production ở chế độ read-only để đối chiếu số
#      bản ghi. Không ghi một byte nào vào /opt/xanax.
#   2. Không đụng vào xanax.service. Script kiểm tra service vẫn chạy ở đầu và
#      cuối, và báo lỗi nếu trạng thái thay đổi.
#   3. restore.sh được gọi với XANAX_RESTORE_MODE=drill; rào chắn trong đó sẽ
#      từ chối chạy nếu APP_ROOT hay SERVICE_NAME trỏ vào production.
#   4. Archive gốc không bao giờ bị động tới — luôn làm việc trên bản sao.

set -uo pipefail

DRILL_ROOT="${DRILL_ROOT:-/opt/xanax-drill}"
DRILL_SERVICE="${DRILL_SERVICE:-xanax-drill.service}"
DRILL_PORT="${DRILL_PORT:-8001}"
DRILL_WORK="${DRILL_WORK:-/var/tmp/xanax-drill}"

PROD_ROOT="${PROD_ROOT:-/opt/xanax}"
PROD_SERVICE="${PROD_SERVICE:-xanax.service}"
PROD_VENV_PY="${PROD_VENV_PY:-$PROD_ROOT/.venv/bin/python}"

RESTORE_BIN="${RESTORE_BIN:-/usr/local/sbin/xanax-restore}"
NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
PRE_START_BIN="${PRE_START_BIN:-/usr/local/sbin/xanax-drill-pre-start}"

BACKUP_ENV="${BACKUP_ENV:-/etc/xanax/backup.env}"
if [[ -r "$BACKUP_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$BACKUP_ENV"
fi
: "${OFFSITE_REMOTE:=}"
: "${RCLONE_CONFIG:=/root/.config/rclone/rclone.conf}"
: "${BACKUP_DIR:=/var/backups/xanax}"
export RCLONE_CONFIG

SOURCE='cloud'
KEEP=0
TEARDOWN_ONLY=0

while (( $# > 0 )); do
    case "$1" in
        --local)    SOURCE='local' ;;
        --cloud)    SOURCE='cloud' ;;
        --keep)     KEEP=1 ;;
        --teardown) TEARDOWN_ONLY=1 ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            printf 'Tham số không hiểu: %s\n' "$1" >&2
            exit 64
            ;;
    esac
    shift
done

notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

say() { printf '\n>>> %s\n' "$*"; }

fail() {
    local code="$1"
    shift
    printf 'LỖI: %s\n' "$*" >&2
    notify crit 'Diễn tập restore THẤT BẠI' \
"$*

Bản diễn tập còn ở $DRILL_ROOT để bạn xem xét.
Dọn khi xong: sudo xanax-drill-restore --teardown

Production KHÔNG bị ảnh hưởng — diễn tập không bao giờ ghi vào $PROD_ROOT."
    exit "$code"
}

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 77 "Phải chạy bằng root (sudo)."

# ── Dọn bản diễn tập ───────────────────────────────────────────────────────
teardown() {
    say 'Dọn bản diễn tập'
    systemctl stop "$DRILL_SERVICE" 2>/dev/null || true
    systemctl disable "$DRILL_SERVICE" 2>/dev/null || true

    # Xóa có rào: chỉ chấp nhận đúng đường dẫn drill đã cấu hình, và tuyệt đối
    # không phải production. `rm -rf` với biến rỗng là cách xóa nhầm cả ổ.
    local resolved
    resolved="$(readlink -f -- "$DRILL_ROOT" 2>/dev/null || printf '%s' "$DRILL_ROOT")"
    if [[ -n "$resolved" && "$resolved" != "/" \
        && "$resolved" != "$(readlink -f -- "$PROD_ROOT" 2>/dev/null)" \
        && "$resolved" == *xanax-drill* ]]; then
        rm -rf -- "$resolved"
        printf 'Đã xóa %s\n' "$resolved"
    else
        printf 'BỎ QUA việc xóa %s — không đạt điều kiện an toàn.\n' "$DRILL_ROOT" >&2
    fi

    if [[ "$DRILL_WORK" == *xanax-drill* ]]; then
        rm -rf -- "$DRILL_WORK"
    fi
    rm -f /etc/systemd/system/"$DRILL_SERVICE"
    systemctl daemon-reload
    printf 'Đã dọn xong bản diễn tập.\n'
}

if (( TEARDOWN_ONLY == 1 )); then
    teardown
    exit 0
fi

# ── Tiền kiểm ──────────────────────────────────────────────────────────────
say 'Tiền kiểm'

for command_name in systemctl curl sqlite3 tar git install readlink df awk ss du find sudo; do
    command -v "$command_name" >/dev/null 2>&1 \
        || fail 69 "Thiếu lệnh phụ thuộc: $command_name"
done

[[ -x "$RESTORE_BIN" ]]    || fail 66 "Không thấy $RESTORE_BIN — cài restore.sh trước."
[[ -x "$PRE_START_BIN" ]]  || fail 66 "Không thấy $PRE_START_BIN — cài drill-pre-start.sh trước."
[[ -x "$PROD_VENV_PY" ]]   || fail 66 "Không thấy interpreter production: $PROD_VENV_PY"
[[ -d "$PROD_ROOT/.git" ]] || fail 66 "$PROD_ROOT không phải một git repo."

prod_active_before="$(systemctl is-active "$PROD_SERVICE" 2>/dev/null || true)"
printf 'Production %s đang: %s\n' "$PROD_SERVICE" "$prod_active_before"
[[ "$prod_active_before" == "active" ]] \
    || fail 70 "Production không ở trạng thái active ($prod_active_before). Sửa production trước đã, đừng diễn tập lúc web đang hỏng."

# Cổng drill phải trống. Trùng cổng với production là hỏng cả hai.
if ss -ltn 2>/dev/null | grep -q ":$DRILL_PORT "; then
    fail 70 "Cổng $DRILL_PORT đã có người nghe. Dọn bản diễn tập cũ: sudo xanax-drill-restore --teardown"
fi

# Diễn tập cần chỗ cho một bản sao đầy đủ của database + data. Hết chỗ giữa
# chừng sẽ làm hỏng chính production (cùng filesystem), nên dừng sớm.
prod_data_kb="$(du -sk "$PROD_ROOT/backend/data" "$PROD_ROOT/backend/xanax.db" 2>/dev/null \
    | awk '{ total += $1 } END { print total + 0 }')"
avail_kb="$(df -k --output=avail "$(dirname -- "$DRILL_ROOT")" 2>/dev/null | tail -n 1 | tr -d ' ')"
needed_kb=$(( prod_data_kb * 3 + 262144 ))
if [[ "$avail_kb" =~ ^[0-9]+$ ]] && (( avail_kb < needed_kb )); then
    fail 70 "Không đủ chỗ cho diễn tập: cần ~$(( needed_kb / 1024 )) MB, còn $(( avail_kb / 1024 )) MB."
fi

# Bản diễn tập lần trước còn sót thì dọn trước khi làm lại.
if [[ -e "$DRILL_ROOT" ]]; then
    printf 'Phát hiện bản diễn tập cũ ở %s — dọn trước.\n' "$DRILL_ROOT"
    teardown
fi

# Quyền ở đây phải tính theo hai user khác nhau cùng dùng thư mục này:
#   - archive tải về CHỨA backend/.env, nên `incoming` chỉ root đọc được;
#   - còn bản diễn tập chạy bằng user `xanax` và ghi vào HERMES_HOME, nên `hermes`
#     phải thuộc xanax, và thư mục cha phải cho phép đi xuyên qua (0755).
install -d -m 0755 -o root -g root "$DRILL_WORK"
install -d -m 0700 -o root -g root "$DRILL_WORK/incoming"
install -d -m 0700 -o xanax -g xanax "$DRILL_WORK/hermes"

# ── Lấy archive ────────────────────────────────────────────────────────────
say "Lấy bản backup (nguồn: $SOURCE)"

archive=''
if [[ "$SOURCE" == "cloud" ]]; then
    [[ -n "$OFFSITE_REMOTE" ]] \
        || fail 64 "Chưa cấu hình OFFSITE_REMOTE trong $BACKUP_ENV. Dùng --local nếu muốn diễn tập với bản trên máy."
    command -v rclone >/dev/null 2>&1 || fail 69 "Không có rclone."

    remote_path="$OFFSITE_REMOTE"
    [[ "$remote_path" == *: || "$remote_path" == */ ]] || remote_path="$remote_path/"

    # Lấy bản mới nhất theo THỜI GIAN chứ không theo tên: nếu quy ước đặt tên
    # đổi trong tương lai, phép sắp xếp theo tên sẽ âm thầm chọn nhầm file.
    newest="$(rclone --config "$RCLONE_CONFIG" lsf --files-only \
        --format tp --separator ';' --include 'xanax-backup-*.tar.gz' \
        "$remote_path" 2>/dev/null | sort -r | head -n 1)"
    [[ -n "$newest" ]] || fail 66 "Không thấy bản backup nào trên $remote_path"
    remote_name="${newest#*;}"

    printf 'Bản mới nhất trên cloud: %s\n' "$remote_name"
    archive="$DRILL_WORK/incoming/$remote_name"
    rclone --config "$RCLONE_CONFIG" copyto "$remote_path$remote_name" "$archive" \
        || fail 74 "Không tải được archive từ cloud."
    # Tải được về và giải nén được chính là phép thử cho cả đường off-site lẫn
    # passphrase của remote crypt. Đây là nửa quan trọng nhất của diễn tập.
    printf 'Đã tải về: %s\n' "$archive"
else
    newest_local="$(find "$BACKUP_DIR" -maxdepth 1 -type f \
        -name 'xanax-backup-*.tar.gz' -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -n 1)"
    [[ -n "$newest_local" ]] || fail 66 "Không thấy bản backup nào trong $BACKUP_DIR"
    source_file="${newest_local#* }"
    archive="$DRILL_WORK/incoming/$(basename -- "$source_file")"
    # Làm việc trên BẢN SAO: restore.sh không được phép động vào archive gốc.
    cp -- "$source_file" "$archive" || fail 74 "Không sao chép được archive."
    printf 'Dùng bản local: %s\n' "$source_file"
fi

say 'Kiểm tra archive'
tar -tzf "$archive" >/dev/null || fail 65 "Archive hỏng: không giải nén thử được."
printf 'Archive giải nén thử được.\n'

# ── Dựng bản diễn tập ──────────────────────────────────────────────────────
say 'Dựng bản diễn tập'

# Mọi lệnh git ở đây chạy dưới user `xanax`, KHÔNG phải root. Lý do: /opt/xanax
# thuộc user xanax, và git từ chối làm việc với repo của người khác
# ("detected dubious ownership") — chạy bằng root sẽ gãy, hoặc tệ hơn là gãy âm
# thầm khi stderr bị chặn. Chạy đúng chủ sở hữu vừa hết lỗi, vừa khỏi phải thêm
# ngoại lệ safe.directory vào cấu hình toàn máy.
prod_commit="$(sudo -u xanax git -C "$PROD_ROOT" rev-parse HEAD 2>/dev/null || echo '')"

# Clone từ chính bản production trên máy: không cần mạng, không cần deploy key,
# và chắc chắn cùng commit với thứ đang chạy thật. Thư mục đích được tạo trước
# và thuộc xanax để user đó ghi được vào /opt.
install -d -m 0755 -o xanax -g xanax "$DRILL_ROOT" \
    || fail 73 "Không tạo được $DRILL_ROOT"
sudo -u xanax git clone --quiet --no-hardlinks "$PROD_ROOT" "$DRILL_ROOT" \
    || fail 74 "Không clone được mã nguồn sang $DRILL_ROOT"
if [[ -n "$prod_commit" ]]; then
    sudo -u xanax git -C "$DRILL_ROOT" checkout --quiet "$prod_commit" 2>/dev/null || true
fi
chown -R xanax:xanax "$DRILL_ROOT"
printf 'Đã dựng %s tại commit %s\n' "$DRILL_ROOT" "${prod_commit:0:8}"

install -m 0644 "$PROD_ROOT/deploy/xanax-drill.service" \
    /etc/systemd/system/"$DRILL_SERVICE" \
    || fail 73 "Không cài được unit diễn tập."
systemctl daemon-reload

# ── Chạy restore thật ──────────────────────────────────────────────────────
say 'Chạy restore.sh (chế độ drill)'

APP_ROOT="$DRILL_ROOT" \
SERVICE_NAME="$DRILL_SERVICE" \
ROLLBACK_ROOT="$DRILL_WORK/rollback" \
HEALTH_URL="http://127.0.0.1:$DRILL_PORT/api/health" \
XANAX_RESTORE_MODE=drill \
XANAX_RESTORE_ASSUME_YES=1 \
PRE_START_HOOK="$PRE_START_BIN" \
    "$RESTORE_BIN" "$archive" \
    || fail 70 "restore.sh thất bại ở chế độ drill."

# ── Nghiệm thu ─────────────────────────────────────────────────────────────
say 'Nghiệm thu'

drill_db="$DRILL_ROOT/backend/xanax.db"
prod_db="$PROD_ROOT/backend/xanax.db"
report=''

ready_body="$(curl --silent --max-time 30 --retry 10 --retry-delay 2 \
    --retry-connrefused "http://127.0.0.1:$DRILL_PORT/api/health/ready" 2>&1)"
if printf '%s' "$ready_body" | grep -q '"ready":[[:space:]]*true'; then
    report+='readiness: ĐẠT (đủ 4 check)'$'\n'
    printf 'Readiness: ĐẠT\n'
else
    fail 70 "Bản khôi phục khởi động nhưng readiness KHÔNG đạt:
$ready_body"
fi

integrity="$(sqlite3 "$drill_db" 'PRAGMA integrity_check;' 2>&1 | head -n 1)"
if [[ "$integrity" == "ok" ]]; then
    report+='integrity_check: ok'$'\n'
    printf 'Integrity check: ok\n'
else
    fail 70 "PRAGMA integrity_check trên bản khôi phục trả về: $integrity"
fi

# Đối chiếu số bản ghi với production. Một archive cụt vẫn có thể mở được và vẫn
# trả integrity ok — chỉ so số lượng mới phát hiện được nó thiếu dữ liệu.
# Production được mở READ-ONLY qua URI `?mode=ro`: không tạo WAL, không ghi gì.
say 'Đối chiếu số bản ghi với production'
# `-readonly` là cách chắc chắn nhất để mở database production mà không ghi gì:
# không tạo journal, không tạo WAL, không đổi mtime. `.timeout` để không bung ra
# lỗi "database is locked" chỉ vì production đang ghi đúng lúc đó.
count_prod() {
    sqlite3 -readonly -cmd '.timeout 5000' "$prod_db" \
        "SELECT COUNT(*) FROM $1;" 2>/dev/null || printf 'n/a'
}
count_drill() {
    sqlite3 -cmd '.timeout 5000' "$drill_db" \
        "SELECT COUNT(*) FROM $1;" 2>/dev/null || printf 'n/a'
}
mismatch=0
for table in agent_configs training_sessions training_messages skills projects \
             workflow_tasks knowledge_documents meetings meeting_messages xanax_notes; do
    prod_count="$(count_prod "$table")"
    drill_count="$(count_drill "$table")"
    marker='='
    if [[ "$prod_count" != "$drill_count" ]]; then
        marker='≠'
        mismatch=$(( mismatch + 1 ))
    fi
    line="$(printf '  %-22s prod=%-8s drill=%-8s %s' "$table" "$prod_count" "$drill_count" "$marker")"
    printf '%s\n' "$line"
    report+="$line"$'\n'
done

# Lệch KHÔNG phải là lỗi: backup chụp lúc 2 giờ sáng, production chạy tiếp cả
# ngày nên đương nhiên nhiều hơn. Đây là số để bạn nhìn và thấy nó hợp lý.
if (( mismatch > 0 )); then
    printf '\nCó %d bảng lệch số — bình thường nếu backup được tạo trước đó khá lâu.\n' "$mismatch"
    printf 'Chỉ đáng lo khi bản drill lệch NHIỀU hoặc bằng 0 ở bảng đáng ra phải có dữ liệu.\n'
fi

# ── Production vẫn nguyên vẹn? ─────────────────────────────────────────────
prod_active_after="$(systemctl is-active "$PROD_SERVICE" 2>/dev/null || true)"
if [[ "$prod_active_after" != "active" ]]; then
    fail 70 "NGHIÊM TRỌNG: production chuyển từ '$prod_active_before' sang '$prod_active_after' trong lúc diễn tập."
fi
printf '\nProduction %s: vẫn %s — không bị ảnh hưởng.\n' "$PROD_SERVICE" "$prod_active_after"

archive_label="$(basename -- "$archive")"
say 'Diễn tập ĐẠT'
notify info 'Diễn tập restore ĐẠT' \
"Archive: $archive_label (nguồn: $SOURCE)

$report
Production $PROD_SERVICE: vẫn active, không bị ảnh hưởng."

if (( KEEP == 1 )); then
    printf '\nGiữ bản diễn tập lại theo yêu cầu (--keep).\n'
    printf 'Xem tại: http://127.0.0.1:%s (ssh -L %s:127.0.0.1:%s ...)\n' \
        "$DRILL_PORT" "$DRILL_PORT" "$DRILL_PORT"
    printf 'Dọn khi xong: sudo xanax-drill-restore --teardown\n'
else
    teardown
fi

exit 0
