#!/usr/bin/env bash
# Dead-man switch cho backup. Cài thành: /usr/local/sbin/xanax-backup-freshness
# Chạy hằng ngày qua xanax-backup-freshness.timer.
#
# TẠI SAO CẦN, khi backup.sh đã tự gửi cảnh báo lúc thất bại:
# vì chế độ hỏng nguy hiểm nhất không phải là backup chạy rồi lỗi — mà là backup
# KHÔNG CHẠY. Timer bị disable sau một lần nghịch systemd, script bị OOM giết
# (trap EXIT không chạy khi bị SIGKILL), máy tắt đúng giờ backup. Trong mọi tình
# huống đó không có gì "thất bại" cả, nên không có gì báo. Sáu tháng sau mới phát
# hiện bản backup mới nhất là từ tháng Ba.
#
# Script này không quan tâm backup chạy thế nào. Nó chỉ hỏi đúng một câu: bản
# mới nhất có còn mới không — cả ở local lẫn trên cloud.

set -uo pipefail

MONITOR_ENV="${MONITOR_ENV:-/etc/xanax/monitor.env}"
BACKUP_ENV="${BACKUP_ENV:-/etc/xanax/backup.env}"
NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
STATE_DIR="${STATE_DIR:-/var/lib/xanax}"

if [[ -r "$MONITOR_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$MONITOR_ENV"
fi
if [[ -r "$BACKUP_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$BACKUP_ENV"
fi
: "${BACKUP_MAX_AGE_HOURS:=36}"
: "${BACKUP_DIR:=/var/backups/xanax}"
: "${BACKUP_CHECK_OFFSITE:=1}"
: "${OFFSITE_REMOTE:=}"
: "${RCLONE_CONFIG:=/root/.config/rclone/rclone.conf}"
export RCLONE_CONFIG

notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

mkdir -p "$STATE_DIR" 2>/dev/null || true
state_file="$STATE_DIR/backup-freshness.state"

max_age_seconds=$(( BACKUP_MAX_AGE_HOURS * 3600 ))
now_epoch="$(date +%s)"
problems=''
summary=''

human_age() {
    local seconds="$1"
    printf '%d giờ %d phút' $(( seconds / 3600 )) $(( (seconds % 3600) / 60 ))
}

# ── Bản local ──────────────────────────────────────────────────────────────
newest_local="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'xanax-backup-*.tar.gz' \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 1)"

if [[ -z "$newest_local" ]]; then
    problems+="Không tìm thấy bản backup nào trong $BACKUP_DIR."$'\n'
else
    local_epoch="${newest_local%% *}"
    local_epoch="${local_epoch%%.*}"
    local_file="${newest_local#* }"
    local_age=$(( now_epoch - local_epoch ))
    local_size="$(du -h -- "$local_file" 2>/dev/null | cut -f1)"
    summary+="Local: $(basename -- "$local_file") ($local_size), $(human_age "$local_age") trước."$'\n'

    if (( local_age > max_age_seconds )); then
        problems+="Bản backup local mới nhất đã $(human_age "$local_age") tuổi, quá ngưỡng ${BACKUP_MAX_AGE_HOURS}h.
  $local_file"$'\n'
    fi

    # File 0 byte hoặc bé bất thường nghĩa là backup tạo ra rác. Ngưỡng 1 KB chỉ
    # để bắt trường hợp rỗng hẳn, không phải để đoán kích thước hợp lý.
    local_bytes="$(stat -c '%s' "$local_file" 2>/dev/null || echo 0)"
    if (( local_bytes < 1024 )); then
        problems+="Bản backup local mới nhất chỉ có $local_bytes byte — gần như chắc chắn là file hỏng."$'\n'
    fi
fi

# ── Bản trên cloud ─────────────────────────────────────────────────────────
if [[ "$BACKUP_CHECK_OFFSITE" == "1" && -n "$OFFSITE_REMOTE" ]]; then
    if ! command -v rclone >/dev/null 2>&1; then
        problems+='Đã bật kiểm tra off-site nhưng máy không có rclone.'$'\n'
    elif [[ ! -r "$RCLONE_CONFIG" ]]; then
        problems+="Không đọc được cấu hình rclone: $RCLONE_CONFIG"$'\n'
    else
        remote_path="$OFFSITE_REMOTE"
        [[ "$remote_path" == *: || "$remote_path" == */ ]] || remote_path="$remote_path/"

        # `lsf --format tp` cho "<thời gian>;<tên>"; sort ngược lấy bản mới nhất.
        newest_remote="$(rclone --config "$RCLONE_CONFIG" lsf --files-only \
            --format tp --separator ';' \
            --include 'xanax-backup-*.tar.gz' "$remote_path" 2>/dev/null \
            | sort -r | head -n 1)"

        if [[ -z "$newest_remote" ]]; then
            problems+="Không thấy bản backup nào trên $remote_path (hoặc không kết nối được)."$'\n'
        else
            remote_time="${newest_remote%%;*}"
            remote_name="${newest_remote#*;}"
            remote_epoch="$(date -d "$remote_time" +%s 2>/dev/null || echo 0)"
            if (( remote_epoch == 0 )); then
                problems+="Không đọc được thời gian bản backup trên cloud: $newest_remote"$'\n'
            else
                remote_age=$(( now_epoch - remote_epoch ))
                summary+="Cloud: $remote_name, $(human_age "$remote_age") trước."$'\n'
                if (( remote_age > max_age_seconds )); then
                    problems+="Bản backup trên cloud mới nhất đã $(human_age "$remote_age") tuổi, quá ngưỡng ${BACKUP_MAX_AGE_HOURS}h.
Backup có thể vẫn chạy nhưng không còn ra khỏi VPS được."$'\n'
                fi
            fi
        fi
    fi
fi

# ── Báo cáo, chỉ khi đổi trạng thái ────────────────────────────────────────
prev_status='ok'
if [[ -r "$state_file" ]]; then
    read -r prev_status <"$state_file" 2>/dev/null || prev_status='ok'
    [[ -n "$prev_status" ]] || prev_status='ok'
fi

if [[ -n "$problems" ]]; then
    if [[ "$prev_status" != "stale" ]]; then
        notify crit 'Backup Xanax không còn mới' \
"$problems
$summary
Chạy tay để kiểm tra: sudo /usr/local/sbin/xanax-backup
Xem lịch: systemctl list-timers xanax-backup.timer"
    else
        printf 'Vẫn cũ, đã cảnh báo trước đó — im lặng.\n' >&2
    fi
    printf 'stale\n' >"$state_file" 2>/dev/null || true
    printf '%s' "$problems" >&2
    exit 1
fi

if [[ "$prev_status" == "stale" ]]; then
    notify info 'Backup Xanax đã bình thường trở lại' "$summary"
fi
printf 'ok\n' >"$state_file" 2>/dev/null || true
printf '%s' "$summary"
exit 0
