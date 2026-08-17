#!/usr/bin/env bash
# Gửi cảnh báo qua Telegram. Cài thành: /usr/local/sbin/xanax-notify
#
#   xanax-notify <mức độ> <tiêu đề> [nội dung...]
#   xanax-notify crit "Backup thất bại" "sqlite3 trả mã 74"
#
# Nội dung cũng có thể đưa qua stdin:
#   journalctl -u xanax -n 20 | xanax-notify warn "Service restart"
#
# Mức độ: info | warn | crit  (chỉ đổi tiền tố, không đổi cách gửi).
#
# NGUYÊN TẮC: script này KHÔNG BAO GIỜ được làm hỏng script gọi nó. Mọi lỗi —
# thiếu cấu hình, mất mạng, Telegram trả 4xx — đều chỉ ghi ra stderr rồi exit 0.
# Cảnh báo là thứ phụ trợ; nó không được phép biến một backup thành công thành
# một backup "thất bại".

set -uo pipefail

ALERT_ENV="${ALERT_ENV:-/etc/xanax/alert.env}"
CURL_TIMEOUT="${CURL_TIMEOUT:-15}"

log() {
    printf 'xanax-notify: %s\n' "$*" >&2
}

# Không dùng `exit 1` ở bất kỳ đâu — xem phần NGUYÊN TẮC ở đầu file.
give_up() {
    log "$*"
    log 'Bỏ qua việc gửi cảnh báo; script gọi vẫn tiếp tục bình thường.'
    exit 0
}

if (( $# < 2 )); then
    give_up 'Cách dùng: xanax-notify <info|warn|crit> <tiêu đề> [nội dung...]'
fi

level="$1"
title="$2"
shift 2
body="$*"

case "$level" in
    info) prefix='[INFO]' ;;
    warn) prefix='[CẢNH BÁO]' ;;
    crit) prefix='[KHẨN]' ;;
    *)    prefix='[?]' ;;
esac

command -v curl >/dev/null 2>&1 || give_up 'Không có curl trên máy.'

[[ -r "$ALERT_ENV" ]] || give_up "Không đọc được $ALERT_ENV — chưa cấu hình Telegram?"
# shellcheck disable=SC1090
source "$ALERT_ENV"

: "${TELEGRAM_BOT_TOKEN:=}"
: "${TELEGRAM_CHAT_ID:=}"
[[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]] \
    || give_up "Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong $ALERT_ENV"

host="${ALERT_HOSTNAME:-$(hostname -s 2>/dev/null || echo '?')}"
stamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"

# Không có nội dung ở tham số thì lấy từ stdin, nhưng chỉ khi stdin là pipe/file.
# Nếu chạy tay trong terminal mà đọc stdin thì script sẽ treo chờ gõ phím.
if [[ -z "$body" && ! -t 0 ]]; then
    body="$(cat)"
fi

payload_file="$(mktemp)" || give_up 'Không tạo được file tạm.'
chmod 0600 "$payload_file" 2>/dev/null || true
trap 'rm -f -- "$payload_file" "$payload_file.cut"' EXIT

{
    printf '%s %s\n' "$prefix" "$title"
    printf 'Máy: %s — %s\n' "$host" "$stamp"
    if [[ -n "$body" ]]; then
        printf '\n%s\n' "$body"
    fi
} >"$payload_file"

# Telegram chặn tin nhắn quá 4096 ký tự; 3500 byte là mức an toàn kể cả khi toàn
# bộ nội dung là tiếng Việt có dấu.
#
# `head -c` cắt theo BYTE nên có thể xé đôi một ký tự nhiều byte và tạo ra chuỗi
# UTF-8 hỏng ở cuối. `iconv -c` lọc bỏ đúng mẩu ký tự dở dang đó.
# (Đừng thay bằng `cut -c`: nó cắt theo từng DÒNG, không cắt cả file.)
if (( $(wc -c <"$payload_file") > 3500 )); then
    cut_file="$payload_file.cut"
    { head -c 3500 "$payload_file" | iconv -c -f UTF-8 -t UTF-8
      printf '\n…(đã cắt bớt)\n'
    } >"$cut_file" 2>/dev/null && mv -f -- "$cut_file" "$payload_file"
fi

# URL chứa bot token nên KHÔNG được đưa vào dòng lệnh: mọi user trên máy đều đọc
# được qua `ps aux`. Đẩy qua stdin dưới dạng file cấu hình của curl.
# Nội dung tin nhắn đi bằng `@file` để khỏi phải escape dấu nháy/xuống dòng.
# Cố ý KHÔNG dùng parse_mode: text thô của log hay chứa ký tự làm Markdown lỗi
# cú pháp, Telegram sẽ từ chối cả tin nhắn.
if ! printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TELEGRAM_BOT_TOKEN" \
    | curl --silent --show-error --config - \
        --max-time "$CURL_TIMEOUT" --retry 2 --retry-delay 3 \
        --output /dev/null --fail \
        --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
        --data-urlencode "disable_web_page_preview=true" \
        --data-urlencode "text@$payload_file"
then
    log "Gửi Telegram thất bại (tiêu đề: $title)."
fi

exit 0
