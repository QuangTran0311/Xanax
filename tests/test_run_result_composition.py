from api.websocket_workflow import (
    _compose_run_result, _extract_image_markdown, _strip_image_processing,
)

IMG = "/api/workflow/runs/95/archive-file?path=02_lexapro.png"


def test_strips_prompt_block_at_start_of_output():
    # Bước tạo ảnh trả về prompt ngay từ ký tự đầu — không có dòng trống phía trước.
    text = f"IMAGE PROMPT\nCreate a poster...\n\nTỶ LỆ\n4:5\n\n![Ảnh đã tạo]({IMG})"
    assert _strip_image_processing(text) == ""


def test_strips_prompt_block_after_caption():
    text = "Caption bài đăng\n\nIMAGE PROMPT\nCreate a poster..."
    assert _strip_image_processing(text) == "Caption bài đăng"


def test_extract_image_markdown():
    assert _extract_image_markdown(f"abc ![Ảnh đã tạo]({IMG})") == [IMG]


def test_compose_keeps_caption_and_attaches_image():
    outputs = [
        {"output_content": "Caption bài đăng\n\n#hashtag"},
        {"output_content": f"IMAGE PROMPT\nCreate a poster\n\nTỶ LỆ\n4:5\n\n![Ảnh đã tạo]({IMG})"},
    ]
    result = _compose_run_result(outputs)
    assert result.startswith("Caption bài đăng")
    assert "IMAGE PROMPT" not in result
    assert f"![Ảnh đã tạo]({IMG})" in result


def test_compose_without_image():
    outputs = [{"output_content": "Chỉ có chữ"}]
    assert _compose_run_result(outputs) == "Chỉ có chữ"


def test_compose_ignores_empty_trailing_output():
    outputs = [
        {"output_content": "Nội dung thật"},
        {"output_content": "IMAGE PROMPT\nabc"},
    ]
    assert _compose_run_result(outputs) == "Nội dung thật"
