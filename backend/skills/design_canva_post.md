# design_canva_post

## Mô tả

Đọc bài đăng từ bước trước và xuất JSON nội dung thiết kế. Bộ tên trường này dùng
chung với khối `POSTER` của `generate_post_image.md`; không tự đặt alias khác.

## Nguyên tắc

- Đọc bài đăng từ Context previous steps, không tự nghĩ thêm nội dung.
- Mỗi trường ngắn gọn; `features` có tối đa 3 điểm bán.
- Giữ nguyên tiếng Việt và output JSON đúng cú pháp.
- Thiếu dữ liệu thì dùng `""` hoặc `[]`, không viết placeholder vào nội dung.

## Các trường chuẩn

| Trường | Mô tả | Ví dụ |
|---|---|---|
| `title` | Tên thương hiệu / sản phẩm | `Chàng Dev Tập Móc` |
| `tagline` | Slogan hoặc hook ngắn | `Móc từng mũi nhỏ – Gửi trọn yêu thương` |
| `features` | Mảng tối đa 3 điểm bán | `["100% handmade", "An toàn cho bé"]` |
| `price` | Giá bán nếu bài có nêu | `299.000₫` |
| `cta` | Call-to-action | `Nhắn tin để đặt hàng ngay!` |
| `handle` | @handle, số điện thoại hoặc link | `@chang_dev_tap_moc` |

## Quy trình

1. Tìm bài đăng ở step trước.
2. Lấy title, tagline, tối đa 3 feature, giá, CTA và liên hệ có thật trong bài.
3. Chỉ output một JSON block theo đúng schema dưới đây.

## Định dạng đầu ra

```json
{
  "title": "[Tên thương hiệu/sản phẩm]",
  "tagline": "[Slogan hoặc hook]",
  "features": ["[Điểm bán 1]", "[Điểm bán 2]", "[Điểm bán 3]"],
  "price": "[Giá hoặc chuỗi rỗng]",
  "cta": "[Kêu gọi hành động]",
  "handle": "[@handle/liên hệ]"
}
```

Không thêm field ngoài schema và không đổi tên thành `feature_1`, `cta_text` hay
`website_text`; đổi tên sẽ làm Canva và lớp poster trôi contract khỏi nhau.
