#!/usr/bin/env bash
# Báo Telegram khi một systemd unit rơi vào trạng thái failed.
# Cài thành: /usr/local/sbin/xanax-alert-unit-failed
# Được gọi tự động qua OnFailure=xanax-alert@%n.service, không gọi tay.
#
#   xanax-alert-unit-failed xanax.service

set -uo pipefail

NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
unit="${1:-<không rõ unit>}"

[[ -x "$NOTIFY_BIN" ]] || {
    printf 'Không có %s; bỏ qua cảnh báo cho %s\n' "$NOTIFY_BIN" "$unit" >&2
    exit 0
}

state="$(systemctl show -p ActiveState -p SubState -p Result -p NRestarts \
    --value "$unit" 2>/dev/null | tr '\n' ' ')"

# 30 dòng cuối thường đủ thấy traceback khiến app chết lúc khởi động.
tail_log="$(journalctl -u "$unit" -n 30 --no-pager 2>/dev/null)"

"$NOTIFY_BIN" crit "Unit $unit đã chết" \
"Trạng thái (ActiveState SubState Result NRestarts): $state

Nhật ký gần nhất:
$tail_log

Kiểm tra: systemctl status $unit
Khởi động lại: sudo systemctl restart $unit"

exit 0
