#!/usr/bin/env bash
# Cảnh báo khi ổ sắp đầy. Cài thành: /usr/local/sbin/xanax-disk-check
# Chạy hằng ngày qua xanax-diskcheck.timer.
#
# Ổ đầy là một trong vài cách hiếm hoi làm HỎNG dữ liệu chứ không chỉ làm dừng
# dịch vụ: SQLite ghi giữa chừng mà hết chỗ, backup tạo ra file cụt. Với ổ 60 GB
# và backup giữ 14 bản, chỗ trống tụt đi âm thầm chứ không đột ngột.

set -uo pipefail

MONITOR_ENV="${MONITOR_ENV:-/etc/xanax/monitor.env}"
NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
STATE_DIR="${STATE_DIR:-/var/lib/xanax}"

if [[ -r "$MONITOR_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$MONITOR_ENV"
fi
: "${DISK_WARN_PERCENT:=80}"
: "${DISK_CRIT_PERCENT:=90}"
: "${DISK_PATHS:=/opt/xanax /var/backups/xanax /var/log}"

notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

mkdir -p "$STATE_DIR" 2>/dev/null || true
state_file="$STATE_DIR/disk.state"

# Ai đang ăn chỗ — kèm vào cảnh báo để khỏi phải ssh vào máy mới biết dọn gì.
usage_detail() {
    printf 'Chi tiết dung lượng:\n'
    local target
    for target in /opt/xanax/backend/data /var/backups/xanax /var/log/caddy; do
        if [[ -e "$target" ]]; then
            printf '  %s\n' "$(du -sh -- "$target" 2>/dev/null || printf '?  %s' "$target")"
        fi
    done
    local journal_size
    journal_size="$(journalctl --disk-usage 2>/dev/null | tail -n 1)"
    if [[ -n "$journal_size" ]]; then
        printf '  journald: %s\n' "$journal_size"
    fi
}

# State cũ: mỗi dòng "<mount point> <mức>".
prev_level_of() {
    if [[ ! -r "$state_file" ]]; then
        printf 'ok'
        return
    fi
    local found
    found="$(awk -v want="$1" '$1 == want { print $2 }' "$state_file" 2>/dev/null | tail -n 1)"
    printf '%s' "${found:-ok}"
}

new_state=''
alert_count=0

# Nhiều đường dẫn thường nằm trên cùng một filesystem. Gộp theo mount point để
# không gửi ba tin nhắn giống hệt nhau cho cùng một ổ.
seen_mounts=' '
for path in $DISK_PATHS; do
    [[ -e "$path" ]] || continue

    # `--output` không dùng chung được với `-P`. Lấy đúng dòng dữ liệu, bỏ header.
    read -r mount_point used_percent avail <<<"$(
        df --output=target,pcent,avail "$path" 2>/dev/null | tail -n 1 | tr -d '%'
    )"
    [[ -n "${mount_point:-}" && "${used_percent:-}" =~ ^[0-9]+$ ]] || continue
    case "$seen_mounts" in
        *" $mount_point "*) continue ;;
    esac
    seen_mounts+="$mount_point "

    if (( used_percent >= DISK_CRIT_PERCENT )); then
        level='crit'
    elif (( used_percent >= DISK_WARN_PERCENT )); then
        level='warn'
    else
        level='ok'
    fi
    new_state+="$mount_point $level"$'\n'

    prev="$(prev_level_of "$mount_point")"
    if [[ "$prev" == "$level" ]]; then
        continue
    fi

    # Chỉ báo khi mức độ ĐỔI. Nhờ vậy ổ nằm ở 82% suốt tuần chỉ sinh đúng một
    # tin nhắn, còn lúc nhảy từ warn lên crit thì vẫn báo ngay.
    avail_human="$(numfmt --to=iec --from-unit=1024 "$avail" 2>/dev/null || printf '%s KB' "$avail")"
    alert_count=$(( alert_count + 1 ))
    case "$level" in
        crit)
            notify crit "Ổ $mount_point còn rất ít chỗ" \
"Đã dùng ${used_percent}% (ngưỡng khẩn ${DISK_CRIT_PERCENT}%), còn trống ${avail_human}.

$(usage_detail)
Dọn nhanh: giảm KEEP_BACKUPS, xóa pre-restore-* cũ trong /var/backups/xanax,
hoặc journalctl --vacuum-size=200M"
            ;;
        warn)
            notify warn "Ổ $mount_point sắp đầy" \
"Đã dùng ${used_percent}% (ngưỡng cảnh báo ${DISK_WARN_PERCENT}%), còn trống ${avail_human}.

$(usage_detail)"
            ;;
        ok)
            notify info "Ổ $mount_point đã trở lại bình thường" \
"Đã dùng ${used_percent}%, còn trống ${avail_human}."
            ;;
    esac
    printf '%s: %s ở %s%%\n' "$level" "$mount_point" "$used_percent"
done

printf '%s' "$new_state" >"$state_file" 2>/dev/null || true

if (( alert_count == 0 )); then
    printf 'Dung lượng bình thường, không có thay đổi mức độ.\n'
fi
exit 0
