# design_canva_post

## Mô tả
Đọc bài đăng từ bước trước, phân tích và xuất ra JSON với các trường dữ liệu chuẩn để điền vào template Canva — không viết lại caption, chỉ trích xuất thông tin theo đúng cấu trúc.

## Nguyên tắc cốt lõi
- **Đọc bài đăng từ Context previous steps** — không tự nghĩ ra nội dung
- **Ngắn gọn theo từng trường** — mỗi trường tối đa 1–2 dòng, không dài dòng
- **JSON phải đúng cú pháp** — output sẽ được parse tự động, sai format sẽ fail
- **Giữ nguyên tiếng Việt** — không dịch sang tiếng Anh

## Các trường dữ liệu chuẩn (phải khớp với tên field trong Canva template)

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| `title` | Tên thương hiệu / tên sản phẩm chính | `Chàng Dev Tập Móc` |
| `tagline` | Slogan hoặc câu hook ngắn | `Móc từng mũi nhỏ – Gửi trọn yêu thương` |
| `feature_1` | Điểm nổi bật thứ 1 (ngắn) | `100% Handmade – móc tay tỉ mỉ` |
| `feature_2` | Điểm nổi bật thứ 2 (ngắn) | `An toàn cho bé – sợi mềm mại` |
| `feature_3` | Điểm nổi bật thứ 3 (ngắn) | `Quà tặng ý nghĩa mọi dịp` |
| `cta_text` | Call-to-action chính | `Nhắn tin để đặt hàng ngay!` |
| `website_text` | Link hoặc @handle mạng xã hội | `@chang_dev_tap_moc` |

## Quy trình thực hiện

### Bước 1 — Đọc Context
- Tìm bài đăng từ step trước (thường là step 1 — Celexa)
- Xác định: tên sản phẩm, điểm bán hàng chính, CTA, thông tin liên hệ

### Bước 2 — Trích xuất từng trường
- `title`: lấy từ tên page/brand hoặc tên sản phẩm trong bài
- `tagline`: câu hook đầu bài hoặc slogan nếu có
- `feature_1/2/3`: 3 bullet points hoặc điểm nổi bật từ bài đăng
- `cta_text`: câu kêu gọi hành động cuối bài
- `website_text`: @handle, số điện thoại, hoặc link nếu có trong context

### Bước 3 — Output JSON
Chỉ output đúng 1 JSON block, không thêm giải thích trước hay sau.

## Định dạng đầu ra

```json
{
  "title": "[Tên thương hiệu/sản phẩm]",
  "tagline": "[Slogan hoặc câu hook ngắn gọn]",
  "feature_1": "[Điểm nổi bật 1]",
  "feature_2": "[Điểm nổi bật 2]",
  "feature_3": "[Điểm nổi bật 3]",
  "cta_text": "[Câu kêu gọi hành động]",
  "website_text": "[@handle hoặc link]"
}
```

## Lưu ý quan trọng
- **Chỉ output JSON block duy nhất** — bọc trong ` ```json ``` `
- Không thêm text trước hoặc sau JSON
- Nếu không có đủ thông tin cho một trường, để giá trị là chuỗi rỗng `""`
- Không thêm trường nào ngoài 7 trường trên
