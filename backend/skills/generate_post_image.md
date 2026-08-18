# generate_post_image

## Mô tả
Đọc bài đăng từ bước trước và chuẩn bị ảnh social media chuyên nghiệp. Nếu có ảnh
sản phẩm thật, model chỉ sinh nền không chữ; code sẽ ghép sản phẩm và vẽ lớp poster
tiếng Việt sau cùng.

## HAI CHẾ ĐỘ — chọn đúng chế độ TRƯỚC khi viết prompt

> **Người dùng gửi kèm ảnh → CHẾ ĐỘ B. Chỉ đưa chủ đề, không ảnh → CHẾ ĐỘ A.**

| | Chế độ A — model vẽ tất | Chế độ B — sản phẩm là ảnh thật |
|---|---|---|
| Khi nào | Người dùng chỉ nói chủ đề | Người dùng bấm kẹp giấy gửi ảnh vào |
| IMAGE PROMPT tả gì | Cả thiết kế, món hàng và chữ | **CHỈ CÁI NỀN, KHÔNG CHỮ** |
| `ẢNH SẢN PHẨM` | Không có | **Bắt buộc có** |
| `POSTER` | Không có | Có dữ liệu để code vẽ chữ |

Hệ thống đã tự dò ảnh đính kèm và nói thẳng chế độ trong mục "NGUỒN ẢNH". Nghe
theo dòng đó, không tự suy lại từ lời người dùng.

### Người dùng không biết kỹ thuật — đừng hỏi họ

Người gửi ảnh thường là chủ shop. Họ chỉ gửi ảnh và nói muốn làm poster; mọi bước
kỹ thuật phía sau là việc của bạn.

**Cấm hỏi người dùng** đường dẫn file, tên chế độ, `cao`/`xuống`, hoặc yêu cầu họ
tự cắt nền. Chỉ hỏi khi thiếu thông tin chỉ họ mới biết, ví dụ giá bán hay tên page.

Có ảnh thật mà vẫn dùng chế độ A sẽ tạo hai món hàng chồng nhau. Chế độ B là mặc
định cho bài bán hàng vì ảnh đăng phải dùng đúng món hàng thật.

## Nguyên tắc cốt lõi

- Không output lại caption; bước trước đã viết rồi.
- Chế độ A: prompt mô tả cả thiết kế và text tiếng Việt chính xác để model vẽ.
- Chế độ B: prompt chỉ mô tả nền và **cấm tuyệt đối mọi chữ/ký tự/logo/watermark**.
  Chữ tiếng Việt nằm trong JSON `POSTER`, do Pillow vẽ sau khi ghép sản phẩm.
- Chỉ output đúng format của chế độ tương ứng, không thêm giải thích.

## Quy trình

### Bước 1 — Đọc bài đăng từ Context

Xác định tên thương hiệu/sản phẩm, hook, tối đa 3 điểm bán, giá nếu có, CTA,
@handle/liên hệ, tone và platform. Không bịa trường bị thiếu; để chuỗi rỗng hoặc
danh sách rỗng trong `POSTER`, code sẽ bỏ hẳn phần đó.

### Bước 2 — Xác định phong cách

- Handmade: kem/be ấm, chất liệu giấy/vải nhẹ, thân thiện.
- Thời trang: sạch, tương phản, hình học tối giản.
- F&B: tông ấm và sáng, nhưng không vẽ thêm đồ ăn cạnh tranh với sản phẩm thật.
- Công nghệ/dịch vụ: navy, gradient hiện đại, bề mặt studio gọn.
- Trẻ em/đồ chơi: pastel, vòm hoặc pattern rất nhẹ.

### Bước 3 — Soạn IMAGE PROMPT

Chế độ A mô tả đầy đủ layout, typography, text, hình chính và trang trí.

Chế độ B chỉ mô tả:

1. Nền trống dùng cho ảnh sản phẩm cắt rời: `an empty product backdrop`.
2. Màu, gradient, ánh sáng mềm từ trên xuống và chất liệu nền.
3. Mặt phẳng/vòm/bục tối giản để sản phẩm có chỗ đứng.
4. Khẳng định không có món hàng, người, tay, mannequin, chữ, logo hoặc watermark.

## Chế độ B — layout chữ quyết định vị trí sản phẩm

Không còn vùng cấm cứng 17–93%. Code làm theo thứ tự:

1. Tự xuống dòng và đo chiều cao thật của khối trên (`title`, `tagline`).
2. Đo khối dưới (`features`, `price`, `cta`, `handle`).
3. Khoảng còn lại giữa hai khối trở thành chỗ sản phẩm.
4. Từ khoảng đó code tính `cao` và `xuống`, rồi mới ghép sản phẩm.

Vì vậy prompt nền **không được tự đặt chữ ở dải trên/dưới**. Model không biết bố
cục Pillow đã đo ra bao nhiêu và chữ model vẽ vừa dễ sai dấu vừa bị chồng chữ.

### Trang trí nền được phép và vật thể cạnh tranh bị cấm

Vùng giữa được phép có trang trí **nhẹ, phẳng hoặc mang tính kiến trúc nền**:
gradient, vòm màu, bục trơn, ánh sáng loang, giấy/vải/đá mịn, pattern rất nhạt.
Những thứ này vẫn hở quanh ảnh cắt rời và làm poster bớt sơ sài.

Không được vẽ vật thể có thể bị hiểu là món hàng hay giành sự chú ý: sản phẩm
tương tự, đồ chơi, cuộn len, giỏ, hoa lớn, thức ăn, người, tay, mannequin. Cũng
không vẽ icon có chữ, logo, ký tự trang trí hoặc watermark.

### Tuỳ chọn: khai báo tường minh vị trí sản phẩm

Thông thường không cần khối này vì code tự tính theo chữ. Chỉ khai báo khi có chủ
đích bố cục rõ; khai báo tường minh **thắng** giá trị tự tính:

```
VỊ TRÍ SẢN PHẨM
cao: 0.78
xuống: 0.02
```

`cao` là chiều cao món hàng / chiều cao ảnh. `xuống` là độ đẩy xuống so với tâm
ảnh (số âm đẩy lên). Code kẹp `cao 0.30–0.90`, `xuống −0.15…0.15`.

Khi tự khai báo, dùng công thức sau để biết vùng sản phẩm và bóng có thể chạm:

```
mép trên sản phẩm = (1 − cao) / 2 + xuống
mép dưới          = mép trên + cao
VÙNG CẤM          = từ (mép trên − 3%) đến (mép dưới + 5%)
```

3% trên và 5% dưới dành cho bóng mềm. Không nhét quá nhiều chữ vào vùng còn lại;
nếu xung đột, bỏ bớt feature trước khi làm sản phẩm nhỏ đi.

## Khối POSTER

Dùng đúng sáu tên trường dùng chung với `design_canva_post.md`:

| Trường | Nội dung |
|---|---|
| `title` | Tên thương hiệu / sản phẩm |
| `tagline` | Hook ngắn |
| `features` | Mảng tối đa 3 điểm bán ngắn |
| `price` | Giá; có thể rỗng |
| `cta` | Kêu gọi hành động |
| `handle` | @page / liên hệ |

Không đổi thành `feature_1`, `cta_text`, `website_text` hay tên gần nghĩa khác.
Trường thiếu để `""` hoặc `[]`; code sẽ bỏ hẳn, không vẽ placeholder.

## Định dạng đầu ra

### Chế độ A

```
IMAGE PROMPT
[Prompt tiếng Anh mô tả thiết kế đầy đủ, gồm text tiếng Việt cụ thể trong dấu ngoặc kép. Dài 150–300 words.]

TỶ LỆ
4:5
```

### Chế độ B

````text
IMAGE PROMPT
[Prompt tiếng Anh mô tả CÁI NỀN KHÔNG CHỮ. Dài 120–250 words.]

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\<tên file>_cut.png

POSTER
```json
{
  "title": "[Tên thương hiệu/sản phẩm]",
  "tagline": "[Hook ngắn]",
  "features": ["[Điểm bán 1]", "[Điểm bán 2]", "[Điểm bán 3]"],
  "price": "[Giá hoặc chuỗi rỗng]",
  "cta": "[Kêu gọi hành động]",
  "handle": "[@page/liên hệ]"
}
```
````

Đường dẫn phải tuyệt đối và trỏ tới PNG đã tách nền. Chưa có file thì tự dùng
công cụ cắt ảnh trước.

## Ví dụ output ĐÚNG — chế độ A

```
IMAGE PROMPT
Create a professional Vietnamese Facebook post graphic in 4:5 vertical format
for a handmade crochet shop called "Chàng Dev Tập Móc". Use a warm cream and
brown layout. Render the title "Chàng Dev Tập Móc", three concise feature cards,
a central crocheted bear product scene, and a dark footer bar reading "Nhắn tin
để đặt hàng ngay!". Use friendly rounded typography and small stitch motifs.

TỶ LỆ
4:5
```

## Ví dụ output ĐÚNG — chế độ B

````text
IMAGE PROMPT
Create an empty premium product photography backdrop in 4:5 vertical format.
Warm cream-to-beige gradient, soft diffused light from above, a subtle shallow
arch painted into the back wall and a smooth low studio plinth near the lower
third. Add only a very faint paper texture and restrained ambient shadows. Keep
the composition calm and spacious around the center. Background decoration only:
no products, toys, yarn balls, baskets, people, hands or mannequins. Absolutely
no text, letters, numbers, logos, signage or watermarks anywhere in the image.

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\76da0bf8_IMG_2981_cut.png

POSTER
```json
{
  "title": "Chàng Dev Tập Móc",
  "tagline": "Móc từng mũi nhỏ – Gửi trọn yêu thương",
  "features": [
    "100% handmade – móc tay tỉ mỉ",
    "Sợi mềm mại, an toàn cho bé",
    "Quà tặng ý nghĩa mọi dịp"
  ],
  "price": "299.000₫",
  "cta": "Nhắn tin để đặt hàng ngay!",
  "handle": "@chang_dev_tap_moc"
}
```
````

## Ví dụ output SAI

- ❌ Chế độ B có bất kỳ chữ/logo/watermark nào trong IMAGE PROMPT.
- ❌ Chế độ B tả lại món hàng, người hoặc vật thể cạnh tranh.
- ❌ Quên `ẢNH SẢN PHẨM` hoặc `POSTER` khi có ảnh thật.
- ❌ Dùng tên field khác contract (`feature_1`, `cta_text`, `website_text`).
- ❌ Vẫn bắt model chừa cứng vùng 17–93%; vùng này nay do code đo động.
- ❌ Viết caption hoặc giải thích ngoài format.

## Lưu ý

- Chế độ A vẫn cần text cụ thể trong prompt vì model vẽ toàn bộ thiết kế.
- Chế độ B tuyệt đối không có text trong prompt; JSON giữ nguyên tiếng Việt.
- Facebook Feed dùng 4:5; Story/TikTok dùng 9:16; square dùng 1:1.
