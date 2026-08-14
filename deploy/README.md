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

## 6. Vận hành

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
sudo tee /etc/systemd/system/xanax-backup.service >/dev/null <<'EOF'
[Unit]
Description=Backup Xanax

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/xanax-backup
EOF

sudo tee /etc/systemd/system/xanax-backup.timer >/dev/null <<'EOF'
[Unit]
Description=Chạy backup Xanax hằng ngày

[Timer]
OnCalendar=*-*-* 02:17:00
RandomizedDelaySec=5m
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now xanax-backup.timer
systemctl list-timers xanax-backup.timer
```

Restore bắt buộc hỏi xác nhận, tự dừng/start service, đặt lại owner/quyền và gọi
`/api/health`:

```bash
sudo /usr/local/sbin/xanax-restore \
  /var/backups/xanax/xanax-backup-YYYYMMDDTHHMMSSZ.tar.gz
```

Dữ liệu trước restore được giữ trong
`/var/backups/xanax/pre-restore-<timestamp>`; chỉ xóa sau khi nghiệm thu. Ít nhất
mỗi quý phải restore thử một archive lên máy tách biệt. Backup chưa từng restore
thử thì chưa được tính là backup.

### Log và dung lượng

```bash
sudo journalctl -u xanax.service -f
sudo journalctl -u caddy -f
sudo tail -f /var/log/caddy/xanax-access.log
df -h /opt/xanax /var/backups/xanax
du -sh /opt/xanax/backend/data /var/backups/xanax
```

Với ổ 60 GB, đặt cảnh báo khi filesystem đạt 80%; từ 90% coi là khẩn cấp. Kiểm
tra cả `backend/data`, backup, journald và access log. Caddy xoay access log ở
20 MiB, giữ tối đa 10 file/30 ngày; backup giữ theo số lượng ở đầu script.

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

## Không làm

- Không chạy nhiều uvicorn worker/process: SQLite, scheduler và hàng đợi nội bộ
  không hỗ trợ scale ngang.
- Không chạy Xanax bằng root.
- Không mở/public cổng 8000; chỉ Caddy được nghe Internet trên 80/443.
- Không đổi hoặc làm mất `XANAX_SECRET_KEY` sau khi đã lưu token skill.
