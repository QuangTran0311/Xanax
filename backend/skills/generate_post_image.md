# generate_post_image

## Mô tả
Đọc bài đăng từ bước trước, viết một IMAGE PROMPT hoàn chỉnh bằng tiếng Anh để model GPT-image tạo ra ảnh social media chuyên nghiệp — có đầy đủ text tiếng Việt, layout, màu sắc và nội dung trực tiếp trong ảnh.

## HAI CHẾ ĐỘ — chọn đúng chế độ TRƯỚC khi viết prompt

Luật chỉ có một dòng, và **người dùng không phải nói gì cả**:

> **Người dùng gửi kèm ảnh → CHẾ ĐỘ B. Chỉ đưa chủ đề, không ảnh → CHẾ ĐỘ A.**

| | Chế độ A — model vẽ tất | Chế độ B — sản phẩm là ảnh thật |
|---|---|---|
| Khi nào | Người dùng chỉ nói chủ đề | Người dùng bấm kẹp giấy gửi ảnh vào |
| IMAGE PROMPT tả gì | Cả thiết kế, kể cả món hàng | **CHỈ CÁI NỀN** |
| Khối `ẢNH SẢN PHẨM` | Không có | **Bắt buộc có** |

Hệ thống đã tự dò xem có ảnh đính kèm hay chưa và nói thẳng cho bạn biết dùng
chế độ nào (mục "NGUỒN ẢNH" trong bối cảnh). **Nghe theo dòng đó**, đừng tự suy
lại từ lời người dùng.

### Người dùng không biết kỹ thuật — đừng hỏi họ

Người gửi ảnh cho bạn thường là chủ shop, không phải dân kỹ thuật. Họ chỉ gửi
ảnh và nói "làm cho tôi tấm ảnh đăng bán". Từ đó trở đi là việc của bạn.

**Cấm hỏi người dùng những câu này** — tự quyết lấy:
- ❌ "Anh/chị cho em đường dẫn file ảnh đã tách nền" → đường dẫn đã có sẵn trong
  tin nhắn, bạn tự đọc
- ❌ "Anh/chị muốn dùng chế độ A hay B?" → họ không biết chế độ là gì
- ❌ "Anh/chị muốn `cao` bao nhiêu?" → tự nhìn món hàng mà chọn
- ❌ "Anh/chị cắt nền giúp em trước nhé" → bạn có công cụ, bạn tự cắt

Chỉ hỏi lại khi thiếu thứ **chỉ người dùng mới biết**: bán món này giá bao nhiêu,
tên page là gì, muốn nhấn vào điểm nào.

Có ảnh thật mà vẫn viết theo chế độ A là hỏng: model sẽ vẽ thêm một món hàng
nữa vào giữa nền, rồi ảnh chụp thật bị dán đè lên — thành hai món chồng nhau.

**Chế độ B là mặc định cho bài bán hàng.** Ảnh đăng bán phải là hàng thật; model
không nhận ảnh đầu vào nên không thể vẽ đúng món hàng của người dùng, bảo nó vẽ
thì nó vẽ ra một món khác.

## Nguyên tắc cốt lõi
- **Viết prompt như mô tả một thiết kế đồ họa cụ thể**, không phải mô tả cảnh ảnh chụp
- **Bao gồm text tiếng Việt chính xác** muốn xuất hiện trong ảnh — model GPT-image có thể render text
- **Không output caption hay nội dung bài đăng lại** — bước trước đã làm rồi
- **Chỉ output đúng format bên dưới**, không thêm giải thích

## Quy trình thực hiện

### Bước 1 — Đọc bài đăng từ Context
Xác định từ bài đăng của bước trước:
- **Tên thương hiệu / sản phẩm**: tên page, tên món hàng
- **Tagline / hook**: câu đầu tiên hoặc slogan nổi bật nhất
- **3 điểm bán hàng chính** (USP): feature quan trọng nhất
- **CTA**: câu kêu gọi hành động cuối bài
- **Tone**: trẻ trung / chuyên nghiệp / gần gũi / cao cấp
- **Platform**: Facebook / Instagram / TikTok (xác định tỷ lệ)

### Bước 2 — Xác định phong cách thiết kế
Chọn phong cách phù hợp với sản phẩm:
- **Handmade / thủ công**: warm beige/cream tones, rounded fonts, cozy aesthetic
- **Thời trang / lifestyle**: clean white, bold typography, minimalist
- **Thực phẩm / F&B**: warm orange/yellow, vibrant, appetite-driven
- **Công nghệ / dịch vụ**: dark/navy background, modern sans-serif, professional
- **Trẻ em / đồ chơi**: pastel colors, playful, rounded elements

### Bước 3 — Soạn IMAGE PROMPT

Prompt cần mô tả đầy đủ:
1. **Loại thiết kế**: "a professional Facebook post graphic / social media advertisement"
2. **Kích thước và tỷ lệ**: vertical 4:5 ratio
3. **Layout cụ thể**: vị trí các phần tử (header, body, footer)
4. **Text chính xác** muốn render trong ảnh: brand name, tagline, features, CTA
5. **Màu sắc**: primary color, accent color, background
6. **Font style**: bold/serif/rounded/modern
7. **Visual elements**: decorative elements, icons, patterns, product imagery nếu có

## Chế độ B — viết prompt cho NỀN, khi sản phẩm là ảnh thật

Sản phẩm sẽ được dán vào giữa nền bằng code, ở vị trí cố định. Biết trước chỗ nó
rơi vào thì mới chừa đúng chỗ. Tính theo chiều cao ảnh, từ trên xuống:

```
  0% ─────────────────────────────
     VÙNG CHỮ (tiêu đề, USP)         ← 0-17%, đặt chữ ở đây
 17% ─────────────────────────────
     
     VÙNG CẤM — sản phẩm nằm đây     ← 20-88%, ngang 9-91%
     tuyệt đối để trống              ← 17-20% và 88-93% là bóng đổ
     
 93% ─────────────────────────────
     VÙNG CHỮ (tên page, CTA)        ← 93-100%
100% ─────────────────────────────
```

Số đo thật, không phải ước lượng: ghép một ảnh sản phẩm lên nền phẳng rồi đo độ
tối từng 1% chiều cao. Trên 17% sạch tuyệt đối; dưới 93% bóng còn dưới 3% độ
tối, mắt không thấy. Nguồn: `_DEFAULT_SCALE=0.68`, `y_offset=0.04` trong
`core/image_compose.py` — đổi hai hằng đó thì bộ số này phải đo lại.

Sáu điều phải có trong prompt nền:

1. **Nói thẳng là nền trống.** "an empty product backdrop", "no products, no
   objects in the center". Không nói thì model tự ý vẽ đồ vào cho đỡ trống.
2. **Chừa vùng cấm.** "keep the entire central area completely empty and
   unobstructed, reserved for a product to be placed later".
3. **Mặt phẳng để đứng.** Đường chân tường / mép bàn nên nằm ở khoảng **85-90%
   chiều cao** — sản phẩm chạm đất ở 88%. Đặt cao quá thì món hàng như lơ lửng,
   thấp quá thì như chìm xuống sàn.
4. **Ánh sáng từ trên xuống, mềm.** "soft diffused light from above". Ảnh sản
   phẩm chụp bằng đèn trần, nền đánh sáng ngang từ bên là nhìn ra ngay đồ ghép.
5. **Bóng đổ nhẹ có sẵn trên nền.** Code đã tự vẽ bóng dưới chân sản phẩm; nền
   chỉ cần bóng môi trường mờ, đừng vẽ bóng gắt đổ về một hướng khác.
6. **Chữ nằm ngoài vùng cấm.** Tiêu đề ở dải trên, tên page / CTA ở dải dưới.
   Nêu rõ vị trí trong prompt: "at the top", "at the bottom center".

Ba thứ **cấm** đưa vào prompt nền:
- ❌ Bất kỳ món hàng nào — kể cả "similar products", "yarn balls", "a basket"
- ❌ Chữ đè lên giữa ảnh, khung viền chạy quanh mép trong
- ❌ Người, tay cầm, mannequin

## Định dạng đầu ra

Chế độ A:

```
IMAGE PROMPT
[Prompt tiếng Anh mô tả thiết kế đầy đủ. Bao gồm text tiếng Việt cụ thể trong dấu ngoặc kép muốn xuất hiện trong ảnh. Dài 150-300 words.]

TỶ LỆ
4:5
```

Chế độ B — thêm khối `ẢNH SẢN PHẨM` ngay sau `TỶ LỆ`:

```
IMAGE PROMPT
[Prompt tiếng Anh mô tả CÁI NỀN. Dài 120-250 words.]

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\<tên file>_cut.png
```

Đường dẫn phải là **tuyệt đối**, trỏ tới file `.png` đã tách nền. Không có file
đã cắt thì cắt trước bằng công cụ cắt ảnh, rồi mới viết khối này.

### Tuỳ chọn: tự quyết kích thước và vị trí món hàng

Mặc định `cao 0.68 · xuống 0.04` hợp với món **cao và hẹp** (con thú dài cổ, ly,
chai). Món **bè ngang** (túi, khay, khăn gấp) thì bề ngang chạm trần 82% trước
khi đủ cao, nhìn ra bé tí giữa khung — lúc đó nâng `cao` lên. Thêm khối này sau
`ẢNH SẢN PHẨM`:

```
VỊ TRÍ SẢN PHẨM
cao: 0.78
xuống: 0.02
```

`cao` — chiều cao món hàng / chiều cao ảnh. `xuống` — đẩy xuống dưới tâm bao
nhiêu phần chiều cao ảnh (số âm là đẩy lên). Không khai báo thì dùng mặc định.
Khai báo một dòng cũng được, dòng còn lại lấy mặc định.

Giá trị ngoài khoảng `cao 0.30–0.90` và `xuống −0.15…0.15` sẽ bị kẹp lại.

**Đổi vị trí thì phải tính lại vùng cấm**, bộ số 17–93% ở trên chỉ đúng với mặc
định:

```
mép trên sản phẩm = (1 − cao) / 2 + xuống
mép dưới          = mép trên + cao
VÙNG CẤM          = từ (mép trên − 3%) đến (mép dưới + 5%)
```

Ba phần trăm phía trên và năm phần trăm phía dưới là chỗ bóng đổ lan ra. Ví dụ
`cao 0.78 · xuống 0.02`: mép trên 13%, mép dưới 91% → vùng cấm **10–96%**, chỉ
còn 10% trên cho tiêu đề và 4% dưới cho tên page. Nâng `cao` là đánh đổi bằng
chỗ đặt chữ — nâng thì phải rút gọn chữ lại.

## Ví dụ output ĐÚNG — chế độ A (không có ảnh thật, model vẽ tất)

> Chỉ dùng khi KHÔNG có ảnh sản phẩm đã tách nền. Có ảnh thật thì xem ví dụ chế
> độ B bên dưới — đừng chép ví dụ này, nó tả cả món hàng vào giữa ảnh.

```
IMAGE PROMPT
Create a professional Vietnamese Facebook post graphic in 4:5 vertical format (1080x1350px) for a handmade crochet toy shop called "Chàng Dev Tập Móc". 

Layout: rounded header section at top with warm beige/brown color scheme. Large bold title text "Chàng Dev Tập Móc" in decorative font. Below, three feature cards each with a small icon and text: "✓ 100% Handmade - Móc tay tỉ mỉ", "✓ An toàn cho bé - Sợi mềm mại", "✓ Quà tặng ý nghĩa mọi dịp". 

Center of image shows cute crocheted bear toys in warm photography style. Bottom footer bar with CTA text "Nhắn tin để đặt hàng ngay!" in white on dark brown background.

Color palette: warm beige (#F5F0E8), brown (#8B5E3C), sage green (#7A9E7E), cream white. Typography: rounded, friendly, Vietnamese-readable fonts. Decorative elements: small yarn ball icons, heart motifs, stitch patterns. Professional product photography quality, clean composition, warm lighting.

TỶ LỆ
4:5
```

## Ví dụ output ĐÚNG — chế độ B (sản phẩm là ảnh thật)

```
IMAGE PROMPT
Create an empty product photography backdrop in 4:5 vertical format (1080x1350px)
for a Vietnamese handmade crochet brand. This is a BACKGROUND ONLY — absolutely
no products, toys, objects, hands or people anywhere in the frame.

Scene: a warm cream studio wall meeting a smooth beige tabletop, with the wall-to-
table edge running horizontally at about 87% down the frame. Soft diffused light
from above, gentle ambient shading in the corners, no harsh directional shadows.
Subtle warm gradient from top-left to bottom-right. Fine paper-like texture.

CRITICAL: keep the entire central area — from 17% to 93% of the height, and the
full width — completely empty, clean and unobstructed. A product photo will be
placed there afterwards.

Text: at the very top, a small centered title in an elegant serif font reading
"Chàng Dev Tập Móc". At the bottom center, small delicate text reading "Nhắn tin
để đặt hàng nhé" with a thin decorative line on each side. Both text blocks must
stay within the top 17% and bottom 7% bands respectively.

Color palette: cream (#F5EFE3), warm beige (#E8D9C0), soft brown text (#6B5744).
Clean, calm, premium handmade brand aesthetic.

TỶ LỆ
4:5

ẢNH SẢN PHẨM
D:\xanax\data\assets\76da0bf8_IMG_2981_cut.png
```

## Ví dụ output SAI

❌ Viết lại caption bài đăng từ bước trước  
❌ Dùng format POSITIVE PROMPT / NEGATIVE PROMPT kiểu Stable Diffusion  
❌ Prompt chỉ mô tả cảnh ảnh không có text (vd: "a cute bear on wooden table")  
❌ Không có text tiếng Việt cụ thể trong prompt  
❌ Thêm giải thích trước hoặc sau format  
❌ **Có ảnh sản phẩm thật mà prompt vẫn tả món hàng** — nền sẽ mọc thêm một món
   nữa, rồi ảnh thật dán đè lên thành hai món chồng nhau  
❌ **Quên khối `ẢNH SẢN PHẨM`** — ảnh chụp thật không được dán vào, công cắt bỏ phí  
❌ Để chữ hoặc hoa văn trang trí rơi vào dải 17-93% chiều cao  

## Lưu ý
- Text trong prompt phải dùng dấu ngoặc kép `"..."` để model hiểu đây là text cần render
- Càng mô tả layout cụ thể (vị trí, kích thước tương đối, màu nền từng vùng), ảnh càng đúng ý
- Với platform Facebook Feed: tỷ lệ 4:5. Instagram Story / TikTok: 9:16. Square: 1:1
