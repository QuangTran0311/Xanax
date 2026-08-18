<!--
CẢNH BÁO: File này chỉ là bản chép để đọc và version. Nội dung chạy thật nằm ở
skills.config_json.content trong database. Sửa file mà không đồng bộ KHÔNG có tác dụng.
Lệnh VPS: sudo -u xanax /opt/xanax/.venv/bin/python /opt/xanax/backend/scripts/sync_skill_content.py generate_post_image --apply
-->

# generate_post_image

## Mô tả

Đọc bài đăng từ bước trước và chuẩn bị ảnh social media chuyên nghiệp. Nếu có ảnh
sản phẩm thật, model vẫn thiết kế TOÀN BỘ poster kể cả typography tiếng Việt, nhưng
giữ đúng một khoảng khung cảnh tự nhiên theo template để code dán ảnh sản phẩm thật vào sau cùng.

## Hai chế độ — chọn theo dữ kiện có thật

> Người dùng gửi kèm ảnh → CHẾ ĐỘ B. Chỉ đưa chủ đề, không ảnh → CHẾ ĐỘ A.

| | Chế độ A — model vẽ tất | Chế độ B — dùng sản phẩm thật |
|---|---|---|
| Khi nào | Không có ảnh đính kèm | Có ảnh đính kèm |
| Model vẽ | Thiết kế, chữ và món hàng | Thiết kế và chữ; KHÔNG vẽ món hàng |
| `ẢNH SẢN PHẨM` | Không có | Bắt buộc |
| `TEMPLATE` | Không có | Bắt buộc |
| `POSTER` | Không có | Không bắt buộc; có thì ép dùng đường Pillow dự phòng |

Hệ thống đã tự dò ảnh và chốt chế độ trong mục “NGUỒN ẢNH”. Làm theo chỉ dẫn đó,
không hỏi người dùng đường dẫn, tên chế độ, template, tọa độ, `cao`/`xuống`, hoặc
bắt họ tự cắt nền. Chỉ hỏi điều chỉ họ mới biết như giá hoặc tên page.

## Nguyên tắc cốt lõi

- Không output lại caption; bước trước đã viết rồi.
- Chế độ A: prompt mô tả toàn bộ thiết kế, chữ tiếng Việt và món hàng.
- Chế độ B mặc định mới: prompt mô tả toàn bộ thiết kế và chữ tiếng Việt; không
  vẽ món hàng, người cầm hàng hoặc vật thay thế trong vùng sản phẩm.
- Vùng sản phẩm KHÔNG phải ô trống hay placeholder. Cùng bức tường, mặt bàn, texture, phối cảnh,
  ánh sáng và bóng môi trường của toàn cảnh phải tiếp tục chảy tự nhiên xuyên qua vùng này; chỉ
  không đặt vật thể vào đó.
- Không còn luật “cấm mọi chữ” ở chế độ B. Chữ do model vẽ là điều mong muốn.
- Chỉ output đúng format tương ứng, không thêm lời giải thích.

## Quy trình

### Bước 1 — Chắt lọc nội dung

Xác định tên sản phẩm/thương hiệu, một hook, tối đa 3–4 lợi ích, giá nếu có, CTA,
@handle, tone và platform. Không bịa dữ kiện thiếu.

### Bước 2 — Chọn phong cách

- Handmade: kem/be ấm, giấy hoặc vải nhẹ, chữ script phối chữ tròn thân thiện.
- Thời trang: sạch, tương phản, hình học tối giản, type có nhịp điệu.
- F&B: ấm và sáng, không thêm thức ăn cạnh tranh với sản phẩm thật.
- Công nghệ/dịch vụ: navy, gradient hiện đại, bề mặt studio gọn.
- Trẻ em/đồ chơi: pastel, sticker, badge và pattern rất nhẹ.

Model được khuyến khích dùng chữ script có chọn lọc, mũi tên chỉ chi tiết, thẻ bo
góc, badge và sticker. Mọi thứ phải có chủ đích, không chỉ xếp chữ thành từng hàng.

### Bước 3 — Chọn template ở chế độ B

Lexapro tự chọn, không hỏi người dùng:

1. `giua-khung`: món cao và hẹp như móc khóa, búp bê. Vùng sản phẩm x 30%–70%,
   y 22%–74%. Đường chân tường/mép sau mặt bàn cắt ngang ở y=70%, gần đáy vùng để món ghép
   đứng trên mặt phẳng. Tiêu đề ở dải trên; 2–3 thẻ trong y 74%–88%; CTA y 88%–97%.
2. `trai-san-pham`: cần khoe nhiều tính năng hoặc nội dung cần cột riêng. Vùng sản
   phẩm x 6%–56%, y 26%–84%. Tiêu đề toàn ngang y 0%–24%; 3 thẻ bên phải x
   58%–96%, y 26%–84%; CTA y 86%–97%. Đường chân tường/mép sau mặt bàn cắt ngang ở
   y=80%, gần đáy vùng sản phẩm.
3. `luoi-the-duoi`: món bè ngang như bộ lót ly, khăn. Vùng sản phẩm x 22%–78%,
   y 20%–58%. Tiêu đề y 0%–18%; 4 thẻ nhỏ y 60%–76%; ghi chú y 76%–86%; CTA
   y 87%–97%. Đường chân tường/mép sau mặt bàn cắt ngang ở y=54%, gần đáy vùng sản phẩm.

Ưu tiên dáng món hàng trước: cao-hẹp → `giua-khung`, bè-ngang → `luoi-the-duoi`.
Với món gần vuông, nếu có 3 lợi ích cần đọc rõ thì dùng `trai-san-pham`; nếu chỉ
có 1–2 ý thì dùng `giua-khung` để sản phẩm giữ vai trò chính.

### Bước 4 — Soạn IMAGE PROMPT

Chế độ A mô tả đầy đủ layout, typography, text, món hàng và trang trí.

Chế độ B phải:

1. Nêu đúng mã template và mô tả layout của nó.
2. Ghi TƯỜNG MINH vùng sản phẩm bằng phần trăm x/y đúng như danh sách trên.
3. Nói rõ một ảnh chụp sản phẩm thật đã tách nền sẽ được dán vào đúng vùng đó; vì vậy đây phải
   giống một chỗ trống TỰ NHIÊN trên bàn trong cùng khung cảnh, không phải một ô chờ điền.
4. Ra lệnh khung cảnh phải tiếp tục liền mạch xuyên qua vùng ấy: cùng tường, cùng mặt bàn,
   cùng texture, phối cảnh, ánh sáng và bóng môi trường; chỉ không có món hàng, silhouette,
   người, tay, prop, card, badge, icon, chữ hay pattern mạnh đặt bên trong.
5. Đặt toàn bộ chữ, thẻ, badge, sticker và mũi tên BÊN NGOÀI vùng sản phẩm. Mũi tên
   được phép hướng về mép vùng nhưng không vẽ chi tiết sản phẩm giả trong vùng.
6. CẤM TUYỆT ĐỐI mọi dấu hiệu đánh dấu vùng: viền đứt nét, viền liền, khung, hình chữ nhật
   hoặc hình chữ nhật bo góc bao quanh vùng, panel màu khác nền, đường kẻ phân vùng,
   "photo frame", vùng màu phẳng khác tông với xung quanh và watermark placeholder.
7. Ánh sáng và bóng môi trường trong vùng phải liên tục với phần sát bên ngoài; không được có
   ranh giới sáng/tối đột ngột theo hình chữ nhật.
8. Bắt buộc có mặt phẳng để sản phẩm đứng: đường chân tường hoặc mép sau mặt bàn chạy ngang
   gần đáy vùng ở đúng mốc của template — `giua-khung` y=70%, `trai-san-pham` y=80%,
   `luoi-the-duoi` y=54%. Mặt bàn tiếp tục liền mạch cả trong lẫn ngoài vùng.
9. Ghi nguyên văn từng chuỗi tiếng Việt cần model vẽ trong dấu ngoặc kép.

### Luật viết chữ — tránh lặp và tránh “mô tả cho có”

- Tiêu đề, tagline và các thẻ tính năng KHÔNG được dùng lại cùng một từ khóa của
  nhau. Đọc lại toàn bộ trước khi output; nếu một từ nổi bật xuất hiện hai lần,
  viết lại một câu bằng lợi ích khác.
- Mỗi thẻ chỉ nói MỘT LỢI ÍCH rõ ràng cho người mua: cảm xúc nhận được, dịp dùng,
  độ bền, sự tiện lợi, an toàn hoặc giá trị quà tặng.
- Không dùng thẻ để tả bộ phận hoặc dáng vẻ mà người mua không hiểu được lợi ích.

Ví dụ SAI: tagline “Mỏ ngơ ngơ hết sức” cạnh các thẻ “Mỏ cam nhỏ”, “Mặt ngơ ngác”
và “Dáng gọn tay”. “Mỏ” lặp hai lần, “ngơ” lặp ba lần; “Dáng gọn tay” không cho
người mua biết họ được gì.

Ví dụ ĐÚNG:

- Tiêu đề: “Đà Điểu Len Vui Nhộn”
- Tagline: “Nhìn là muốn ôm”
- Thẻ 1: “Quà nhỏ khiến người nhận bật cười”
- Thẻ 2: “Treo balo nhẹ tênh mỗi ngày”
- Thẻ 3: “Sợi mềm bền màu, dùng lâu vẫn xinh”

Ba thẻ lần lượt bán cảm xúc, tình huống sử dụng và độ bền; không kể lại mỏ, mắt,
chân hay lặp keyword của tiêu đề/tagline.

## Đường Pillow dự phòng

Mặc định KHÔNG xuất `POSTER`. Nếu cần tương thích hoặc model typography đang lỗi,
có thể xuất khối `POSTER` theo contract cũ; sự hiện diện của khối này chọn tường
minh renderer Pillow (`core/poster_layer.py`). Khi đã chọn fallback, IMAGE PROMPT
phải là nền không chữ để tránh chồng lên chữ do Pillow vẽ.

Các field hợp lệ: `title`, `tagline`, `features` (tối đa 3), `price`, `cta`, `handle`.
Không đổi sang alias như `feature_1`, `cta_text` hoặc `website_text`.

## Định dạng đầu ra

### Chế độ A

```text
IMAGE PROMPT
[Prompt tiếng Anh 150–300 từ, gồm text tiếng Việt chính xác trong dấu ngoặc kép.]

TỶ LỆ
4:5
```

### Chế độ B — mặc định template

```text
IMAGE PROMPT
[Prompt tiếng Anh 180–350 từ: thiết kế toàn poster và mọi chữ tiếng Việt; nêu tọa độ vùng
sản phẩm bằng phần trăm, ảnh thật sẽ dán vào đó, khung cảnh/mặt bàn phải chảy liền mạch qua
vùng, cấm mọi khung/panel đánh dấu vùng và cấm vật thể/chữ trong riêng vùng ấy.]

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\<tên file>_cut.png

TEMPLATE
giua-khung
```

Đường dẫn phải tuyệt đối và trỏ tới PNG đã tách nền. Chưa có file thì tự dùng công
cụ cắt ảnh trước.

### Chế độ B — fallback tùy chọn

Chỉ thêm khối này sau `TEMPLATE` khi chủ ý dùng Pillow:

```json
POSTER
{
  "title": "Tên sản phẩm",
  "tagline": "Hook ngắn",
  "features": ["Lợi ích 1", "Lợi ích 2", "Lợi ích 3"],
  "price": "299.000₫",
  "cta": "Nhắn tin đặt hàng",
  "handle": "@ten_page"
}
```

## Ví dụ output ĐÚNG — chế độ B

```text
IMAGE PROMPT
Create a polished Vietnamese 4:5 social poster using the giua-khung template for
a tall, narrow handmade ostrich keychain. Use a warm cream and apricot palette,
playful editorial typography, one restrained handwritten script accent, rounded
feature cards, a small star sticker and thin hand-drawn arrows. Render the exact
Vietnamese title "Đà Điểu Len Vui Nhộn" across the top band and the tagline "Nhìn
là muốn ôm" beneath it. Below the product placement coordinates, render three distinct
benefit cards: "Quà nhỏ khiến người nhận bật cười", "Treo balo nhẹ tênh mỗi ngày",
and "Sợi mềm bền màu, dùng lâu vẫn xinh". Add the CTA "Nhắn tin đặt hàng" in the
bottom bar and "@chang_dev_tap_moc" in small type.

The real cut-out product photograph will be composited afterward at x=30% to 70%,
y=22% to 74%. Treat those coordinates as a natural unoccupied place in the same
scene, never as a blank placeholder: continue the same cream wall, subtle texture,
perspective, soft studio light and environmental shadows seamlessly through it,
with no product, toy, animal, silhouette, person, hand, prop, card, badge, icon,
lettering or strong pattern placed there. Continue one warm tabletop across the
entire poster; its rear edge must cross horizontally at y=70% so the inserted item
appears to stand on it. There must be no dashed or solid border, frame, rounded
rectangle, divider, photo frame, differently colored panel, flat color block,
rectangular light/dark boundary or placeholder watermark around these coordinates.
Keep every typography and decoration outside them.

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\76da0bf8_IMG_2981_cut.png

TEMPLATE
giua-khung
```

## Ví dụ output SAI

- Chế độ B chỉ tả nền hoặc cấm mọi chữ; model phải thiết kế cả poster và typography.
- Chế độ B vẽ món hàng, placeholder hoặc sticker lọt vào vùng sản phẩm.
- Chế độ B biến vùng sản phẩm thành ô chờ: vẽ viền đứt nét/viền liền, khung, panel khác màu,
  hình chữ nhật bo góc, đường phân vùng, photo frame, mảng màu phẳng hay watermark placeholder.
- Nền, ánh sáng hoặc bóng bị ngắt theo mép hình chữ nhật thay vì chảy liên tục qua vùng; hoặc
  thiếu đường chân tường/mép bàn tại y=70%, y=80% hay y=54% theo template đã chọn.
- Prompt nói “chừa chỗ ở giữa” nhưng không ghi phần trăm x/y chính xác.
- Quên `ẢNH SẢN PHẨM` hoặc `TEMPLATE` khi có ảnh thật.
- Xuất `POSTER` theo thói quen dù không có chủ ý dùng fallback.
- Lặp keyword giữa tiêu đề, tagline và thẻ; hoặc dùng thẻ tả bộ phận thay vì lợi ích.
- Viết caption hay lời giải thích ngoài format.

## Lưu ý

- Facebook Feed dùng 4:5; Story/TikTok dùng 9:16; square dùng 1:1.
- Code sẽ đo vùng sản phẩm sau khi sinh. Không đạt thì tự sinh lại đúng một lần với
  prompt siết mạnh; lần hai vẫn không đạt thì vẫn ghép và ghi cảnh báo có số đo.
