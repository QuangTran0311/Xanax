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

Tạo swapfile 4 GiB trước khi build hoặc chạy service. Gói VPS quảng cáo 8 GB có
MemTotal thật `8131780 kB` (khoảng 7,75 GiB); không có swap thì `MemoryHigh` gần
như không có chỗ để đẩy các trang ít dùng ra. Với `MemoryMax=7G`, máy còn khoảng
0,75 GiB cho OS, Caddy và journald, cộng swap 4 GiB làm đệm, vì vậy **không được
xóa swap**; riêng
`npm run build` của Vite lúc cập nhật cũng có thể ăn nhiều RAM. Trước hết kiểm tra
máy chưa có swapfile trùng tên hoặc swap đã bật:

```bash
sudo swapon --show
free -h
sudo ls -lh /swapfile 2>/dev/null || true
```

Nếu `/swapfile` chưa tồn tại, tạo và bật nó. Khối này kiểm tra lại trước từng bước
để có thể chạy lại mà không format một swapfile đang hoạt động:

```bash
if [ ! -e /swapfile ]; then
  sudo fallocate -l 4G /swapfile
  sudo chmod 0600 /swapfile
  sudo mkswap /swapfile
fi
if ! sudo swapon --show=NAME --noheadings | grep -qE '^[[:space:]]*/swapfile[[:space:]]*$'; then
  sudo swapon /swapfile
fi
```

Chỉ ghi `/etc/fstab` nếu chưa có đúng entry; **không** bỏ `grep -q`, vì thêm
cùng một swapfile hai lần có thể làm lần boot sau gặp lỗi:

```bash
grep -qE '^[[:space:]]*/swapfile[[:space:]]+' /etc/fstab \
  || printf '%s\n' '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
printf '%s\n' 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-xanax-swap.conf
sudo sysctl --system
```

`swappiness=10` nghĩa là chỉ đổi trang ra swap khi thật cần, không đổi chỗ sớm
làm app chậm. Xác nhận cả swap lẫn giá trị kernel trước khi đi tiếp:

```bash
sudo swapon --show
free -h
sysctl vm.swappiness
```

Kết quả phải có `/swapfile` khoảng 4 GB và `vm.swappiness = 10`. Không tiếp tục
nếu `swapon --show` hoặc `free -h` vẫn không thấy swap.

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
if [ -s /opt/xanax/backend/requirements.lock ]; then
  PYTHON_REQUIREMENTS=/opt/xanax/backend/requirements.lock
else
  # Chỉ xảy ra ở lần bootstrap đầu tiên, trước khi freeze venv production.
  PYTHON_REQUIREMENTS=/opt/xanax/backend/requirements.txt
fi
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install -r "$PYTHON_REQUIREMENTS"

sudo -u xanax bash -lc 'cd /opt/xanax/frontend && npm ci && npm run build'
test -f /opt/xanax/frontend/dist/index.html
```

Không chạy `npm run dev` trên server. FastAPI phục vụ trực tiếp
`frontend/dist/` sau khi build.

### Venv riêng cho skill cắt ảnh sản phẩm

Skill này **không dùng venv chính** `/opt/xanax/.venv`. `rembg` kéo theo
`onnxruntime` và một cây xử lý ảnh nặng, nên dựng và bảo trì nó riêng:

```bash
sudo -u xanax -H python3.12 -m venv /opt/xanax/.venv-rembg
sudo -u xanax -H /opt/xanax/.venv-rembg/bin/python -m pip install --upgrade pip
sudo -u xanax -H /opt/xanax/.venv-rembg/bin/python -m pip install \
  'rembg[cpu]' pillow 'mcp>=1.9,<2'
sudo -u xanax -H /opt/xanax/.venv-rembg/bin/python -c \
  'import onnxruntime, PIL, mcp, rembg; print("venv rembg OK:", onnxruntime.__version__)'
```

Extra `[cpu]` là bắt buộc với rembg hiện tại: nó cài backend `onnxruntime` CPU.
PyPI có wheel CPython 3.12 cho Linux x86_64 (`manylinux`, glibc 2.27+), nên trên
Ubuntu 24.04 lệnh trên phải lấy wheel, không build `onnxruntime` từ source. Nếu
log hiện bước compile gói này thì dừng lại và kiểm tra đúng kiến trúc/Python.

Model `birefnet-general-lite` khoảng 214 MB. Tải và nạp thử **trước khi bật
service** để lần gọi đầu không vừa tải model vừa đụng timeout 300 giây:

```bash
sudo install -d -m 0700 -o xanax -g xanax /home/xanax/.u2net
sudo -u xanax -H env U2NET_HOME=/home/xanax/.u2net \
  /opt/xanax/.venv-rembg/bin/python - <<'PY'
from pathlib import Path
from rembg import new_session

session = new_session("birefnet-general-lite")
print("Model OK:", type(session).__name__)
print("Cache:", *Path("/home/xanax/.u2net").rglob("*birefnet*"), sep="\n  ")
PY
```

Rembg dùng `U2NET_HOME`; nếu biến này không có thì mới rơi về
`$XDG_DATA_HOME/.u2net` hoặc `$HOME/.u2net`. Unit đặt cố định `HOME=/home/xanax`
và `U2NET_HOME=/home/xanax/.u2net`; `core/mcp_client.py` cũng truyền hai biến đó
qua whitelist rút gọn của MCP SDK. Vì vậy tiến trình con đọc đúng model đã tải
dưới user `xanax`, không tải lại sau mỗi lần khởi động.

Kiểm tra launcher bằng venv chính nhưng server thật chạy trong venv rembg. EOF
làm MCP server thoát sạch sau khi import xong:

```bash
sudo -u xanax -H env \
  HOME=/home/xanax U2NET_HOME=/home/xanax/.u2net \
  XANAX_REMBG_PYTHON=/opt/xanax/.venv-rembg/bin/python \
  /opt/xanax/.venv/bin/python \
  /opt/xanax/backend/mcp_servers/image_cut_launcher.py </dev/null
```

Launcher tự đặt thư mục làm việc về `/opt/xanax/backend`, nên có thể chạy lệnh
kiểm tra này từ thư mục bất kỳ mà không cần `cd` trước.

Target lưu trong database từ nay là `xanax://image-cut`. Alias này được đổi
thành Python của venv chính và đường dẫn tuyệt đối tới launcher; launcher ưu
tiên `XANAX_REMBG_PYTHON`, sau đó dùng mặc định
`/opt/xanax/.venv-rembg/bin/python`. Không lưu đường dẫn Windows/Linux vào
`skills.config_json` nữa.

Skill có ba biến môi trường riêng; không đặt thì đã dùng mặc định an toàn:

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `XANAX_IMAGE_CUT_MAX_SIDE` | `2000` | Cạnh dài tối đa của bản đưa vào inference; kết quả vẫn lấy pixel ảnh gốc. `0` hoặc số âm tắt thu nhỏ. |
| `XANAX_IMAGE_CUT_IDLE_SECONDS` | `600` | Xóa session model sau từng ấy giây không cắt ảnh. `0` hoặc số âm giữ session mãi. |
| `XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK` | không đặt | Đặt đúng `1` để bỏ qua chốt RAM trước inference khi đo đạc hoặc chủ động chấp nhận rủi ro. |

Giá trị sai định dạng quay về mặc định. Nếu cần ghi đè, đặt chúng bằng
`Environment=` trong unit/drop-in của `xanax.service`; `core/mcp_client.py` truyền
tường minh sang launcher và tiến trình trong venv rembg. Sau khi đổi unit phải
`daemon-reload` và restart như mục 7.

Đo thật trên production ngày 18/08/2026: `birefnet-general-lite` đạt RSS đỉnh
5.562–5.628 MiB (~5,5 GiB) và mất 24–46 giây/ảnh; `u2netp` đạt 518 MiB và
0,7–2,3 giây/ảnh. Sau 30 giây nhàn rỗi RSS còn 127–138 MiB, nên phần xóa session
và `malloc_trim` đang làm việc đúng. Ảnh test chỉ 485x711; ép đầu vào xuống 800px
vẫn đạt 5.562 MiB vì ONNX của birefnet có input cố định `[1, 3, 1024, 1024]`.
Thu nhỏ ảnh vẫn giữ để giảm buffer PIL của ảnh điện thoại thật, nhưng không hạ
được đỉnh của birefnet.

**Cảnh báo cgroup:** trước khi chạy bất kỳ model birefnet nào, cgroup phải còn ít
nhất **6 GiB khả dụng**. Vì tiến trình rembg dùng chung cgroup với web,
`MemoryMax` phải cao hơn hẳn **6 GiB cộng với phần RAM tiến trình web và các tiến
trình con đang dùng**; đặt đúng 6G vẫn không đủ. VPS sau khi nâng có MemTotal
`8131780 kB` (khoảng 7,75 GiB), `MemoryMax=7G`, và service lúc nghỉ có
`MemoryCurrent=301723648` byte (khoảng 288 MiB). Cgroup khi đó còn khoảng 6,7
GiB, vượt chốt 6 GiB nên birefnet chạy được. Không hạ `MemoryMax` xuống dưới
khoảng 6,5 GiB nếu chưa hạ cả ngưỡng trong `MODEL_MEMORY_REQUIREMENTS` hoặc đổi
model mặc định: chốt so với phần **còn lại** của cgroup, không phải tổng RAM.
`birefnet-general-lite` là model duy nhất đã đo được xử lý sạch cả nền tối lẫn
bóng đổ trên bàn gỗ. Chỉ dùng
`XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK=1` khi đo đạc hoặc đã chủ động nhận rủi ro.

Đường MCP hiện chờ 90 giây để kết nối và tối đa 300 giây cho **toàn bộ
một lần gọi tool**; `HUB_CLI_TIMEOUT_SECONDS` không áp dụng ở đây. Một batch lớn
có thể vượt 300 giây và bị hủy, nên chia batch nhỏ; tài liệu này không tự nâng
timeout vì tăng trần sẽ làm mọi MCP tool treo lâu hơn khi có sự cố.

### Chuyển bản ghi skill đang có trên production

Deploy code và dựng venv rembg trước. Sau đó tìm đúng hàng cũ; câu lệnh chỉ đọc
này không sửa database:

```bash
sudo -u xanax sqlite3 -readonly /opt/xanax/backend/xanax.db \
  "SELECT id,name,type,json_extract(config_json,'$.target') FROM skills WHERE type='mcp' AND (json_extract(config_json,'$.target') LIKE '%image_cut.py%' OR json_extract(config_json,'$.target')='xanax://image-cut');"
```

Kết quả phải có đúng skill cắt ảnh sản phẩm. Nếu target đã là
`xanax://image-cut` thì không chạy migration lần nữa. Nếu còn đường dẫn cũ, gán
**ID vừa xem** vào `SKILL_ID`, backup trước, dừng app để không có người sửa skill
đồng thời, rồi chạy migration tham số hóa dưới đây. Script giữ nguyên mọi khóa
khác trong `config_json`, chỉ đổi `target`, và tự từ chối nếu ID không phải skill
MCP trỏ tới `image_cut.py`:

```bash
set -euo pipefail
SKILL_ID=THAY_BANG_ID_VUA_XEM
sudo /usr/local/sbin/xanax-backup
sudo systemctl stop xanax.service
sudo -u xanax -H env SKILL_ID="$SKILL_ID" \
  /opt/xanax/.venv/bin/python - <<'PY'
import json
import os
import sqlite3

db_path = "/opt/xanax/backend/xanax.db"
skill_id = int(os.environ["SKILL_ID"])
new_target = "xanax://image-cut"

with sqlite3.connect(db_path) as db:
    row = db.execute(
        "SELECT id,name,type,config_json FROM skills WHERE id=?", (skill_id,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"Không có skill id={skill_id}; database chưa bị sửa")
    config = json.loads(row[3] or "{}")
    old_target = str(config.get("target") or "")
    if row[2] != "mcp" or "image_cut.py" not in old_target.replace("\\", "/"):
        raise SystemExit(
            f"Từ chối sửa #{row[0]} {row[1]!r}: không phải MCP image_cut.py"
        )
    config["target"] = new_target
    updated = json.dumps(config, ensure_ascii=False)
    db.execute("BEGIN IMMEDIATE")
    cursor = db.execute(
        "UPDATE skills SET config_json=? WHERE id=? AND config_json=?",
        (updated, skill_id, row[3]),
    )
    if cursor.rowcount != 1:
        db.rollback()
        raise SystemExit("Bản ghi đã đổi đồng thời; rollback, chưa sửa gì")
    db.commit()
    print(f"Đã đổi đúng skill #{row[0]} {row[1]!r}: {old_target!r} -> {new_target!r}")
PY
```

Xác minh trước khi khởi động lại:

```bash
sudo -u xanax sqlite3 -readonly /opt/xanax/backend/xanax.db \
  "SELECT id,name,json_extract(config_json,'$.target') FROM skills WHERE id=$SKILL_ID;"
sudo systemctl start xanax.service
sudo journalctl -u xanax.service -n 100 --no-pager
```

Trên database mới hiện **không có seed** cho skill này. `sync_api_skill_tools()`
và `sync_mcp_skill_tools()` chỉ đọc các hàng đã tồn tại rồi đăng ký tool, không
tạo hàng mới. Nếu câu `SELECT` đầu tiên không có kết quả, tạo skill loại MCP qua
giao diện với cấu hình `{"transport":"stdio","target":"xanax://image-cut"}`;
không chạy migration và không chèn seed ngầm.

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
cài. `systemctl revert` cũng xóa drop-in bền vững ở `/etc`, nên phải xem
`systemctl cat xanax.service` trước khi chạy; bước revert bên dưới xóa drop-in
`--runtime` trong `/run/systemd/system.control/` để nó không đè unit vừa copy:

```bash
sudo install -m 0644 /opt/xanax/deploy/xanax.service \
  /etc/systemd/system/xanax.service
sudo systemctl cat xanax.service
sudo systemctl revert xanax.service
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
sudo install -m 0750 -o root -g root /opt/xanax/deploy/provider-check.sh \
  /usr/local/sbin/xanax-provider-check
sudo install -m 0750 -o root -g root /opt/xanax/deploy/disk-check.sh \
  /usr/local/sbin/xanax-disk-check
sudo install -m 0750 -o root -g root /opt/xanax/deploy/backup-freshness.sh \
  /usr/local/sbin/xanax-backup-freshness

sudo install -d -m 0750 -o root -g root /var/lib/xanax

for unit in xanax-alert@.service \
            xanax-healthcheck.service xanax-healthcheck.timer \
            xanax-provider-check.service xanax-provider-check.timer \
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
sudo /usr/local/sbin/xanax-provider-check
sudo /usr/local/sbin/xanax-disk-check

sudo systemctl enable --now xanax-healthcheck.timer
sudo systemctl enable --now xanax-provider-check.timer
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
sudo systemctl cat xanax.service   # kiểm tra trước: revert cũng xóa drop-in bền vững ở /etc
sudo systemctl revert xanax.service
sudo systemctl daemon-reload
sudo systemctl restart xanax.service
sudo systemctl show xanax -p MemoryHigh -p MemoryMax
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

Cả bốn script đều có máy trạng thái chống spam trong `/var/lib/xanax`:

- healthcheck chỉ báo sau **2 lần hỏng liên tiếp**, im lặng suốt thời gian hỏng,
  và báo **đúng một lần** khi phục hồi.
- provider-check báo ngay khi credential CLI chuyển sang hỏng, im lặng khi
  vẫn hỏng, và báo đúng một lần khi phục hồi.
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

### Khóa phiên bản dependency Python

`backend/requirements.txt` ghi **ý định**: code cần tối thiểu phiên bản nào và
cho phép nâng trong khoảng nào. `backend/requirements.lock` ghi **đúng môi trường
được deploy**: mọi phiên bản đều được pin bằng `==`. Không tự đoán các pin trên
máy dev Windows; sinh lock từ venv production Linux sau khi đã cài và kiểm thử.

Trên VPS, chạy lệnh sau từ shell có quyền ghi vào repo:

```bash
sudo -u xanax /opt/xanax/.venv/bin/python -m pip freeze > /opt/xanax/backend/requirements.lock
```

`pip freeze` đưa cả dependency gián tiếp vào file; đó là điều mong muốn, vì một
lock file phải cố định toàn bộ cây dependency chứ không chỉ 17 gói khai báo trực
tiếp. File này **phải được commit vào Git**. Sau lần sinh đầu tiên, copy nội dung
về máy dev, commit rồi pull lại trên VPS; đừng để nó chỉ tồn tại cục bộ trên máy
production.

Venv `/opt/xanax/.venv-rembg` là ngoại lệ có chủ ý: nó không nằm trong
`backend/requirements.txt` hay `backend/requirements.lock`. Vì vậy lệnh cài từ
`requirements.lock` và `pip freeze` của venv chính không cài, nâng hay ghi lại
`rembg`, `onnxruntime`, Pillow hoặc MCP trong venv riêng. Khi cần nâng skill cắt
ảnh, phải chạy pip và kiểm tra model bằng chính
`/opt/xanax/.venv-rembg/bin/python` theo mục **Venv riêng cho skill cắt ảnh sản
phẩm**, rồi theo dõi RAM/thời gian inference sau khi nâng.

Khi chủ động nâng dependency, sửa khoảng phiên bản trong `requirements.txt`, rồi
trên VPS chạy:

```bash
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install \
  -r /opt/xanax/backend/requirements.txt --upgrade
sudo -u xanax bash -lc \
  'cd /opt/xanax && .venv/bin/python -m pytest backend/tests -x -q'
sudo -u xanax /opt/xanax/.venv/bin/python -m pip freeze > /opt/xanax/backend/requirements.lock
```

Copy lock mới về máy dev và commit cùng thay đổi `requirements.txt`. Việc nâng
phiên bản kết thúc ở bước kiểm thử và sinh lock này; deploy bình thường không tự
nâng FastAPI, pydantic, mcp hay dependency gián tiếp.

### Cập nhật phiên bản

Backup trước, rồi pull fast-forward, cập nhật dependency, build lại frontend và
restart đúng một service:

```bash
sudo /usr/local/sbin/xanax-backup
sudo -u xanax git -C /opt/xanax pull --ff-only
test -s /opt/xanax/backend/requirements.lock
sudo -u xanax /opt/xanax/.venv/bin/python -m pip install \
  -r /opt/xanax/backend/requirements.lock
sudo -u xanax bash -lc 'cd /opt/xanax/frontend && npm ci && npm run build'
sudo systemctl restart xanax.service
curl -fsS --retry 15 --retry-delay 2 --retry-connrefused \
  http://127.0.0.1:8000/api/health/ready | python3.12 -m json.tool
```

Deploy dùng `requirements.lock` để cùng một commit luôn cài đúng cùng một cây
dependency. Dòng `test -s` cố ý dừng sớm nếu repo chưa có lock, thay vì âm thầm
quay lại `requirements.txt` và tự nâng package ngay trên production. Ngoại lệ duy
nhất là lần bootstrap đầu tiên ở mục 2; sinh và commit lock ngay sau lần đó.

Các lệnh cập nhật trên chỉ chạm venv chính. Chúng **không** bảo trì
`/opt/xanax/.venv-rembg`; không xóa hoặc dựng lại venv này trong mỗi lần deploy,
và không đưa dependency nặng của rembg vào `requirements.lock`. Nếu release có
đổi yêu cầu của skill cắt ảnh, cập nhật venv rembg bằng lệnh riêng ở mục 2, tải
trước model dưới user `xanax`, chạy kiểm tra launcher rồi mới restart service.

Nếu đợt cập nhật có thay đổi file trong `deploy/`, cài lại unit/script tương ứng;
với `xanax.service`, làm đủ bước `cat`/`revert` bên dưới trước khi
`systemctl daemon-reload`. Validate Caddyfile rồi mới reload Caddy.

### Áp dụng thay đổi unit và xem giới hạn tài nguyên

Sửa file trong repo chưa làm unit đang chạy thay đổi. Sau mỗi lần sửa
`deploy/xanax.service`, cài lại bản root-owned rồi xóa drop-in `--runtime` trong
`/run/systemd/system.control/`; nếu không, giá trị tạm cũ vẫn đè lên file mới.
`systemctl revert` cũng xóa drop-in bền vững ở `/etc`, nên phải dùng
`systemctl cat xanax.service` kiểm tra trước:

```bash
sudo install -m 0644 /opt/xanax/deploy/xanax.service \
  /etc/systemd/system/xanax.service
sudo systemctl cat xanax.service
sudo systemctl revert xanax.service
sudo systemctl daemon-reload
sudo systemctl restart xanax.service
```

Xác nhận systemd đã đọc đúng giới hạn và xem lượng RAM hiện tại:

```bash
systemctl show xanax -p MemoryHigh -p MemoryMax -p TasksMax
systemctl status xanax.service --no-pager | grep -i memory
```

`MemoryHigh=6.5G` là ngưỡng kìm, `MemoryMax=7G` mới là trần cứng;
`TasksMax=512` chặn rò process/thread từ các CLI agent. MemTotal thật là
`8131780 kB` (khoảng 7,75 GiB), nên trần 7G chừa khoảng 0,75 GiB cho OS, Caddy và
journald, cộng swap 4 GiB với `swappiness=10` làm đệm. **Không được xóa swap đó.**
Service lúc nghỉ dùng 288 MiB, nên cgroup còn khoảng 6,7 GiB, vượt chốt 6 GiB
trước inference. Số đo 18/08/2026 cho thấy birefnet đạt đỉnh 5.562–5.628 MiB;
cộng 288 MiB của web vẫn dưới `MemoryHigh=6.5G`, nên một lượt inference không bị
throttle. Giữ giới hạn cgroup để OOM chỉ chọn nạn nhân trong Xanax, không bắn
nhầm Caddy hay sshd. Xác nhận cấu hình bằng `systemctl show` trước khi inference.

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
| `xanax-provider-check` | 10:15 hằng ngày | Gọi thật các entry `claude_cli`/`codex_cli` qua loopback | Credential/provider CLI hỏng; và một lần khi phục hồi |
| `xanax-backup-freshness` | 09:00 hằng ngày | Bản backup mới nhất còn mới hơn 36h không, cả local lẫn cloud | Backup cũ quá ngưỡng, hoặc file cụt |
| `xanax-diskcheck` | 08:30 hằng ngày | Dung lượng các filesystem | Vượt 80%, vượt 90%, hoặc trở lại bình thường |

Ngoài timer còn có `OnFailure=xanax-alert@%n.service` gắn trên `xanax.service`,
bắn ngay khi service rơi vào trạng thái failed.

Kiểm tra nhanh trạng thái toàn bộ lớp giám sát:

```bash
systemctl list-timers 'xanax*' --no-pager
cat /var/lib/xanax/health.state /var/lib/xanax/provider.state \
    /var/lib/xanax/disk.state \
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

### Log báo `database is locked`

SQLite đã chạy ở chế độ WAL để reader không bị writer chặn, và mọi kết nối của
app chờ khóa tối đa 5 giây qua `busy_timeout` thay vì báo lỗi ngay. Kiểm tra mode
thực tế trên production:

```bash
sudo -u xanax sqlite3 /opt/xanax/backend/xanax.db 'PRAGMA journal_mode;'
```

Kết quả phải là `wal`. Nếu không phải, restart `xanax.service` để `init_db()` đặt
lại mode rồi kiểm tra log và quyền ghi của file database cùng thư mục chứa nó.

### Đăng nhập xong lại mất phiên

Production phải dùng `HUB_COOKIE_SECURE=true` và truy cập bằng
`https://domain`. Cookie `Secure` không được trình duyệt gửi qua `http://IP`.
Kiểm tra DNS, chứng chỉ và Caddy; không hạ `HUB_COOKIE_SECURE=false` để chữa tạm
trên Internet.

### Rate limit đăng nhập tính mọi người chung một IP

Đặt `HUB_TRUST_PROXY_HEADERS=true` khi và chỉ khi Caddy đứng trước app. Caddy v2
tự tạo `X-Forwarded-For` an toàn khi nó là proxy Internet đầu tiên; không cần
`header_up`. Đồng thời xác nhận UFW không public 8000 và `HUB_HOST=127.0.0.1`.

### Agent gãy nhưng health vẫn xanh

Nếu nhiều agent cùng không gọi được model trong khi `/api/health/ready`
vẫn trả `ready: true`, nghi credential của `claude`/`codex` CLI đã hết hạn
hoặc bị thu hồi. Readiness không gọi model thật nên không thể thấy lỗi này.

Chạy probe bằng tay; script tự đọc `HUB_API_KEY` và gọi endpoint qua
loopback, không cần đưa secret lên command line:

```bash
sudo /usr/local/sbin/xanax-provider-check
sudo journalctl -u xanax-provider-check.service -n 50 --no-pager
```

Đăng nhập lại dưới chính user chạy app. Trong shell mới, chạy lệnh
tương ứng với provider hỏng (`claude` mở luồng đăng nhập của Claude;
`codex login` đăng nhập lại Codex):

```bash
sudo -u xanax -H bash
claude
codex login
```

Thoát shell `xanax`, chạy lại `sudo /usr/local/sbin/xanax-provider-check`.
Probe thành công sẽ chuyển `/var/lib/xanax/provider.state` về `ok` và gửi
đúng một tin phục hồi nếu trước đó đã cảnh báo.

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
- Không deploy Python trực tiếp từ `requirements.txt` sau giai đoạn bootstrap;
  nâng có kiểm soát, chạy test rồi commit `requirements.lock` sinh từ VPS.
- Không bỏ `MemoryMax` khi Xanax chạm trần, không thêm `CPUQuota` và không đặt
  `MemorySwapMax=0`: cần giữ OOM trong cgroup, workload chủ yếu chờ I/O và
  `MemoryHigh` cần swap để có tác dụng.
