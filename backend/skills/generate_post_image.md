# generate_post_image

## Mô tả
Đọc bài đăng từ bước trước, viết một IMAGE PROMPT hoàn chỉnh bằng tiếng Anh để model GPT-image tạo ra ảnh social media chuyên nghiệp — có đầy đủ text tiếng Việt, layout, màu sắc và nội dung trực tiếp trong ảnh.

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

## Định dạng đầu ra

```
IMAGE PROMPT
[Prompt tiếng Anh mô tả thiết kế đầy đủ. Bao gồm text tiếng Việt cụ thể trong dấu ngoặc kép muốn xuất hiện trong ảnh. Dài 150-300 words.]

TỶ LỆ
4:5
```

## Ví dụ output ĐÚNG

```
IMAGE PROMPT
Create a professional Vietnamese Facebook post graphic in 4:5 vertical format (1080x1350px) for a handmade crochet toy shop called "Chàng Dev Tập Móc". 

Layout: rounded header section at top with warm beige/brown color scheme. Large bold title text "Chàng Dev Tập Móc" in decorative font. Below, three feature cards each with a small icon and text: "✓ 100% Handmade - Móc tay tỉ mỉ", "✓ An toàn cho bé - Sợi mềm mại", "✓ Quà tặng ý nghĩa mọi dịp". 

Center of image shows cute crocheted bear toys in warm photography style. Bottom footer bar with CTA text "Nhắn tin để đặt hàng ngay!" in white on dark brown background.

Color palette: warm beige (#F5F0E8), brown (#8B5E3C), sage green (#7A9E7E), cream white. Typography: rounded, friendly, Vietnamese-readable fonts. Decorative elements: small yarn ball icons, heart motifs, stitch patterns. Professional product photography quality, clean composition, warm lighting.

TỶ LỆ
4:5
```

## Ví dụ output SAI

❌ Viết lại caption bài đăng từ bước trước  
❌ Dùng format POSITIVE PROMPT / NEGATIVE PROMPT kiểu Stable Diffusion  
❌ Prompt chỉ mô tả cảnh ảnh không có text (vd: "a cute bear on wooden table")  
❌ Không có text tiếng Việt cụ thể trong prompt  
❌ Thêm giải thích trước hoặc sau format  

## Lưu ý
- Text trong prompt phải dùng dấu ngoặc kép `"..."` để model hiểu đây là text cần render
- Càng mô tả layout cụ thể (vị trí, kích thước tương đối, màu nền từng vùng), ảnh càng đúng ý
- Với platform Facebook Feed: tỷ lệ 4:5. Instagram Story / TikTok: 9:16. Square: 1:1
