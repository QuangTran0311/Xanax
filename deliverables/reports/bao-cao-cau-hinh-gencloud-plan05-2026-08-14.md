# Báo cáo cấu hình VPS GenCloud Plan 05 Platinum cho Xanax

**Ngày đánh giá:** 14/08/2026  
**Nhà cung cấp:** GenCloud  
**Gói:** Plan 05 – Platinum  
**Hệ điều hành đã chọn:** Ubuntu 24.04 LTS x86_64 (amd64)  
**Mục tiêu:** triển khai Xanax cho cá nhân hoặc nhóm nhỏ

## 1. Kết luận

Gói Plan 05 Platinum **đủ và phù hợp để chạy Xanax**. Ứng dụng sử dụng model AI từ API/CLI bên ngoài nên không cần GPU hoặc máy chủ chuyên AI. VPS chỉ vận hành web application, WebSocket, scheduler, SQLite, lưu file và các tiến trình agent cục bộ.

Với giá hiển thị **210.000 đồng/tháng + 10% VAT = 231.000 đồng/tháng**, cấu hình này có tỷ lệ tài nguyên/chi phí tốt trên thông số công bố. Nên thuê một tháng đầu để kiểm tra chất lượng CPU thực tế, tuyến quốc tế và quy trình backup trước khi trả dài hạn.

Ubuntu 24.04 LTS là lựa chọn phù hợp cho máy chủ mới: Canonical duy trì bảo mật tiêu chuẩn đến tháng 05/2029 và Python mặc định 3.12 đáp ứng yêu cầu `Python >=3.11` của Xanax. Không cần Ubuntu Pro/ESM trong giai đoạn triển khai ban đầu.

## 2. Thông số được công bố

| Hạng mục | Thông số |
|---|---|
| CPU | 3 core, Intel Xeon Platinum 8171M hoặc 8272CL |
| RAM | 6 GB DDR4 ECC |
| Ổ đĩa | 60 GB SSD NVMe, RAID 10 |
| Nền tảng ổ | NVMe PCIe 4 Enterprise |
| IOPS tham chiếu | 50.000–150.000 IOPS |
| Network speed | 1 Gbps |
| Port hạ tầng | 10 Gbps |
| Băng thông | Không giới hạn, áp dụng fair-use |
| IP | 1 IPv4 riêng; có thể mua thêm |
| Datacenter | Việt Nam, hạ tầng Viettel/FPT/VNPT |
| RAM phần cứng | DDR4 ECC |
| SLA | 99,9% |
| Firewall | Anti-DDoS Pro theo trang đặt hàng |
| Backup | Có thông tin chưa thống nhất, cần xác nhận |

Nguồn công bố: [GenCloud Cloud VPS Platinum](https://gencloud.vn/cloud-vps/platinum/#specs) và màn hình cấu hình đơn hàng ngày 14/08/2026.

## 3. Mức độ phù hợp với Xanax

| Tài nguyên | Nhu cầu dự kiến | Đánh giá |
|---|---|---|
| 3 vCPU | FastAPI, WebSocket, scheduler và 1–2 agent đồng thời | Đủ |
| 6 GB RAM | Ubuntu Server + Python app + agent subprocess | Dư dùng hợp lý |
| 60 GB NVMe | Code, môi trường Python, database và dữ liệu ban đầu | Đủ |
| 1 IPv4 | Domain, HTTPS và WebSocket | Đủ |
| 1 Gbps | Gọi API model và phục vụ UI | Dư dùng về thông lượng |
| GPU | Không cần vì không training/inference model cục bộ | Không cần |

CPU Xeon Platinum 8171M/8272CL không phải thế hệ mới, nhưng hiệu năng vẫn dư cho workload web/API của Xanax. Điều quan trọng hơn là mức oversell của node và hiệu năng vCPU thực tế vào giờ cao điểm.

IOPS công bố vượt xa nhu cầu SQLite hiện tại. Tuy nhiên RAID 10 và backup nhà cung cấp không thay thế bản sao dữ liệu độc lập.

## 4. Các điểm phải làm rõ với GenCloud

### 4.1. Mâu thuẫn về backup

- Màn hình đặt hàng ghi **Auto Backup hằng ngày**.
- Trang thông số kỹ thuật ghi **Backup 2 lần/tuần**.

Cần yêu cầu nhà cung cấp xác nhận bằng ticket/email:

1. Tần suất backup áp dụng đúng cho Plan 05.
2. Số bản backup được giữ lại và thời gian lưu.
3. Backup có nằm trên node/ổ/máy chủ độc lập không.
4. Khôi phục có mất phí và khách hàng có tự restore được không.
5. Backup có bao gồm toàn bộ ổ hệ thống không.

### 4.2. Băng thông fair-use

Cần hỏi rõ:

- Ngưỡng fair-use theo tháng.
- Có giới hạn riêng cho băng thông quốc tế không.
- Sau khi vượt ngưỡng sẽ giảm tốc hay tính thêm phí.
- IP có bị chặn hoặc hạn chế khi kết nối tới API model đang sử dụng không.

Đối với Xanax, độ ổn định tuyến từ datacenter tới OpenAI/Anthropic/provider quan trọng hơn con số port 10 Gbps.

### 4.3. CPU và SLA

- Xác nhận 3 core là vCPU shared hay dedicated; ở mức giá này nhiều khả năng là shared.
- Hỏi chính sách khi CPU bị giới hạn kéo dài hoặc node quá tải.
- SLA 99,9% tương ứng khoảng **43 phút 50 giây downtime trong tháng 30 ngày** nếu tính thuần theo tỷ lệ.

### 4.4. IPv4 và hệ điều hành

- Trang thông số cho biết có 1 IPv4; vẫn nên xác nhận đó là IPv4 public routable, không phải địa chỉ sau NAT.
- Xác nhận image đúng là **Ubuntu 24.04 LTS x86_64/amd64**, có quyền `root` hoặc user được phép `sudo`.
- Xác nhận có web console/rescue console và chức năng reinstall OS trong bảng điều khiển.
- Xác nhận kernel, repository và bản cập nhật bảo mật của image hoạt động bình thường ngay sau khi khởi tạo.

## 5. Lựa chọn hệ điều hành

### Hệ điều hành đã chọn: Ubuntu 24.04 LTS x86_64

Ubuntu phù hợp với cách vận hành server lâu dài: nhẹ hơn Windows, dùng systemd để tự khởi động dịch vụ, dễ cấu hình SSH, firewall, log rotation và reverse proxy. Với 6 GB RAM, hệ điều hành và Xanax có đủ dư địa để chạy 1–2 agent đồng thời.

Chọn 24.04 giải quyết luôn hai vướng mắc của các bản LTS cũ hơn:

1. **Vòng đời bảo mật:** bảo trì tiêu chuẩn đến tháng 05/2029, không cần Ubuntu Pro/ESM cho giai đoạn đầu.
2. **Python mặc định:** 24.04 đi kèm Python 3.12, thỏa yêu cầu `Python >=3.11` của Xanax nên không phải cài Python riêng. Vẫn nên dùng virtualenv riêng cho ứng dụng thay vì cài gói vào Python hệ thống.

Nguồn vòng đời chính thức:

- [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)
- [Ubuntu 24.04 LTS](https://ubuntu.com/24-04)

### Khuyến nghị quyết định

- Giữ Ubuntu 24.04 LTS cho máy chủ mới; không có lý do dùng bản LTS cũ hơn.
- Dùng virtualenv riêng cho Xanax, không cài dependency thẳng vào Python hệ thống.
- Không cài desktop GUI hoặc control panel nếu không cần; quản trị bằng SSH để tiết kiệm RAM và giảm bề mặt tấn công.

### Hạng mục tương thích Linux của Xanax

Project hiện được phát triển trên Windows, vì vậy cần hoàn thành các kiểm tra sau:

- Sửa hàm xác định vị trí `SOUL.md`; code hiện còn fallback qua `LOCALAPPDATA`.
- Đảm bảo `claude`, `codex` và `hermes` được cài trong `PATH`; không dựa vào fallback đường dẫn Windows.
- Di trú các target MCP lưu trong database từ đường dẫn `D:\...` sang đường dẫn Linux bằng công cụ migrate của project.
- Kiểm tra quyền đọc/ghi của user chạy service đối với `backend/xanax.db` và `backend/data`.
- Chạy lại toàn bộ backend test, frontend verify và một smoke test WebSocket trên chính Ubuntu.

## 6. Kiến trúc triển khai đề xuất trên Ubuntu Server

```text
Internet
   |
Domain + DNS
   |
Caddy :443 (TLS tự động, WebSocket proxy)
   |
Xanax/FastAPI 127.0.0.1:8000
   |
SQLite + backend/data trên NVMe
```

Quy tắc firewall đề xuất:

| Cổng | Trạng thái | Ghi chú |
|---|---|---|
| 80/TCP | Public | Chuyển hướng HTTPS/challenge chứng chỉ |
| 443/TCP | Public | UI, API và WebSocket bảo mật |
| 8000/TCP | Không public | Chỉ bind `127.0.0.1` |
| 22/TCP | Hạn chế | Chỉ SSH key; giới hạn IP quản trị hoặc qua VPN |
| SQLite | Không có cổng | File cục bộ, không chia sẻ qua mạng |

Quy tắc quản trị tối thiểu:

- Tắt đăng nhập SSH bằng mật khẩu sau khi đã kiểm tra SSH key.
- Không cho phép đăng nhập trực tiếp bằng `root` qua SSH.
- Bật UFW và chỉ mở 22/80/443 theo chính sách ở trên.
- Chạy Xanax bằng user hệ thống riêng, không chạy bằng `root`.
- Quản lý ứng dụng bằng `systemd`; cấu hình tự khởi động và tự restart khi process lỗi.
- Đặt `HUB_HOST=127.0.0.1`, `HUB_DEBUG=false` và `XANAX_NO_BROWSER=1`.

## 7. Phân bổ tài nguyên ban đầu

| Hạng mục | Cấu hình đề xuất |
|---|---|
| Uvicorn process | 1 |
| `HUB_TASK_WORKER_COUNT` | 2 lúc đầu |
| Concurrent agent jobs | 1–2 |
| Reverse proxy | Caddy |
| Service manager | systemd |
| Swap | 2 GB, dùng làm vùng đệm chứ không thay RAM |
| Database | SQLite trên ổ cục bộ |
| Log retention | 7–14 ngày, có rotation |
| Cảnh báo disk | 70% cảnh báo, 85% khẩn cấp |

Sau 7–14 ngày vận hành, có thể tăng worker nếu peak RAM còn trên 1,5–2 GB trống và CPU không bị nghẽn kéo dài.

## 8. Kế hoạch backup bắt buộc

Các thành phần cần bảo vệ:

- `backend/xanax.db`.
- Toàn bộ `backend/data`.
- `backend/.env`.
- `backend/data/.secret_key` hoặc bản lưu an toàn của `XANAX_SECRET_KEY`.
- Cấu hình Caddy/service/firewall.
- File unit systemd và cấu hình UFW/SSH.
- Thư mục cấu hình đăng nhập của Claude/Codex/Hermes trong home của user chạy service nếu sử dụng CLI trên server.

Nên có hai lớp:

1. Backup/snapshot của GenCloud.
2. Backup độc lập sang object storage hoặc máy khác, tối thiểu hằng ngày đối với database và secret.

Không chỉ copy database đang ghi một cách tùy ý. Nên dùng cơ chế SQLite backup nhất quán hoặc dừng dịch vụ ngắn trong cửa sổ backup.

## 9. Kế hoạch nghiệm thu tháng đầu

- [ ] Xác nhận IPv4 public và truy cập SSH bằng key/web console.
- [ ] Cập nhật hệ thống lần đầu (`apt update && apt upgrade`) và bật unattended-upgrades cho bản vá bảo mật.
- [ ] Tạo virtualenv riêng cho Xanax trên Python 3.12 có sẵn, không cài gói vào Python hệ thống.
- [ ] Sửa và kiểm tra các đường dẫn Windows còn lại trong project.
- [ ] Đo tốc độ/độ trễ tới các API model thực tế.
- [ ] Build frontend và chạy backend thành công trên server sạch.
- [ ] HTTPS, cookie Secure và `wss://` hoạt động.
- [ ] Chạy thử hai workflow đồng thời.
- [ ] Theo dõi RAM/CPU trong 24–48 giờ.
- [ ] Reboot Ubuntu và xác nhận systemd tự khởi động Xanax/Caddy.
- [ ] Kiểm tra lịch chạy được khôi phục sau restart.
- [ ] Thực hiện backup và restore thử.
- [ ] Kiểm tra dung lượng tăng sau một tuần sử dụng.
- [ ] Xác nhận hóa đơn tháng sau vẫn là 231.000 đồng hoặc biết rõ điều kiện thay đổi giá.

## 10. Quyết định mua

| Tiêu chí | Kết quả |
|---|---|
| Đủ CPU/RAM | Đạt |
| Đủ lưu trữ ban đầu | Đạt |
| Có IPv4 | Đạt theo công bố |
| Không cần GPU | Đúng |
| Chi phí mục tiêu khoảng 200.000 đồng | Đạt, 231.000 đồng gồm VAT |
| Ubuntu 24.04 chạy được Xanax | Đạt: Python 3.12 sẵn có, chỉ cần sửa tương thích Linux |
| Vòng đời OS phù hợp cho máy mới | Đạt: bảo trì tiêu chuẩn đến 05/2029 |
| Backup rõ ràng | Chưa; cần xác nhận mâu thuẫn |
| Phù hợp mua dài hạn ngay | Chưa nên; thử một tháng trước |

**Khuyến nghị cuối:** cấu hình Plan 05 Platinum vẫn phù hợp và không cần mua thêm CPU, RAM, IPv4 hoặc SSD. Ubuntu 24.04 LTS x86_64 là template đúng cho máy chủ này. Chỉ public Xanax sau khi đã sửa các điểm phụ thuộc Windows và hoàn tất kiểm thử trên Linux. Chỉ nên gia hạn dài hạn sau khi đã kiểm tra tuyến quốc tế, hiệu năng vCPU giờ cao điểm và restore backup thành công.
