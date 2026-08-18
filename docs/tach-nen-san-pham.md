# Tách nền ảnh sản phẩm: cơ chế, số đo, và trần của cách làm hiện tại

Tài liệu này giải thích chuyện gì thật sự xảy ra khi `cut_product` tách nền một
tấm ảnh chụp, vì sao vẫn còn vệt nền dính lại, và — phần quan trọng nhất — **vì
sao có một loại lỗi mà không tham số nào chữa được**.

Toàn bộ số liệu dưới đây đo trên một ảnh thật: `IMG_2978.JPEG`, 1536×2048, móc
khoá đà điểu len treo trên ba lô vải tối màu. Đây là ca khó điển hình của dự án:
nền lộn xộn, tối, và có vật thể lạ (vòng khoá kim loại) dính vào sản phẩm.

---

## 1. Đường đi của một tấm ảnh

`rembg.remove()` không phải một khối liền. Nó là bốn bước, và mỗi bước hỏng theo
một kiểu khác nhau:

```
ảnh chụp  →  [1] model ONNX  →  mask xám  →  [2] nhị phân hoá  →  [3] cutout  →  PNG có alpha
                                    ↑                                  ↑
                              chỗ ta KHÔNG chạm được         chỗ ta chạm được
```

**Bước 1 — model.** Một mạng nơ-ron đã huấn luyện sẵn (`u2netp.onnx`, 4,7MB) nhìn
ảnh và trả về **mask xám**: mỗi pixel một con số 0–255, nghĩa là "tôi tin chỗ này
là sản phẩm đến mức nào". Đây là toàn bộ phần thông minh của hệ thống.

**Bước 2 — nhị phân hoá.** rembg lấy mask xám đó làm thẳng kênh alpha. Con số
"tôi không chắc, khoảng 94/255" biến thành "trong suốt 37%" — và **màu gốc của
pixel được giữ nguyên**. Nếu pixel đó vốn là vải ba lô đen, nó thành một pixel
đen mờ 37% nằm trong ảnh sản phẩm.

**Bước 3 — cutout.** Ghép màu gốc với alpha vừa có, xuất PNG.

**Bước 4 (của mình, ở `core/image_compose.py`)** — dán lên nền do model vẽ. Đây
là lúc mọi khuyết tật lộ ra: trên nền trắng của trình xem ảnh thì pixel đen mờ
gần như vô hình, dán lên nền kem là hiện thành quầng xám quanh sản phẩm.

---

## 2. Chẩn đoán: model không sai, model đang *do dự*

Câu hỏi quyết định là: **tại đúng những pixel còn đen, mask xám trả về bao
nhiêu?** Nếu nó trả 250 thì model tin chắc đó là sản phẩm — lỗi nằm ở model. Nếu
nó trả lưng chừng thì model đã ngờ ngợ, chỉ là bước 2 vứt bỏ sự ngờ vực đó.

Đo trên 34.959 pixel vừa nằm trong mask vừa tối (độ sáng < 60):

| mask xám trả về | số pixel | tỷ lệ |
|---|---:|---:|
| 12–128 — do dự, nghiêng về nền | 20.243 | **57,9%** |
| 128–240 — do dự | 7.370 | 21,1% |
| 240–255 — chắc chắn là sản phẩm | 7.346 | 21,0% |

Trung vị **94/255**. Kết luận: model không hề khẳng định vải ba lô là sản phẩm.
Nó lưỡng lự, và bước nhị phân hoá đã biến sự lưỡng lự đó thành màu đen nửa mờ.

Đây là tin tốt, vì lưỡng lự thì cứu được.

---

## 3. Alpha matting: bảo nó xét lại bằng màu

`alpha_matting=True` chèn một bước vào giữa 1 và 2. Thay vì tin mask, nó chia
ảnh làm ba vùng rồi **tính lại độ trong suốt từ màu thật của pixel**:

| vùng | điều kiện | xử lý |
|---|---|---|
| chắc chắn sản phẩm | `mask > 240`, rồi bào mòn `erode_size` px | alpha = 255 |
| chắc chắn nền | `mask < 10`, rồi bào mòn | alpha = 0 |
| còn nghi ngờ | phần ở giữa | giải phương trình matting theo màu |

Chữ **bào mòn** là chỗ ăn tiền. `erode_size=10` đẩy 10 pixel sát mép mask từ
"chắc chắn sản phẩm" xuống "còn nghi ngờ" — và ở vùng nghi ngờ, thuật toán quyết
bằng màu. Len kem trên nền vải đen là tương phản mạnh, matting tách rất gọn.

Thêm một lợi ích: matting gọi `estimate_foreground_ml`, trả về màu sản phẩm **đã
gỡ khỏi màu nền**, chứ không chỉ gán alpha rồi để nguyên màu lẫn lộn.

### Số đo

Đếm pixel tối còn dính trong vành 25px sát biên (loại trừ hai con mắt đen của
sản phẩm, chúng nằm sâu bên trong):

| tổ hợp | giây | pixel nền dính | % vành biên |
|---|---:|---:|---:|
| u2netp thô — *mặc định cũ* | 0,5 | 5.366 | 4,7% |
| **u2netp + matting mặc định — *mặc định mới*** | **6,0** | **2.712** | **2,5%** |
| u2netp + matting `erode=25` | 10,4 | 2.428 | 2,2% |
| u2netp + matting `erode=25 bg=40` | 9,0 | 2.452 | 2,2% |
| u2netp + `post_process_mask` | 1,0 | 6.597 | 5,9% |
| isnet-general-use thô | 1,8 | 6.876 | 5,2% |
| isnet-general-use + matting `erode=25` | 9,7 | 2.790 | 2,4% |

Ba điều rút ra, cả ba đều ngược với trực giác ban đầu:

**`isnet-general-use` không cứu được.** Nặng gấp 38 lần (171MB), chạy lần đầu 78
giây, và cho kết quả **tệ hơn** u2netp. Tệ hơn nữa: mask của nó rắc pixel lạc
khắp khung ảnh, bbox sản phẩm chạm cả mép trên lẫn mép dưới, nên bước cắt sát ở
`image_cut.py` sẽ cắt ra nguyên tấm ảnh thay vì sát sản phẩm.

> **Đính chính.** Từ kết quả này, bản đầu của tài liệu đã kết luận rộng ra thành
> "đổi model không cứu được". Sai — nó chỉ đúng với isnet. Xem mục 3b:
> `birefnet-general-lite` giải quyết được cả những ca mà tham số bó tay.

**`post_process_mask` làm xấu đi.** Ruột nó chỉ là `opening(mask, disk(1))` — hạt
nhân bán kính **1 pixel**, chỉ quét được đốm nhiễu 1–2px lạc lõng, trong khi vệt
nền ở đây là mảng lớn dính liền vào sản phẩm. Rồi dòng cuối `np.where(mask < 127,
0, 255)` ép alpha về nhị phân, xoá sạch vành alpha mềm — mà cả bước ghép nền của
mình sống nhờ vành mềm đó (bóng đổ lấy alpha làm hình bóng).

**Số đẹp hơn không có nghĩa ảnh đẹp hơn.** `erode=25` cho con số tốt nhất bảng
(2,2%) nhưng nhìn bằng mắt thì nó **ăn mất con mắt đen bên phải của sản phẩm**,
biến thành một cục trắng. Lý do ở ngay trong cơ chế: matting phân biệt bằng
**màu**, mà mắt đen nằm sát biên trông y hệt nền tối. Nới vùng nghi ngờ ra 25px
là đưa con mắt vào diện xét lại, và nó bị xử oan.

Đây là bài học đắt nhất của cả đợt đo: **chỉ tin thước đo là hỏng việc.** Mỗi lần
chỉnh tham số phải mở ảnh ra nhìn.

---

## 3b. Ảnh thứ hai lật lại kết luận: bóng đổ, và birefnet

Ảnh thứ hai (`IMG_2981.JPEG`) chụp cùng món hàng nhưng đặt trên **bàn gỗ sáng
màu** — đúng loại "nền dễ" mà lẽ ra không còn vấn đề gì. Kết quả vẫn có mảng tối
mờ bao quanh sản phẩm.

Đo ra thì đó **không phải nền**, mà là **bóng đổ thật của món hàng trên mặt bàn**.
Và nó **đục hẳn**: 16.678 pixel tối, xám, alpha ≥ 200. Nghĩa là mask khẳng định
bóng đổ là một phần sản phẩm.

Đây là ca mà mọi tham số đều bó tay, vì lý do cấu trúc:

- alpha matting chỉ xét lại vành `erode_size` = 10 pixel sát mép. Vệt bóng rộng
  hơn thế nhiều nên nằm ngoài tầm.
- nâng ngưỡng alpha không giúp: bóng đổ có alpha 255, không phải bán trong suốt.
- `post_process_mask` càng không: nó chỉ xoá đốm 1–2px.

Bóng đổ là ca sách giáo khoa của giới hạn ở mục 4: model *tin chắc* nó sai, và ta
không có cách nào nói cho nó biết.

### Nhưng model khác thì giải được

`birefnet-general-lite` (kiến trúc BiRefNet, backbone Swin-tiny) — model duy nhất
chưa thử ở vòng đo đầu — xử lý sạch cả hai ảnh:

| | u2netp + matting | birefnet-general-lite |
|---|---|---|
| ảnh 1, nền ba lô tối | sạch nền | sạch nền |
| ảnh 1, con mắt đen | **bị bạc thành xám nhạt** | giữ nguyên đen bóng |
| ảnh 1, vòng khoá kim loại | còn vệt trắng mờ | tự loại gần hết |
| ảnh 2, bóng đổ trên bàn gỗ | **còn nguyên** | sạch |
| thời gian mỗi ảnh | 5,0s | 13,5s |
| dung lượng model | 4,4MB | 214MB |

birefnet **không cần** alpha matting: mask của nó đủ sạch để bật matting lên chỉ
tốn thêm ~4s mà không đổi gì đáng kể. Đây cũng là lý do vòng đo đầu đi sai hướng
— nó dồn công sức vào việc cứu chữa mask của một model yếu, thay vì đổi model.

**Một lần nữa thước đo suýt đánh lừa.** Chỉ số "pixel tối, xám, đục" cho birefnet
15.126 so với u2netp 16.678 — chênh 9%, nhìn như không đáng kể. Nhưng nhìn ảnh
thì một bên còn nguyên đám mây xám quanh đầu, một bên sạch trơn. Lý do: chỉ số đó
đếm cả mắt đen, len đỏ sẫm và len xám của chính sản phẩm, nên phần nhiễu thật bị
pha loãng. Không có cách nào biết điều đó nếu không mở ảnh ra xem.

---

## 4. Giới hạn: ta không sửa được model, chỉ sửa được xung quanh nó

Đây là phần cần nhớ khi viết về giới hạn của hướng nghiên cứu này.

Nhìn lại sơ đồ ở mục 1: **bước 1 là một hộp đen ta không có quyền chạm vào.**
File `.onnx` là trọng số đã huấn luyện sẵn, tải về từ GitHub release. Ta chọn
được *cái* hộp đen nào — và mục 3b cho thấy lựa chọn đó quan trọng hơn mọi tham
số cộng lại — nhưng bên trong hộp thì không. Trong toàn bộ hệ thống hiện tại
không có đường nào để:

- huấn luyện lại hay tinh chỉnh (fine-tune) model trên ảnh sản phẩm của mình;
- dạy nó "vòng khoá kim loại không phải là món hàng";
- cho nó biết bối cảnh — rằng đây là ảnh chụp để đăng bán, nền cần bỏ hết;
- sửa lỗi của nó ở một vùng cụ thể mà không ảnh hưởng vùng khác.

Các tham số hậu kỳ — `alpha_matting`, ba ngưỡng, `padding_percent` — đều nằm
**bên ngoài** hộp đen. Chúng chỉ làm được đúng một việc: *diễn giải lại* mask mà
model đã trả, theo những quy tắc thủ công không biết gì về sản phẩm. Matting biết
màu. Nó không biết đâu là mắt, đâu là vòng khoá, đâu là bóng đổ.

Hệ quả thực tế, xếp theo mức độ khó chịu:

**a) Có loại lỗi tham số không chạm tới được.** Hai ví dụ đã gặp: vòng khoá kim
loại (dính thật vào sản phẩm, model giữ lại là hợp lý) và bóng đổ trên mặt bàn
(mask khẳng định là sản phẩm với alpha 255, nằm ngoài vành 10px mà matting xét
lại). Cả hai chỉ đổi được bằng cách **đổi model** hoặc **chụp lại**, không có
tham số nào chạm tới.

**b) Tối gặp tối thì bó tay.** Phần len khuất sáng nằm sát nền vải đen: ở đó màu
**thật sự** mơ hồ, không phải model đoán ẩu. Đây là giới hạn thông tin, không
phải giới hạn thuật toán — chụp lại với nền tương phản là cách duy nhất.

**c) Mỗi lần chỉnh là đánh đổi mù.** Không tinh chỉnh được model thì mọi cải
thiện đều phải mua bằng một tham số toàn cục, mà tham số toàn cục thì tác động
lên cả ảnh. `erode=25` gỡ được thêm nền *và* ăn mất con mắt — hai chuyện đó là
cùng một phép toán, không tách rời được.

**d) Không có đường tiến dần.** Model không học được từ ảnh Papa đã sửa tay. Cắt
1.000 tấm thì tấm thứ 1.000 vẫn sai y như tấm đầu.

### Muốn nâng trần thì phải làm gì

Bốn hướng, xếp theo chi phí:

1. **Đổi sang model mạnh hơn.** Rẻ nhất về công sức, và đã làm: birefnet giải
   được cả bóng đổ lẫn con mắt bị bạc. Trên production, trả bằng tốc độ
   (u2netp 0,7–2,3 giây → birefnet 14,5–27,6 giây) và dung lượng model
   (4,4MB → 214MB). Trần của hướng này là danh sách model rembg có sẵn.
2. **Sửa đầu vào, không sửa thuật toán.** Chụp trên nền sáng tương phản, ánh sáng
   toả đều để không đổ bóng gắt, tháo phụ kiện kim loại. Không tốn gì và phá được
   cả (a) lẫn (b) — nhưng đòi người chụp đổi thói quen.
3. **Đổi sang model có ngữ nghĩa.** Loại model nhận chỉ dẫn bằng chữ ("giữ con
   thú len, bỏ vòng kim loại") thay vì chỉ đoán vật thể nổi bật. Đắt hơn, phụ
   thuộc dịch vụ ngoài, nhưng là cách duy nhất xử lý được (a) một cách có chủ ý
   thay vì may rủi.
4. **Tinh chỉnh model trên ảnh của mình.** Phá được cả (a) và (d), nhưng cần bộ
   ảnh có nhãn và một quy trình huấn luyện — hiện dự án chưa có gì cho việc này.

---

## 5. Cấu hình đang chốt

```python
cut_product(input_path, output_path,
            model="birefnet-general-lite",   # sạch nhất trong các model rembg có sẵn
            alpha_matting=False,             # birefnet không cần, bật chỉ tốn thêm ~4s
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,     # nâng 30-50 nếu nền tối mà còn sót
            alpha_matting_erode_size=10)               # ĐỪNG nâng quá 10
```

Giá phải trả trên production: **0,7–2,3 giây → 14,5–27,6 giây mỗi ảnh**, và 214MB
tải về lần đầu. Với ảnh đăng bán thì đáng. Cần nhanh (thư mục vài trăm ảnh) thì
`model="u2netp"` — RSS đỉnh đo được 518 MiB, đổi lại chấp nhận bóng đổ còn sót.

Phía ghép nền, `core/image_compose.py` có thêm một chốt an toàn: matting đã khử
nhiễm màu sẵn rồi, chạy thêm bước chia ngược alpha nữa là khử hai lần, len trắng
sẽ ngả bạc. Nhưng hàm ghép chỉ nhận một file PNG, không có cách nào biết file đó
đã qua matting hay chưa — nên nó **tự đo**: so độ sáng trung bình của vành bán
trong suốt với ruột sản phẩm, vành không tối hơn thì bỏ qua bước khử.

Đo trên chính ảnh đà điểu sau khi bật matting: vành 84,8 / ruột 155,8 — tỷ lệ
0,54, vẫn dưới ngưỡng 0,85, nên bước khử **vẫn chạy**. Nghĩa là trên ảnh nền tối
như thế này, matting chưa dọn hết màu nền ở vành; chốt an toàn kia là để dành cho
ảnh chụp nền sáng, nơi matting làm sạch triệt để hơn.

### Cảnh báo: không phải "viền đen" nào cũng là lỗi tách nền

Sau khi đổi sang birefnet, ảnh vẫn hiện ra một **khung chữ nhật tối** quanh sản
phẩm. Nhìn thì giống hệt nền còn sót, nhưng đo ra thì bốn góc file cắt đều trong
suốt hoàn toàn — khung đó sinh ra ở **khâu ghép**, không phải khâu cắt.

Nguyên nhân: hình bóng đổ được làm mờ trên một tấm canvas chỉ to bằng sản phẩm.
Gaussian blur cần lan ra ngoài, tới mép tấm là bị xén cụt, nên bên ngoài khung
sản phẩm không còn một chút bóng nào — để lại đúng một hình chữ nhật sắc cạnh.
Đã sửa: dán hình bóng lên tấm to bằng cả nền rồi mới làm mờ.

Bài học cho việc chẩn đoán: **luôn kiểm tra file cắt riêng trước khi đổ lỗi cho
model.** Ghép ảnh cắt lên một tấm nền trơn màu kem là biết ngay lỗi nằm ở khâu
nào. Đợt này đã suýt đi tinh chỉnh tiếp tham số tách nền cho một lỗi nằm ở chỗ
hoàn toàn khác.

---

## 6. RAM trên production: số đo ngày 18/08/2026

Đây là số đo lại trực tiếp trên VPS production sau khi nâng máy lên 8 GB,
MemTotal thật **7,75 GiB**. Máy còn dư RAM trong lúc đo nên các số dưới đây mới
phản ánh nhu cầu thật, không phải suy ra từ dung lượng file model:

| model / phép thử | RSS đỉnh | thời gian mỗi ảnh |
|---|---:|---:|
| `birefnet-general-lite`, các lượt chạy | **6.105–6.562 MiB**; từ lượt thứ hai ổn định ở **6.562 MiB** | **14,5–27,6 giây** |
| `birefnet-general-lite`, chạy trần | **6.537 MiB** | — |
| `birefnet-general-lite`, `OMP_NUM_THREADS=4` + `MALLOC_ARENA_MAX=2` như production | **6.562 MiB** | — |
| `u2netp` | **518 MiB** | **0,7–2,3 giây** |

Hai đợt đo birefnet đạt 6.537 và 6.562 MiB, chỉ chênh **0,4%**: số vCPU tăng từ
3 lên 4 và hai biến môi trường production không tạo khác biệt đáng kể. Trên máy
đủ RAM, RSS ngay sau mỗi lượt cắt là **525 MiB**. Mức **127–138 MiB** từng ghi
trên máy cũ là hậu quả của áp lực bộ nhớ ép kernel reclaim, không phải bằng chứng
code cũ dọn RAM tốt hơn. Vẫn giữ đường xóa session, GC và `malloc_trim(0)`, nhưng
không dùng RSS sau lượt cắt của hai máy để suy ra hiệu quả dọn bộ nhớ.

### Bài học riêng: máy thiếu RAM cho ra đỉnh RSS thấp giả tạo

Số cũ 5.562–5.628 MiB được đo trên máy chỉ có khoảng 5,8 GiB RAM. Tiến trình còn
muốn cấp thêm bộ nhớ nhưng kernel không còn gì để cấp nên phải reclaim; vì thế
đỉnh RSS bị **chính máy cũ cắt cụt**, không phải nhu cầu thật của model. Việc máy
vẫn chạy xong không chứng minh model chỉ cần chừng đó.

**Muốn biết nhu cầu thật phải đo trên máy còn dư RAM.** Sai lầm này đã dẫn tới
việc đặt thấp cả trần cgroup lẫn ngưỡng chặn trước inference. Khi đọc lại log đo,
phải phân biệt “cao nhất máy cho phép giữ” với “cao nhất tiến trình cần dùng”.

### Thu nhỏ đầu vào không hạ được đỉnh của birefnet

Phép thử cũ với ảnh 485x711 và cạnh bị ép xuống 800px cũng chịu cùng áp lực bộ
nhớ, nên con số đỉnh cụ thể của phép thử đó không còn giá trị. Tuy nhiên nguyên
nhân kỹ thuật đã xác nhận trực tiếp từ file ONNX vẫn đúng: `birefnet-general-lite`
có input shape cố định **`[1, 3, 1024, 1024]`**, không có trục động. Model luôn
dựng và chạy tensor 1024x1024 bất kể kích thước ảnh đưa vào. Vì vậy **không được
tiếp tục coi thu nhỏ ảnh là hướng để kéo RSS đỉnh birefnet xuống**.

Bước thu nhỏ vẫn được giữ. Với ảnh điện thoại thật 4000x3000, nó giảm các buffer
PIL/rembg trước và sau inference; alpha sau đó vẫn được phóng về kích thước gốc
và gắn lên pixel ảnh gốc. Lợi ích này giảm phần buffer phụ của ảnh lớn, nhưng
không chạm được đỉnh nền 1024x1024 cố định của chính birefnet.

### Chốt RAM trước inference

`image_cut.py` lấy lượng RAM thật sự dùng được là giá trị **nhỏ hơn** giữa
`MemAvailable` và `memory.max - memory.current` của cgroup v2 hiện tại. Vế cgroup
là quan trọng nhất vì tiến trình rembg nằm cùng cgroup với `xanax.service`: máy
có thể còn RAM nhưng cgroup vẫn đã sát trần. File thiếu, không đọc được hoặc
`memory.max` là `max` được coi là nguồn không giới hạn để máy dev Windows và
cgroup v1 không lỗi.

| nhóm model | ngưỡng trước inference | hành vi |
|---|---:|---|
| `birefnet-general-lite` và mọi model tên bắt đầu bằng `birefnet` | **6,5 GiB** | từ chối nếu thấp hơn |
| `u2netp`, `u2net`, `isnet-general-use`, `u2net_cloth_seg`, `u2net_human_seg` | **1 GiB** | từ chối nếu thấp hơn |
| tên model lạ, chưa đo | ngưỡng tham chiếu 1 GiB | không chặn, vì chưa được phép đoán là nặng |

Thông báo từ chối ghi model, ngưỡng, RAM còn lại, nguồn đang nghẽn và gợi ý
`model='u2netp'`. Batch kiểm tra trước vòng lặp và dừng ngay nếu RAM tụt xuống
dưới ngưỡng, không lặp cùng một lỗi cho hàng trăm ảnh.

Sau khi nâng RAM, VPS có MemTotal `8131780 kB` (khoảng 7,75 GiB). Đỉnh thật trong
cgroup xấp xỉ **6,7 GiB**: 6.562 MiB của rembg cộng khoảng 300 MiB của web. Mức
này nằm dưới `MemoryHigh=7G`, nên lượt inference bình thường không bị throttle.
`MemoryMax=7.5G` còn chừa khoảng 250 MiB RAM vật lý cộng swap 4 GiB; MemoryHigh
sẽ kìm và đẩy trang ít dùng ra swap trước khi cgroup chạm được trần cứng đó.

Chốt birefnet dùng **6,5 GiB**, nhỉnh hơn đỉnh rembg 6.562 MiB (xấp xỉ 6,41 GiB)
và vẫn còn khoảng an toàn tới trần. Không đặt chốt đúng 7 GiB: với
`MemoryMax=7.5G` và web dao động 300–800 MiB, phần **còn lại** của cgroup sẽ dao
động quanh đúng ngưỡng, khiến skill lúc chạy được lúc không. Chốt luôn so với
phần còn lại của cgroup, không phải tổng RAM; muốn đổi giới hạn phải tính lại cả
`MODEL_MEMORY_REQUIREMENTS` và phần RAM của web.

Ba biến môi trường liên quan:

- `XANAX_IMAGE_CUT_MAX_SIDE` mặc định `2000`: cạnh dài tối đa đưa vào rembg;
  `0` hoặc số âm tắt bước thu nhỏ. Giá trị không phải số quay về `2000`.
- `XANAX_IMAGE_CUT_IDLE_SECONDS` mặc định `600`: số giây nhàn rỗi trước khi xóa
  toàn bộ session; `0` hoặc số âm tắt việc xóa. Giá trị không phải số quay về
  `600`.
- `XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK=1`: bỏ qua chốt RAM khi đo đạc hoặc khi chủ
  máy chủ động chấp nhận rủi ro. Không đặt `1` thì chốt vẫn bật.

Đo lại trên đúng VPS bằng:

```bash
sudo -u xanax env XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK=1 \
  /opt/xanax/.venv-rembg/bin/python \
  /opt/xanax/backend/scripts/measure_image_cut_memory.py <ảnh>

# Đo gần baseline: không thu nhỏ ảnh và không xóa session khi idle.
sudo -u xanax env XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK=1 \
  XANAX_IMAGE_CUT_MAX_SIDE=0 XANAX_IMAGE_CUT_IDLE_SECONDS=0 \
  /opt/xanax/.venv-rembg/bin/python \
  /opt/xanax/backend/scripts/measure_image_cut_memory.py <ảnh>
```

Script in RSS hiện tại sau từng lượt, RSS đỉnh của tiến trình và RSS sau thời
gian nghỉ mà không cần `psutil`. Khi chủ động đo trên cấu hình chưa đủ RAM, thêm
`XANAX_IMAGE_CUT_SKIP_MEMORY_CHECK=1`. Biến thể gần baseline tắt cả bước thu nhỏ
lẫn việc xóa session khi idle để đo mức giữ bộ nhớ của đường xử lý gốc. Không lấy
việc thu nhỏ ảnh làm bằng chứng rằng đỉnh birefnet đã lọt dưới một trần cụ thể.

---

## Phụ lục: cách đo lại

Script đo nằm ở lịch sử phiên làm việc, nguyên tắc như sau:

- **Chỉ số đúng** là số pixel *tối* + *đục* + *sát biên*. Phải có cả ba điều kiện:
  bỏ "sát biên" thì hai con mắt đen của sản phẩm bị tính thành lỗi; bỏ "đục" thì
  đếm cả vành mềm hợp lệ.
- **Luôn xuất kèm ảnh ghép trên nền kem.** PNG trong suốt xem trên nền đen của
  trình xem ảnh thì không phân biệt được đâu là trong suốt, đâu là nền dính —
  đúng cái bẫy đã làm lạc hướng chẩn đoán ban đầu.
- **Đọc mask thô** bằng `remove(..., only_mask=True)` khi cần biết lỗi nằm ở model
  hay ở khâu diễn giải mask. Đây là phép thử phân biệt hai nguyên nhân.
