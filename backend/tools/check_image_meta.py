"""Kiểm tra tín hiệu nguồn gốc AI trong ảnh, trước khi đăng lên Meta.

Đọc 3 thứ Meta dùng để gắn nhãn "AI info":
  1. IPTC DigitalSourceType (nằm trong XMP) — tín hiệu chính
  2. C2PA manifest (khối JUMBF nhúng trong file)
  3. Phần mềm tạo/chỉnh sửa (EXIF Software, XMP CreatorTool) + lịch sử chỉnh sửa

KHÔNG đọc được watermark vô hình (SynthID, watermark của Meta AI) — thứ đó nằm
trong pixel, chỉ nền tảng giải mã được. "clean" ở đây nghĩa là file không mang
tín hiệu KHAI BÁO, không đảm bảo nền tảng sẽ không nhận ra.

Dùng:
    python tools/check_image_meta.py anh.jpg
    python tools/check_image_meta.py thu_muc/ --recursive
    python tools/check_image_meta.py thu_muc/ --json > bao_cao.json
    python tools/check_image_meta.py anh.jpg --quiet   # chỉ lấy exit code

Exit code: 0 = không file nào mang tín hiệu AI, 1 = có, 2 = lỗi đọc file.
Hàm inspect_image() trả về dict thuần để node/tool trong workflow gọi lại.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import ExifTags, Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".avif"}

# Giá trị IPTC DigitalSourceType báo nội dung do máy sinh, kèm mức độ.
AI_SOURCE_TYPES = {
    "trainedAlgorithmicMedia": ("ai", "Ảnh do mô hình AI sinh ra hoàn toàn"),
    "compositeWithTrainedAlgorithmicMedia": ("ai", "Ảnh thật có ghép phần do AI sinh"),
    "algorithmicMedia": ("ai", "Ảnh do thuật toán sinh"),
    "compositeSynthetic": ("ai", "Ảnh ghép có yếu tố tổng hợp"),
    "syntheticAudio": ("ai", "Âm thanh tổng hợp"),
    "digitalCapture": ("clean", "Ảnh chụp bằng máy"),
    "negativeFilm": ("clean", "Scan từ phim âm bản"),
    "positiveFilm": ("clean", "Scan từ phim dương bản"),
    "print": ("clean", "Scan từ bản in"),
    "composite": ("clean", "Ảnh ghép từ nhiều ảnh thật"),
    "minorHumanEdits": ("clean", "Ảnh thật, chỉnh sửa nhẹ"),
}

VERDICT_LABEL = {
    "ai": "SẼ BỊ GẮN NHÃN — file khai báo nguồn gốc AI",
    "review": "CẦN XEM LẠI — có manifest/dấu vết chỉnh sửa, chưa rõ nội dung khai báo",
    "clean": "KHÔNG mang tín hiệu khai báo AI",
    "error": "Không đọc được file",
}


def _read_xmp(img: Image.Image) -> str:
    """XMP thô dạng chuỗi (Pillow.getxmp() đôi khi trả dict rỗng)."""
    for key in ("XML:com.adobe.xmp", "xmp"):
        raw = img.info.get(key)
        if raw:
            return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    return ""


def inspect_image(path: str | Path) -> dict:
    """Soi một file ảnh. Trả về dict thuần, không in gì — để node gọi lại được."""
    path = Path(path)
    result = {
        "file": str(path),
        "verdict": "clean",
        "source_types": [],   # [{value, level, note}]
        "c2pa": False,
        "software": [],
        "edit_steps": 0,
        "has_xmp": False,
        "notes": [],
    }

    if not path.exists():
        result.update(verdict="error", notes=["Không tìm thấy file"])
        return result

    try:
        blob = path.read_bytes()
        with Image.open(path) as img:
            xmp = _read_xmp(img)
            exif = {
                ExifTags.TAGS.get(tag, tag): value
                for tag, value in (img.getexif() or {}).items()
            }
            result["format"] = img.format
            result["size"] = list(img.size)
    except Exception as exc:  # file hỏng, định dạng lạ, thiếu plugin HEIC...
        result.update(verdict="error", notes=[f"{type(exc).__name__}: {exc}"])
        return result

    result["has_xmp"] = bool(xmp)

    # 1. IPTC DigitalSourceType
    for value in dict.fromkeys(re.findall(r"digitalsourcetype/([A-Za-z]+)", xmp)):
        level, note = AI_SOURCE_TYPES.get(value, ("review", "Giá trị lạ, chưa rõ nghĩa"))
        result["source_types"].append({"value": value, "level": level, "note": note})

    # 2. C2PA — manifest nằm trong khối JUMBF; ở đây chỉ phát hiện sự tồn tại,
    #    đọc nội dung khai báo cần c2patool.
    if b"jumb" in blob and (b"c2pa" in blob or b"contentauth" in blob.lower()):
        result["c2pa"] = True
        result["notes"].append("Có C2PA manifest — chạy `c2patool <file>` để đọc chi tiết")

    # 3. Phần mềm đã đụng vào file
    software = exif.get("Software") or exif.get("ProcessingSoftware")
    tools = re.findall(r"<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>", xmp)
    result["software"] = [str(s).strip() for s in [software, *tools] if s]
    result["edit_steps"] = len(re.findall(r"stEvt:action", xmp))

    # Kết luận
    levels = {item["level"] for item in result["source_types"]}
    if "ai" in levels:
        result["verdict"] = "ai"
    elif "review" in levels or result["c2pa"]:
        result["verdict"] = "review"
    else:
        result["verdict"] = "clean"
        if not xmp:
            result["notes"].append("File không có XMP (thường là ảnh chưa qua trình chỉnh sửa)")

    result["notes"].append(
        "Không kiểm tra được watermark vô hình (SynthID / Meta AI) — nằm trong pixel"
    )
    return result


def collect_targets(args_paths: list[str], recursive: bool) -> list[Path]:
    targets: list[Path] = []
    for raw in args_paths:
        path = Path(raw)
        if path.is_dir():
            it = path.rglob("*") if recursive else path.glob("*")
            targets += sorted(p for p in it if p.suffix.lower() in IMAGE_SUFFIXES)
        else:
            targets.append(path)
    return targets


def print_report(report: dict) -> None:
    icon = {"ai": "[AI]", "review": "[??]", "clean": "[ok]", "error": "[!!]"}[report["verdict"]]
    print(f"\n{icon} {report['file']}")
    print(f"     {VERDICT_LABEL[report['verdict']]}")
    for item in report["source_types"]:
        print(f"     DigitalSourceType = {item['value']} — {item['note']}")
    if report["c2pa"]:
        print("     Có C2PA manifest")
    for name in report["software"]:
        print(f"     Phần mềm: {name}")
    if report["edit_steps"]:
        print(f"     XMP có {report['edit_steps']} bước lịch sử chỉnh sửa")
    for note in report["notes"]:
        print(f"     · {note}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kiểm tra tín hiệu nguồn gốc AI trong ảnh trước khi đăng.",
    )
    parser.add_argument("paths", nargs="+", help="File ảnh hoặc thư mục")
    parser.add_argument("-r", "--recursive", action="store_true", help="Quét thư mục con")
    parser.add_argument("--json", action="store_true", help="Xuất JSON thay vì bảng chữ")
    parser.add_argument("-q", "--quiet", action="store_true", help="Không in, chỉ lấy exit code")
    args = parser.parse_args(argv)

    targets = collect_targets(args.paths, args.recursive)
    if not targets:
        print("Không có file ảnh nào khớp.", file=sys.stderr)
        return 2

    reports = [inspect_image(p) for p in targets]

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    elif not args.quiet:
        for report in reports:
            print_report(report)
        counts = {key: sum(r["verdict"] == key for r in reports) for key in VERDICT_LABEL}
        print(
            f"\nTổng {len(reports)} file — "
            f"{counts['ai']} mang tín hiệu AI, {counts['review']} cần xem lại, "
            f"{counts['clean']} sạch, {counts['error']} lỗi đọc"
        )

    if any(r["verdict"] == "error" for r in reports):
        return 2
    return 1 if any(r["verdict"] in ("ai", "review") for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
