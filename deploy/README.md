# Triển khai Xanax trên Ubuntu 24.04

Runbook này dành cho một VPS Ubuntu 24.04 LTS x86_64, cài mã nguồn tại
`/opt/xanax` và chạy bằng user hệ thống `xanax`:

```text
Internet → DNS → Caddy :443 → Xanax/FastAPI 127.0.0.1:8000 → SQLite + backend/data
```

Chỉ chạy **một process uvicorn**. Các lệnh dưới đây giả định domain là
`xanax.example.com`; thay bằng domain thật ở mọi chỗ. Nếu đổi `/opt/xanax`, phải
sửa đồng bộ đường dẫn trong `xanax.service`, script backup/restore và các lệnh.

## 1. Chuẩn bị máy

Đăng nhập bằng SSH key trong một phiên đang mở. Cập nhật hệ thống và cài các gói
nền; nếu hệ thống yêu cầu reboot thì reboot trước khi đi tiếp:

Image của nhà cung cấp có thể trỏ APT tới mirror ở nước khác, chẳng hạn
`de.archive.ubuntu.com`, trong khi DNS chỉ trả địa chỉ IPv6 nhưng VPS không có IPv6.
Khi đó `apt update` sẽ treo đến timeout ở gần như mọi gói. Nhận biết bằng HTTP code
`000`/timeout từ mirror, kết quả `getent hosts` chỉ có IPv6 và không có địa chỉ IPv6
global trên máy:

```bash
curl -sS -o /dev/null --connect-timeout 5 -w '%{http_code}\n' \
  http://de.archive.ubuntu.com/ubuntu/
getent hosts de.archive.ubuntu.com
ip -6 addr show scope global
```

Đổi mirror theo quốc gia trong `/etc/apt/sources.list.d/ubuntu.sources` sang mirror
chung và buộc APT dùng IPv4:

```bash
sudo sed -i -E \
  's#(https?://)[a-z]{2}\.archive\.ubuntu\.com/ubuntu/?#\1archive.ubuntu.com/ubuntu/#g' \
  /etc/apt/sources.list.d/ubuntu.sources
printf '%s\n' 'Acquire::ForceIPv4 "true";' \
  | sudo tee /etc/apt/apt.conf.d/99force-ipv4
sudo apt update
```

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ca-certificates curl git gnupg openssh-server \
  python3.12 python3.12-venv sqlite3 ufw
sudo useradd --system --create-home --home-dir /home/xanax \
  --shell /bin/bash xanax
```

Nếu user đã tồn tại, `useradd` sẽ báo lỗi; kiểm tra bằng `id xanax` rồi đi tiếp.

Frontend hiện dùng Vite 8, cần Node `^20.19` hoặc `>=22.12`. Ubuntu 24.04 mặc
định không bảo đảm mức này, nên cài Node.js 22 từ repo NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh
sudo -E bash /tmp/nodesource_setup.sh
rm /tmp/nodesource_setup.sh
sudo apt install -y nodejs
node --version
npm --version
```

Cài Caddy stable từ repo chính thức của Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
caddy version
```

`deploy/Caddyfile` dùng `request_body`, cần Caddy 2.10 trở lên. Repo stable ở
trên cung cấp bản hiện hành; không tiếp tục nếu `caddy validate` ở bước 4 báo
không nhận directive này.

Chỉ mở SSH, HTTP và HTTPS. Chạy `ufw enable` khi phiên SSH hiện tại vẫn còn mở:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Tắt đăng nhập SSH bằng mật khẩu. **Trước khi reload**, xác nhận public key đã nằm
trong `authorized_keys`; sau khi reload, mở một cửa sổ mới và thử đăng nhập bằng
key rồi mới đóng phiên hiện tại:

```bash
printf '%s\n' \
  'PasswordAuthentication no' \
  'KbdInteractiveAuthentication no' \
  'PermitRootLogin prohibit-password' \
  | sudo tee /etc/ssh/sshd_config.d/00-xanax-hardening.conf
sudo sshd -t
sudo systemctl reload ssh
sudo sshd -T | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin) '
```

Cuối cùng, tạo bản ghi DNS `A` trỏ domain về IPv4 của VPS. Chỉ tạo `AAAA` nếu
VPS thật sự có IPv6 và UFW đã cho 80/443 trên IPv6. Chờ DNS phân giải đúng trước
khi bật Caddy để việc cấp chứng chỉ TLS không thất bại.

## 2. Lấy mã nguồn và build

Thay `THAY_BANG_URL_REPO` bằng URL thật:

```bash
sudo install -d -m 0755 -o xanax -g xanax /opt/xanax
sudo -u xanax git clone 'THAY_BANG_URL_REPO' /opt/xanax

sudo -u xanax python3.12 -m venv /opt/xanax/.venv
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install --upgrade pip
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install \
  -r /opt/xanax/backend/requirements.txt

sudo -u xanax bash -lc 'cd /opt/xanax/frontend && npm ci && npm run build'
test -f /opt/xanax/frontend/dist/index.html
```

Không chạy `npm run dev` trên server. FastAPI phục vụ trực tiếp
`frontend/dist/` sau khi build.

## 3. Tạo cấu hình production

Sinh từng secret trên VPS rồi lưu ngay trong trình quản lý mật khẩu. Hai lệnh
đầu dùng cho `HUB_SECRET_KEY` và `HUB_API_KEY`; lệnh cuối sinh đúng khóa 32 byte
base64 mà `XANAX_SECRET_KEY` yêu cầu:

```bash
/opt/xanax/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
/opt/xanax/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
/opt/xanax/.venv/bin/python -c 'import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
/opt/xanax/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Lệnh thứ tư có thể dùng làm mật khẩu admin đầu tiên. Tạo file chỉ user `xanax`
đọc được:

```bash
sudo install -m 0600 -o xanax -g xanax /dev/null /opt/xanax/backend/.env
sudo -u xanax nano /opt/xanax/backend/.env
```

Nội dung production tối thiểu; thay toàn bộ giá trị trong dấu `<...>`:

```dotenv
HUB_HOST=127.0.0.1
HUB_PORT=8000
HUB_DEBUG=false
HUB_SECRET_KEY=<secret-ngau-nhien-thu-nhat>
HUB_API_KEY=<secret-ngau-nhien-thu-hai>
HUB_COOKIE_SECURE=true
HUB_TRUST_PROXY_HEADERS=true
HUB_TASK_WORKER_COUNT=2
XANAX_SECRET_KEY=<khoa-base64-32-byte>
XANAX_ADMIN_USER=<ten-admin>
XANAX_ADMIN_PASS=<mat-khau-admin-manh>
XANAX_NO_BROWSER=1
```

`HUB_TASK_WORKER_COUNT=2` là số worker của **hàng đợi nội bộ**, không phải uvicorn
worker. Service vẫn chỉ có đúng một process uvicorn.

> **Đừng viết chú thích ở cuối dòng trong file `.env` này.** systemd đọc nó qua
> `EnvironmentFile` và **không** cắt phần `# ...` phía sau giá trị — dòng
> `HUB_PORT=8000  # cổng backend` sẽ cho ra cổng là chuỗi `8000  # cổng backend`
> và service chết với lỗi khó đoán. Chú thích phải nằm trên dòng riêng.

> **Không được đổi `XANAX_SECRET_KEY` sau lần dùng đầu tiên.** Khóa này mã hóa
> token/API key của skill. Mất hoặc đổi khóa sẽ làm toàn bộ secret đã lưu không
> thể giải mã; không có cách khôi phục ngoài nhập lại từng token. Backup phải giữ
> cả `backend/.env` và `backend/data`.

Khi `HUB_DEBUG=false`, app **cố ý từ chối khởi động** nếu
`HUB_SECRET_KEY`/`HUB_API_KEY` còn mặc định; nếu database chưa có user, mật khẩu
admin mặc định `xanax` cũng bị từ chối. Đây là hàng rào an toàn, không phải lỗi
uvicorn.

## 4. Cài systemd và Caddy

Unit mẫu dùng `/opt/xanax`. Nếu dùng đường khác, sửa tất cả placeholder trước khi
cài:

```bash
sudo install -m 0644 /opt/xanax/deploy/xanax.service \
  /etc/systemd/system/xanax.service
sudo systemctl daemon-reload
sudo systemctl enable --now xanax.service
sudo systemctl status xanax.service --no-pager
sudo journalctl -u xanax.service -n 100 --no-pager
```

App phải chỉ nghe loopback:

```bash
sudo ss -ltnp | grep ':8000'
```

Kết quả phải là `127.0.0.1:8000`, không phải `0.0.0.0:8000`.

Unit gốc của gói Caddy đặt `ProtectSystem=full`, vì vậy `/var/log` là chỉ-đọc đối với
service. Chỉ tạo `/var/log/caddy` chưa đủ: phải cho phép unit ghi đúng thư mục này
bằng systemd drop-in, nếu không Caddy chết ngay khi khởi động với `permission denied`.

Thay domain trong Caddyfile, chuẩn bị thư mục access log và drop-in rồi validate
trước khi reload:

```bash
sudo cp /opt/xanax/deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/xanax\.example\.com/domain-that.example/' /etc/caddy/Caddyfile
sudo install -d -m 0750 -o caddy -g caddy /var/log/caddy
sudo install -d -m 0755 /etc/systemd/system/caddy.service.d
printf '%s\n' '[Service]' 'ReadWritePaths=/var/log/caddy' \
  | sudo tee /etc/systemd/system/caddy.service.d/override.conf
sudo systemctl daemon-reload
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo chown -R caddy:caddy /var/log/caddy
sudo systemctl enable --now caddy
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

> **Đặc biệt kiểm tra owner của access log.** Nếu trước đó đã chạy `caddy validate`
> hoặc `caddy run` bằng root, file `/var/log/caddy/xanax-access.log` có thể đã được
> tạo với owner `root:root` và mode `0600`. Khi service chạy bằng user `caddy`, nó
> không mở được file; triệu chứng vẫn là `permission denied` dù drop-in đã đúng.
> Sửa bằng `sudo chown -R caddy:caddy /var/log/caddy`, rồi restart Caddy.

Thay `domain-that.example` bằng domain thật ngay trong lệnh. Caddy tự cấp/gia hạn
TLS, tự proxy WebSocket và mặc định tự đặt `X-Forwarded-For`,
`X-Forwarded-Proto`, `X-Forwarded-Host`. Vì thế Caddyfile **không** có matcher
WebSocket hoặc `header_up` thủ công. `HUB_TRUST_PROXY_HEADERS=true` chỉ an toàn vì
port 8000 không public và Caddy là proxy trực tiếp duy nhất.

## 5. Nghiệm thu

Đặt domain một lần cho các lệnh kiểm tra:

```bash
DOMAIN='domain-that.example'
curl -fsS "https://$DOMAIN/api/health" | python3.12 -m json.tool
curl -fsS "https://$DOMAIN/api/health/ready" | python3.12 -m json.tool
curl -sS -o /dev/null -w '%{http_code}\n' "https://$DOMAIN/api/docs"
```

Yêu cầu đạt:

- `/api/health` trả HTTP 200 và `status: "ok"`.
- `/api/health/ready` trả HTTP 200, `ready: true`, đủ bốn check
  `database`, `orchestrator`, `scheduler`, `task_queue` đều `true`.
- `/api/docs` trả 404 khi production; 200 nghĩa là `HUB_DEBUG` chưa thật sự
  `false`.
- Mở `https://domain`, đăng nhập được và F5 vẫn giữ phiên trong thời gian phiên
  còn hiệu lực.
- Mở DevTools → Network → WS, vào một màn hình chat/họp/task và xác nhận kết nối
  `wss://domain/ws/...` nhận status `101 Switching Protocols` rồi có frame qua
  lại.

Không nghiệm thu bằng `http://IP:8000`; đường đó không được public và cookie
`Secure` sẽ không hoạt động qua HTTP.

## 6. Cảnh báo và giám sát

`Restart=always` chỉ cứu được crash lẻ. Nó không cứu được app sống mà database
hỏng, worker pool chết, Caddy tắt, chứng chỉ hết hạn, ổ đầy, hay backup lặng lẽ
ngừng chạy. Phần này dựng lớp phát hiện cho những thứ đó. **Làm trước mục backup
off-site**, vì backup dùng chính kênh cảnh báo này khi thất bại.

### 6.1. Bot Telegram

Nhắn `@BotFather` → `/newbot` → lấy token. Nhắn cho bot mới một câu bất kỳ, rồi
lấy `chat_id`:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3.12 -m json.tool
```

Đọc `result[].message.chat.id`. Cất token vào trình quản lý mật khẩu, rồi:

```bash
sudo install -d -m 0750 -o root -g root /etc/xanax
sudo install -m 0600 -o root -g root /opt/xanax/deploy/alert.env.example \
  /etc/xanax/alert.env
sudo nano /etc/xanax/alert.env
sudo install -m 0644 -o root -g root /opt/xanax/deploy/monitor.env.example \
  /etc/xanax/monitor.env
sudo sed -i 's/xanax\.example\.com/domain-that.example/' /etc/xanax/monitor.env
```

`alert.env` chứa bot token nên bắt buộc `0600` owner root. `monitor.env` không
có secret nên `0644`.

### 6.2. Cài script và timer

```bash
sudo install -m 0750 -o root -g root /opt/xanax/deploy/notify.sh \
  /usr/local/sbin/xanax-notify
sudo install -m 0750 -o root -g root /opt/xanax/deploy/alert-unit-failed.sh \
  /usr/local/sbin/xanax-alert-unit-failed
sudo install -m 0750 -o root -g root /opt/xanax/deploy/healthcheck.sh \
  /usr/local/sbin/xanax-healthcheck
sudo install -m 0750 -o root -g root /opt/xanax/deploy/disk-check.sh \
  /usr/local/sbin/xanax-disk-check
sudo install -m 0750 -o root -g root /opt/xanax/deploy/backup-freshness.sh \
  /usr/local/sbin/xanax-backup-freshness

sudo install -d -m 0750 -o root -g root /var/lib/xanax

for unit in xanax-alert@.service \
            xanax-healthcheck.service xanax-healthcheck.timer \
            xanax-diskcheck.service xanax-diskcheck.timer \
            xanax-backup-freshness.service xanax-backup-freshness.timer; do
  sudo install -m 0644 "/opt/xanax/deploy/$unit" "/etc/systemd/system/$unit"
done
sudo systemctl daemon-reload
```

Thử kênh cảnh báo **trước** khi bật timer — không có tin nhắn nào tới thì mọi
thứ phía sau chỉ là trang trí:

```bash
sudo /usr/local/sbin/xanax-notify info 'Thử kênh cảnh báo' 'Nếu đọc được dòng này thì Telegram đã thông.'
```

Chạy tay từng script một lần rồi mới bật timer:

```bash
sudo /usr/local/sbin/xanax-healthcheck
sudo /usr/local/sbin/xanax-disk-check

sudo systemctl enable --now xanax-healthcheck.timer
sudo systemctl enable --now xanax-diskcheck.timer
sudo systemctl enable --now xanax-backup-freshness.timer
systemctl list-timers 'xanax*'
```

### 6.3. Cảnh báo khi service chết

`deploy/xanax.service` đã có sẵn `OnFailure=xanax-alert@%n.service` và nới
`StartLimitIntervalSec=300` / `StartLimitBurst=10`. Mặc định của systemd là 5
lần khởi động trong 10 giây — vượt ngưỡng thì unit **nằm chết vĩnh viễn**, và
với `RestartSec=5s` thì một trục trặc tạm thời cũng đủ đốt hết hạn mức đó. Cài
lại unit sau khi cập nhật mã nguồn:

```bash
sudo install -m 0644 /opt/xanax/deploy/xanax.service /etc/systemd/system/xanax.service
sudo systemctl daemon-reload
sudo systemctl restart xanax.service
```

Kiểm tra đường cảnh báo hoạt động thật, bằng cách ép service chết:

```bash
sudo systemctl kill --signal=SIGKILL xanax.service
```

`Restart=always` sẽ dựng lại ngay nên web chỉ gián đoạn vài giây; muốn thấy tin
nhắn `OnFailure` thì dùng `systemctl stop` rồi sửa tạm `ExecStart` thành đường
dẫn sai — nhớ trả lại như cũ.

### 6.4. Giới hạn dung lượng journald

Mặc định journald được phép ăn 10% filesystem — trên ổ 60 GB là khoảng 6 GB, và
nó phình dần một cách âm thầm vì Xanax ghi toàn bộ output của CLI vào journal:

```bash
sudo install -d -m 0755 /etc/systemd/journald.conf.d
sudo install -m 0644 /opt/xanax/deploy/journald-xanax.conf \
  /etc/systemd/journald.conf.d/99-xanax.conf
sudo systemctl restart systemd-journald
journalctl --disk-usage
```

### 6.5. Cảnh báo im lặng lúc nào

Cả ba script đều có máy trạng thái chống spam trong `/var/lib/xanax`:

- healthcheck chỉ báo sau **2 lần hỏng liên tiếp**, im lặng suốt thời gian hỏng,
  và báo **đúng một lần** khi phục hồi.
- disk-check chỉ báo khi **mức độ thay đổi** (ok → warn → crit), nên ổ nằm ở 82%
  cả tuần chỉ sinh một tin nhắn.
- backup-freshness chỉ báo lần đầu phát hiện backup cũ.

Đây là chủ đích: cảnh báo mỗi 5 phút thì trong hai ngày bạn sẽ tắt thông báo —
đúng lúc chúng trở nên vô dụng. Muốn buộc gửi lại thì xóa file state tương ứng.

## 7. Vận hành

Cài script root-owned ở mục **Backup và restore** ngay sau lần deploy đầu tiên,
trước lần cập nhật đầu tiên.

### Khi nhà cung cấp đổi IP máy chủ

Sửa bản ghi DNS `A` của domain sang IPv4 mới ngay. Nếu DNS còn trỏ IP cũ,
Let's Encrypt vẫn kết nối tới máy cũ và Caddy sẽ báo lỗi dạng
`<ip-cu>: Timeout during connect (likely firewall problem)` khi xin chứng chỉ.
Hỏi thẳng nameserver gốc thay vì chỉ tin cache của resolver địa phương:

```bash
nslookup domain-that.example ns1.nameserver.example
```

Khi nameserver gốc đã trả IP mới, yêu cầu Caddy xin lại chứng chỉ ngay thay vì chờ
backoff:

```bash
sudo systemctl restart caddy
sudo journalctl -u caddy -n 100 --no-pager
```

### Cập nhật phiên bản

Backup trước, rồi pull fast-forward, cập nhật dependency, build lại frontend và
restart đúng một service:

```bash
sudo /usr/local/sbin/xanax-backup
sudo -u xanax git -C /opt/xanax pull --ff-only
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install \
  -r /opt/xanax/backend/requirements.txt
sudo -u xanax bash -lc 'cd /opt/xanax/frontend && npm ci && npm run build'
sudo systemctl restart xanax.service
curl -fsS --retry 15 --retry-delay 2 --retry-connrefused \
  http://127.0.0.1:8000/api/health/ready | python3.12 -m json.tool
```

Nếu đợt cập nhật có thay đổi file trong `deploy/`, cài lại unit/script tương ứng,
chạy `systemctl daemon-reload`, validate Caddyfile rồi mới reload Caddy.

### Backup và restore

Cài script thành bản root-owned để cron/timer chạy root không thực thi file do
user ứng dụng có quyền sửa:

```bash
sudo install -m 0750 -o root -g root /opt/xanax/deploy/backup.sh \
  /usr/local/sbin/xanax-backup
sudo install -m 0750 -o root -g root /opt/xanax/deploy/restore.sh \
  /usr/local/sbin/xanax-restore
sudo /usr/local/sbin/xanax-backup
sudo ls -lh /var/backups/xanax/
```

Mặc định giữ 14 bản gần nhất. Có thể đổi khi chạy, ví dụ
`sudo KEEP_BACKUPS=30 /usr/local/sbin/xanax-backup`. Database được sao lưu bằng
SQLite `.backup`, không copy file đang ghi. Archive còn chứa toàn bộ
`backend/data` và `backend/.env`.

Gắn lịch hằng ngày bằng systemd timer:

```bash
sudo install -m 0644 /opt/xanax/deploy/xanax-backup.service \
  /etc/systemd/system/xanax-backup.service
sudo install -m 0644 /opt/xanax/deploy/xanax-backup.timer \
  /etc/systemd/system/xanax-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now xanax-backup.timer
systemctl list-timers xanax-backup.timer
```

Hai unit này trước đây được tạo bằng heredoc ngay trong runbook; giờ chúng là
file trong `deploy/` để cài lại được và để sửa đổi đi qua Git. Nội dung giữ
nguyên lịch cũ (02:17 + `RandomizedDelaySec=5m`).

Restore bắt buộc hỏi xác nhận, tự dừng/start service, đặt lại owner/quyền và gọi
`/api/health`:

```bash
sudo /usr/local/sbin/xanax-restore \
  /var/backups/xanax/xanax-backup-YYYYMMDDTHHMMSSZ.tar.gz
```

Dữ liệu trước restore được giữ trong
`/var/backups/xanax/pre-restore-<timestamp>`; chỉ xóa sau khi nghiệm thu.

> **Rào chắn chống restore nhầm.** `restore.sh` mặc định trỏ vào production, nên
> quên đặt biến lúc diễn tập là ghi đè thẳng lên dữ liệu thật. Script yêu cầu
> `XANAX_RESTORE_MODE` là `production` hoặc `drill`, và bắt `APP_ROOT` với
> `SERVICE_NAME` phải khớp cặp: chế độ `drill` từ chối chạy nếu một trong hai
> trỏ vào production, chế độ `production` từ chối chạy nếu chúng lệch nhau.
> Chuỗi xác nhận cũng khác nhau (`KHOI PHUC` với production, `DIEN TAP` với diễn
> tập) để việc gõ không thành phản xạ.

### Đẩy backup ra ngoài VPS

Backup nằm cùng ổ với dữ liệu gốc không chống được hỏng ổ hay mất VPS. Bước này
đẩy mỗi bản lên object storage ngay sau khi tạo.

**Trước hết, mã hóa.** Archive chứa `backend/.env`, tức là chứa
`XANAX_SECRET_KEY`. Đẩy nguyên bản lên cloud là mang khóa giải mã toàn bộ token
skill ra khỏi tầm kiểm soát. Vì vậy cấu hình **hai** remote và chỉ dùng cái thứ
hai:

```bash
sudo apt install -y rclone
sudo rclone config     # tạo remote `r2` kiểu s3 (provider Cloudflare)
sudo rclone config     # tạo remote `r2crypt` kiểu crypt, remote = r2:xanax-backup
```

> **Passphrase của remote crypt phải vào trình quản lý mật khẩu ngay lúc tạo.**
> Nó chỉ nằm trong `/root/.config/rclone/rclone.conf` trên VPS — mà mất VPS
> chính là kịch bản backup off-site sinh ra để phòng. Mất passphrase thì toàn bộ
> bản trên cloud thành rác không giải mã được. Cất nó cạnh `XANAX_SECRET_KEY`.

```bash
sudo install -m 0600 -o root -g root /opt/xanax/deploy/backup.env.example \
  /etc/xanax/backup.env
sudo nano /etc/xanax/backup.env
sudo /usr/local/sbin/xanax-backup
sudo rclone --config /root/.config/rclone/rclone.conf ls r2crypt:
```

Không có `/etc/xanax/backup.env` thì `backup.sh` chạy y như cũ và chỉ bỏ qua
bước off-site — máy dev không bị gãy vì thiếu rclone.

Mã thoát của `xanax-backup` có ý nghĩa riêng:

| Mã | Nghĩa |
|----|-------|
| 0 | Backup local xong, off-site xong (hoặc chưa cấu hình off-site) |
| 75 | Backup local **vẫn tốt**, nhưng chưa đẩy ra ngoài được |
| khác | Backup thất bại, không có bản mới |

Cả hai trường hợp lỗi đều gửi Telegram, và mỗi trường hợp chỉ gửi **một** tin.
Local giữ theo **số lượng** (`KEEP_BACKUPS`), cloud giữ theo **tuổi**
(`OFFSITE_KEEP_DAYS`).

Backup chạy nhưng bị SIGKILL giữa chừng thì `trap` không kịp gửi cảnh báo, và
timer bị disable thì chẳng có gì "thất bại" để mà báo. `xanax-backup-freshness`
ở mục 6 bắt đúng hai lỗ hổng đó bằng cách hỏi một câu khác hẳn: bản mới nhất —
cả local lẫn trên cloud — có còn mới hơn 36 giờ không.

### Diễn tập khôi phục

**Backup chưa từng khôi phục thử thì chưa được tính là backup.** `drill-restore.sh`
biến câu đó thành việc chạy được lặp lại: nó tải bản mới nhất **từ cloud** về,
dựng một bản Xanax thứ hai ở `/opt/xanax-drill` chạy trên cổng 8001, restore vào
đó, rồi nghiệm thu tự động.

Nhờ lấy từ cloud, mỗi lần diễn tập kiểm chứng luôn cả đường off-site lẫn
passphrase của remote crypt — không chỉ kiểm tra file tar.

```bash
sudo install -m 0750 -o root -g root /opt/xanax/deploy/drill-restore.sh \
  /usr/local/sbin/xanax-drill-restore
sudo install -m 0750 -o root -g root /opt/xanax/deploy/drill-pre-start.sh \
  /usr/local/sbin/xanax-drill-pre-start

sudo /usr/local/sbin/xanax-drill-restore            # lấy bản mới nhất trên cloud
sudo /usr/local/sbin/xanax-drill-restore --local    # hoặc bản trong /var/backups
sudo /usr/local/sbin/xanax-drill-restore --keep     # xong không dọn, để vào xem
sudo /usr/local/sbin/xanax-drill-restore --teardown # dọn bản diễn tập
```

Diễn tập **không bao giờ ghi vào production**. Cụ thể:

- Chỉ đọc `/opt/xanax`: interpreter `.venv/bin/python` dùng chung ở chế độ đọc,
  và database production mở bằng `sqlite3 -readonly` để đối chiếu số bản ghi.
- Không đụng `xanax.service`. Script kiểm tra service vẫn `active` ở đầu và cuối,
  và báo lỗi nghiêm trọng nếu trạng thái đổi.
- `restore.sh` được gọi ở chế độ `drill`, nên rào chắn của nó sẽ chặn ngay nếu có
  gì đó trỏ nhầm về production.
- Archive gốc không bị động tới; script luôn làm việc trên bản sao.
- Bản diễn tập chạy với `PATH` **không có** `claude`/`codex`, và
  `drill-pre-start.sh` tắt toàn bộ lịch workflow trong bản sao trước khi service
  khởi động.

Điểm cuối quan trọng hơn vẻ ngoài của nó: lúc khởi động,
`api/routes/workflow.py::restore_schedules()` đọc database và đăng ký lại mọi cron
workflow đang bật. Bản diễn tập dùng đúng database của production, nên để nguyên
là nó sẽ tự chạy workflow thật — gọi CLI, đốt token, ghi ra ngoài. Diễn tập phải
là quan sát viên, không được hành động.

Script tự nghiệm thu bốn thứ và gửi kết quả qua Telegram:

1. `/api/health/ready` trên cổng 8001 trả `ready: true` với đủ bốn check.
2. `PRAGMA integrity_check` trên database vừa khôi phục trả `ok`.
3. Số bản ghi của 10 bảng quan trọng, đặt cạnh production để so.
4. Production vẫn `active` sau khi diễn tập xong.

Số bản ghi **lệch là bình thường** — backup chụp lúc 2 giờ sáng còn production
chạy tiếp cả ngày. Chỉ đáng lo khi bản diễn tập lệch rất nhiều, hoặc bằng 0 ở
bảng đáng ra phải có dữ liệu.

Chạy diễn tập ngay sau khi dựng xong off-site, rồi **ít nhất mỗi quý một lần**.
Nên chạy lại sau mỗi lần đổi schema database hoặc đổi nội dung archive.

### Log và dung lượng

```bash
sudo journalctl -u xanax.service -f
sudo journalctl -u caddy -f
sudo tail -f /var/log/caddy/xanax-access.log
df -h /opt/xanax /var/backups/xanax
du -sh /opt/xanax/backend/data /var/backups/xanax
```

Với ổ 60 GB, cảnh báo ở 80% và coi 90% là khẩn cấp — `xanax-diskcheck.timer` ở
mục 6 làm việc này tự động và gửi kèm `du` của những thư mục ăn chỗ nhiều nhất.
Caddy xoay access log ở 20 MiB, giữ tối đa 10 file/30 ngày; journald bị chặn ở
500 MB bởi drop-in ở mục 6.4; backup giữ theo số lượng ở đầu script.

### Các timer đang chạy

```bash
systemctl list-timers 'xanax*'
```

| Timer | Lịch | Việc | Báo Telegram khi |
|-------|------|------|------------------|
| `xanax-backup` | 02:17 hằng ngày | Backup local + đẩy lên cloud | Backup hỏng, hoặc không ra khỏi VPS được |
| `xanax-healthcheck` | mỗi 5 phút | Gọi `/api/health/ready` (loopback) và `/api/health` (công khai) | Hỏng 2 lần liên tiếp; và một lần khi phục hồi |
| `xanax-backup-freshness` | 09:00 hằng ngày | Bản backup mới nhất còn mới hơn 36h không, cả local lẫn cloud | Backup cũ quá ngưỡng, hoặc file cụt |
| `xanax-diskcheck` | 08:30 hằng ngày | Dung lượng các filesystem | Vượt 80%, vượt 90%, hoặc trở lại bình thường |

Ngoài timer còn có `OnFailure=xanax-alert@%n.service` gắn trên `xanax.service`,
bắn ngay khi service rơi vào trạng thái failed.

Kiểm tra nhanh trạng thái toàn bộ lớp giám sát:

```bash
systemctl list-timers 'xanax*' --no-pager
cat /var/lib/xanax/health.state /var/lib/xanax/disk.state \
    /var/lib/xanax/backup-freshness.state
```

## Hỏng thì xem đây trước

### Service chết ngay khi startup

```bash
sudo systemctl status xanax.service --no-pager
sudo journalctl -u xanax.service -n 150 --no-pager
sudo -u xanax /opt/xanax/.venv/bin/python /opt/xanax/backend/main.py
```

Nếu log có dòng bắt đầu như sau thì `.env` production vẫn không an toàn:

```text
RuntimeError: Không thể khởi động production. Cấu hình không an toàn: HUB_SECRET_KEY vẫn là giá trị mặc định; hãy đặt một secret mạnh; HUB_API_KEY vẫn là giá trị mặc định; hãy đặt một API key mạnh; database chưa có người dùng và XANAX_ADMIN_PASS chưa được đặt hoặc vẫn là 'xanax'; hãy đặt mật khẩu quản trị mạnh.
```

Thông báo thực tế có thể chỉ chứa một phần tùy biến nào đang sai. Sửa
`backend/.env`; không bật lại debug để né kiểm tra. Kiểm tra service đọc đúng file:

```bash
sudo stat /opt/xanax/backend/.env
sudo systemctl restart xanax.service
```

### Đăng nhập xong lại mất phiên

Production phải dùng `HUB_COOKIE_SECURE=true` và truy cập bằng
`https://domain`. Cookie `Secure` không được trình duyệt gửi qua `http://IP`.
Kiểm tra DNS, chứng chỉ và Caddy; không hạ `HUB_COOKIE_SECURE=false` để chữa tạm
trên Internet.

### Rate limit đăng nhập tính mọi người chung một IP

Đặt `HUB_TRUST_PROXY_HEADERS=true` khi và chỉ khi Caddy đứng trước app. Caddy v2
tự tạo `X-Forwarded-For` an toàn khi nó là proxy Internet đầu tiên; không cần
`header_up`. Đồng thời xác nhận UFW không public 8000 và `HUB_HOST=127.0.0.1`.

### App không tìm thấy `claude` hoặc `codex`

systemd không nạp `.profile` như phiên SSH. Kiểm tra đúng PATH của unit:

```bash
sudo -u xanax -H env \
  PATH='/opt/xanax/.venv/bin:/home/xanax/.local/bin:/home/xanax/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
  sh -c 'command -v claude; command -v codex'
```

CLI và credential phải được cài/đăng nhập dưới chính user `xanax`, ví dụ chạy
shell quản trị bằng `sudo -u xanax -H bash`. Nếu binary nằm ở thư mục khác, thêm
thư mục đó vào dòng `Environment="PATH=..."` của unit, rồi `daemon-reload` và
restart. `ProtectHome=false` là có chủ ý để CLI đọc cấu hình trong `/home/xanax`.

### `Permission denied` khi ghi database hoặc `backend/data`

```bash
sudo chown -R xanax:xanax /opt/xanax/backend/data
sudo chown xanax:xanax /opt/xanax/backend/xanax.db /opt/xanax/backend/.env
sudo chmod -R u+rwX,go-rwx /opt/xanax/backend/data
sudo chmod 0600 /opt/xanax/backend/xanax.db /opt/xanax/backend/.env
sudo -u xanax test -w /opt/xanax/backend/data
sudo -u xanax test -w /opt/xanax/backend/xanax.db
```

`ProtectSystem=full` không khóa `/opt`; đừng đổi thành `strict` nếu chưa thêm
ngoại lệ write path chính xác.

### Caddy không cấp được TLS hoặc trả 502

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo journalctl -u caddy -n 150 --no-pager
getent ahosts domain-that.example
curl -v http://127.0.0.1:8000/api/health
```

TLS thường hỏng vì DNS chưa trỏ đúng hoặc 80/443 bị chặn; 502 thường là service
Xanax chưa chạy hoặc nghe sai host/port.

### Không nhận được cảnh báo nào

Thử thẳng kênh gửi trước, rồi mới nghi tới script gọi nó:

```bash
sudo /usr/local/sbin/xanax-notify info 'Thử' 'kiểm tra kênh'
sudo stat -c '%a %U' /etc/xanax/alert.env      # phải là 600 root
sudo journalctl -u xanax-healthcheck.service -n 30 --no-pager
```

`notify.sh` cố ý **luôn thoát 0** và chỉ ghi lý do ra stderr — cảnh báo không
được phép biến một backup thành công thành backup thất bại. Vì vậy lỗi cấu hình
Telegram chỉ hiện trong journal của unit gọi nó, không làm gì đổ vỡ.

### Nhận quá nhiều cảnh báo trùng nhau

Xem file state; nếu nó không tồn tại hoặc không ghi được thì máy trạng thái
chống spam mất tác dụng và mỗi lần chạy sẽ báo lại:

```bash
sudo ls -l /var/lib/xanax/
sudo install -d -m 0750 -o root -g root /var/lib/xanax
```

### Diễn tập restore thất bại

```bash
sudo journalctl -u xanax-drill.service -n 100 --no-pager
sudo systemctl is-active xanax.service     # production phải vẫn active
sudo /usr/local/sbin/xanax-drill-restore --teardown
```

Bản diễn tập được giữ nguyên khi thất bại để còn xem xét; `--teardown` dọn nó
đi. Production không bị ảnh hưởng trong mọi trường hợp — diễn tập không ghi vào
`/opt/xanax`.

Lỗi hay gặp: cổng 8001 còn bị bản diễn tập lần trước chiếm (chạy `--teardown`),
hoặc không đủ chỗ trống trên ổ (script kiểm tra trước và dừng sớm).

## Không làm

- Không chạy nhiều uvicorn worker/process: SQLite, scheduler và hàng đợi nội bộ
  không hỗ trợ scale ngang.
- Không chạy Xanax bằng root.
- Không mở/public cổng 8000; chỉ Caddy được nghe Internet trên 80/443.
- Không đổi hoặc làm mất `XANAX_SECRET_KEY` sau khi đã lưu token skill.
- Không đẩy backup lên cloud mà không mã hóa: archive chứa `backend/.env`.
- Không làm mất passphrase của remote crypt — cất cùng chỗ với
  `XANAX_SECRET_KEY`.
- Không chạy `restore.sh` để diễn tập mà quên `XANAX_RESTORE_MODE=drill`; dùng
  `xanax-drill-restore` thay vì gọi tay.
- Không enable `xanax-drill.service`: nó chỉ được sống trong lúc diễn tập.
