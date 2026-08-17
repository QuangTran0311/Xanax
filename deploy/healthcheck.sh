#!/usr/bin/env bash
# Giám sát ngoài cho Xanax. Cài thành: /usr/local/sbin/xanax-healthcheck
# Chạy 5 phút một lần qua xanax-healthcheck.timer.
#
# Restart=always chỉ cứu được crash lẻ. Nó không cứu được: app sống nhưng
# database hỏng, worker pool chết, Caddy tắt, chứng chỉ hết hạn, DNS sai. Script
# này bắt những thứ đó và là nguồn cảnh báo duy nhất khi web chết lúc bạn không
# ngồi trước máy.

set -uo pipefail

MONITOR_ENV="${MONITOR_ENV:-/etc/xanax/monitor.env}"
NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
STATE_DIR="${STATE_DIR:-/var/lib/xanax}"

if [[ -r "$MONITOR_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$MONITOR_ENV"
fi
: "${HEALTH_URL_LOCAL:=http://127.0.0.1:8000/api/health/ready}"
: "${HEALTH_URL_PUBLIC:=}"
: "${HEALTH_FAIL_THRESHOLD:=2}"
[[ "$HEALTH_FAIL_THRESHOLD" =~ ^[1-9][0-9]*$ ]] || HEALTH_FAIL_THRESHOLD=2

notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

mkdir -p "$STATE_DIR" 2>/dev/null || true
state_file="$STATE_DIR/health.state"

# ── Kiểm tra ───────────────────────────────────────────────────────────────
problems=''

add_problem() {
    problems+="$1"$'\n'
}

# /api/health/ready trả 503 khi chưa sẵn sàng nên --fail là đủ để bắt lỗi. Vẫn
# đọc body vì nó liệt kê đúng thành phần nào hỏng (database/orchestrator/
# scheduler/task_queue) — thông tin đó đáng giá hơn nhiều so với "không 200".
local_body="$(curl --silent --show-error --max-time 20 \
    --write-out '\nHTTP_CODE=%{http_code}' "$HEALTH_URL_LOCAL" 2>&1)"
local_code="$(printf '%s' "$local_body" | sed -n 's/.*HTTP_CODE=\([0-9]*\)$/\1/p')"

if [[ "$local_code" != "200" ]]; then
    add_problem "Loopback $HEALTH_URL_LOCAL trả mã '${local_code:-không kết nối được}':
$(printf '%s' "$local_body" | head -c 600)"
elif ! printf '%s' "$local_body" | grep -q '"ready":[[:space:]]*true'; then
    # Phòng trường hợp readiness đổi cách trả mã trong tương lai: 200 mà
    # ready=false vẫn phải tính là hỏng.
    add_problem "Loopback trả 200 nhưng ready không phải true:
$(printf '%s' "$local_body" | head -c 600)"
fi

if [[ -n "$HEALTH_URL_PUBLIC" ]]; then
    # Đường công khai đi qua DNS → Caddy → TLS → app. Hỏng ở đây mà loopback vẫn
    # xanh nghĩa là vấn đề nằm ở proxy/chứng chỉ/DNS chứ không phải ở app.
    public_out="$(curl --silent --show-error --max-time 25 \
        --output /dev/null --write-out '%{http_code}' "$HEALTH_URL_PUBLIC" 2>&1)"
    if [[ "$public_out" != "200" ]]; then
        add_problem "Đường công khai $HEALTH_URL_PUBLIC không trả 200: $public_out
(Loopback bình thường mà đường này hỏng thì nghi Caddy, chứng chỉ TLS hoặc DNS.)"
    fi
fi

# ── Máy trạng thái chống spam ──────────────────────────────────────────────
# Không có phần này thì mỗi 5 phút một tin nhắn, và bạn sẽ tắt thông báo trong
# hai ngày — đúng lúc cảnh báo trở nên vô dụng.
#
# File state: "<trạng thái> <số lần hỏng liên tiếp>"
#   ok      — đang bình thường
#   failing — đang hỏng nhưng chưa đủ ngưỡng để báo
#   alerted — đã gửi cảnh báo, im lặng cho tới khi phục hồi
prev_status='ok'
prev_fails=0
if [[ -r "$state_file" ]]; then
    read -r prev_status prev_fails <"$state_file" 2>/dev/null || true
    [[ "$prev_fails" =~ ^[0-9]+$ ]] || prev_fails=0
    [[ -n "$prev_status" ]] || prev_status='ok'
fi

write_state() {
    printf '%s %s\n' "$1" "$2" >"$state_file" 2>/dev/null || true
}

if [[ -n "$problems" ]]; then
    fails=$(( prev_fails + 1 ))
    if [[ "$prev_status" == "alerted" ]]; then
        # Đã báo rồi, vẫn đang hỏng — im lặng, chỉ ghi log.
        printf 'Vẫn hỏng (lần %d), đã cảnh báo trước đó.\n' "$fails" >&2
        write_state alerted "$fails"
    elif (( fails >= HEALTH_FAIL_THRESHOLD )); then
        notify crit 'Xanax KHÔNG phản hồi' \
"Hỏng $fails lần kiểm tra liên tiếp.

$problems
systemctl status xanax
journalctl -u xanax -n 50"
        write_state alerted "$fails"
    else
        printf 'Hỏng lần %d, chưa đủ ngưỡng %d.\n' "$fails" "$HEALTH_FAIL_THRESHOLD" >&2
        write_state failing "$fails"
    fi
    exit 1
fi

# Chỉ báo phục hồi khi trước đó thực sự đã gửi cảnh báo — nếu không, mỗi lần
# trục trặc thoáng qua lại sinh ra một tin "đã phục hồi" chẳng ai cần.
if [[ "$prev_status" == "alerted" ]]; then
    notify info 'Xanax đã phục hồi' \
"Dịch vụ phản hồi bình thường trở lại sau $prev_fails lần kiểm tra hỏng."
fi
write_state ok 0
exit 0
