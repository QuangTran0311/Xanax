#!/usr/bin/env bash
# Kiểm tra credential của Claude/Codex CLI. Cài thành:
# /usr/local/sbin/xanax-provider-check
# Chạy một lần mỗi ngày qua xanax-provider-check.timer.
#
# Readiness chỉ biết app, database và worker còn sống. Credential CLI hết hạn
# thì bốn đèn đó vẫn xanh trong khi mọi agent đều gãy; probe này gọi
# thật từng entry CLI để bắt đúng chế độ hỏng đó.

set -uo pipefail

MONITOR_ENV="${MONITOR_ENV:-/etc/xanax/monitor.env}"
NOTIFY_BIN="${NOTIFY_BIN:-/usr/local/sbin/xanax-notify}"
STATE_DIR="${STATE_DIR:-/var/lib/xanax}"

if [[ -r "$MONITOR_ENV" ]]; then
    # shellcheck disable=SC1090
    source "$MONITOR_ENV"
fi
: "${PROVIDER_URL:=http://127.0.0.1:8000/api/health/providers}"
: "${PROVIDER_HUB_ENV:=/opt/xanax/backend/.env}"
: "${PROVIDER_MAX_TIME_SECONDS:=45}"
[[ "$PROVIDER_MAX_TIME_SECONDS" =~ ^[1-9][0-9]*$ ]] || PROVIDER_MAX_TIME_SECONDS=45

notify() {
    [[ -x "$NOTIFY_BIN" ]] || return 0
    "$NOTIFY_BIN" "$@" || true
}

mkdir -p "$STATE_DIR" 2>/dev/null || true
state_file="$STATE_DIR/provider.state"

prev_status='ok'
if [[ -r "$state_file" ]]; then
    read -r prev_status <"$state_file" 2>/dev/null || prev_status='ok'
    [[ -n "$prev_status" ]] || prev_status='ok'
fi

write_state() {
    printf '%s\n' "$1" >"$state_file" 2>/dev/null || true
}

response_file="$(mktemp)" || exit 1
error_file="$(mktemp)" || {
    rm -f -- "$response_file"
    exit 1
}
curl_config="$(mktemp)" || {
    rm -f -- "$response_file" "$error_file"
    exit 1
}
chmod 0600 "$response_file" "$error_file" "$curl_config" 2>/dev/null || true
trap 'rm -f -- "$response_file" "$error_file" "$curl_config"' EXIT

problems=''
failed_entries=''
provider_total=''

# Không source backend/.env: systemd EnvironmentFile chấp nhận nhiều giá trị có thể
# làm hỏng cú pháp shell. Chỉ đọc đúng dòng key cần dùng; -f2- giữ
# nguyên phần sau nếu giá trị có dấu '='.
api_key=''
if [[ ! -r "$PROVIDER_HUB_ENV" ]]; then
    problems="Không đọc được file cấu hình app: $PROVIDER_HUB_ENV"
else
    api_key="$(grep -m 1 '^HUB_API_KEY=' "$PROVIDER_HUB_ENV" 2>/dev/null \
        | cut -d= -f2- | tr -d '\r')"
    if [[ -z "$api_key" ]]; then
        problems="Không tìm thấy HUB_API_KEY trong $PROVIDER_HUB_ENV"
    elif [[ ! "$api_key" =~ ^[A-Za-z0-9._~-]+$ ]]; then
        # Runbook sinh key bằng secrets.token_urlsafe(). Từ chối ký tự lạ để
        # chúng không thể chèn thêm chỉ thị vào file config của curl.
        problems='HUB_API_KEY có định dạng không an toàn cho probe'
    fi
fi

if [[ -z "$problems" ]]; then
    # Không đặt X-API-Key trên command line: user khác có thể đọc argv qua ps.
    printf 'header = "X-API-Key: %s"\n' "$api_key" >"$curl_config"

    http_code="$(curl --silent --show-error --fail-with-body \
        --config "$curl_config" \
        --max-time "$PROVIDER_MAX_TIME_SECONDS" \
        --request POST \
        --output "$response_file" \
        --write-out '%{http_code}' \
        "$PROVIDER_URL" 2>"$error_file")"
    curl_rc=$?

    # Chỉ lấy tên entry hỏng. Trường `error` có nguồn từ stderr CLI và
    # tuy đã được API che bớt, vẫn không có lý do đẩy nó lên Telegram.
    failed_entries="$(python3.12 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    names = []
    for item in data.get("failures", []):
        name = " ".join(str(item.get("name", "entry không tên")).split())
        style = " ".join(str(item.get("api_style", "CLI")).split())
        names.append(f"{name} ({style})")
    print(", ".join(names)[:500])
except Exception:
    pass
' "$response_file" 2>/dev/null)"
    provider_total="$(python3.12 -c '
import json, sys
try:
    value = json.load(open(sys.argv[1], encoding="utf-8")).get("total")
    print(value if isinstance(value, int) and value >= 0 else "")
except Exception:
    pass
' "$response_file" 2>/dev/null)"

    if (( curl_rc != 0 )); then
        if [[ -n "$failed_entries" ]]; then
            problems="Endpoint báo credential/provider CLI hỏng (HTTP ${http_code:-503}).
Entry hỏng: $failed_entries"
        else
            curl_error="$(head -c 300 "$error_file" | tr '\r\n' ' ')"
            problems="Không gọi được provider probe (HTTP ${http_code:-không kết nối được}): ${curl_error:-curl thất bại}"
        fi
    elif [[ ! "$provider_total" =~ ^[0-9]+$ ]]; then
        problems='Provider probe trả 200 nhưng JSON không hợp lệ'
    elif ! grep -q '"ok"[[:space:]]*:[[:space:]]*true' "$response_file"; then
        problems='Provider probe trả 200 nhưng ok không phải true'
    fi
fi

# Pool rỗng (hoặc chỉ có API HTTP) không phải lỗi. Cố ý im lặng kể cả
# khi state cũ là alerted: không còn entry CLI thì không còn gì để báo phục hồi.
if [[ -z "$problems" && "$provider_total" == "0" ]]; then
    write_state ok
    printf 'Không có entry CLI nào, bỏ qua.\n'
    exit 0
fi

if [[ -n "$problems" ]]; then
    if [[ "$prev_status" == "alerted" ]]; then
        printf 'Provider CLI vẫn hỏng, đã cảnh báo trước đó — im lặng.\n' >&2
    else
        notify crit 'Credential CLI của Xanax không dùng được' \
"Agent có thể gãy dù /api/health/ready vẫn xanh.

$problems

Cách sửa: mở shell dưới đúng user xanax, rồi chạy lệnh đăng nhập
tương ứng (chỉ cần chạy CLI đang hỏng):
sudo -u xanax -H bash
claude
codex login

Xong thì thoát shell và thử lại:
sudo /usr/local/sbin/xanax-provider-check"
    fi
    write_state alerted
    printf '%s\n' "$problems" >&2
    exit 1
fi

if [[ "$prev_status" == "alerted" ]]; then
    notify info 'Credential CLI của Xanax đã phục hồi' \
"Provider probe đã thử thành công $provider_total entry CLI."
fi
write_state ok
printf 'Provider CLI bình thường: %s entry.\n' "$provider_total"
exit 0
