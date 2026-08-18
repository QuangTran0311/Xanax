"""API Routes – Tài sản: file upload thủ công + tổng hợp kết quả (workflow
archive, benchmark) đang nằm rải rác trong DB/đĩa, gom về một nơi để xem/tải.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from hub.database import (
    create_asset, list_assets, get_asset, delete_asset,
    list_benchmarks, get_benchmark_results, get_benchmark_result,
)

router = APIRouter()

ASSETS_DIR = Path(__file__).parent.parent.parent / "data" / "assets"

# Chỉ các định dạng dưới đây được phép hiển thị cùng origin. Đặc biệt KHÔNG thêm
# SVG/HTML: cả hai có thể chứa script và đọc cookie phiên nếu trình duyệt render
# chúng trong origin của ứng dụng. MIME lưu trong DB đến từ client nên không được
# dùng để quyết định; loại phản hồi chỉ được suy ra từ đuôi file do server duyệt.
_PREVIEW_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".log": "text/plain",
    ".json": "application/json",
}
_TEXT_PREVIEW_TYPES = {"text/plain", "application/json"}
# Giới hạn này là đánh đổi có chủ ý: đủ để đọc log/kết quả thông thường nhưng
# không thể kéo nguyên file hàng trăm MB vào RAM và làm treo tab trình duyệt.
TEXT_PREVIEW_LIMIT = 512 * 1024
_PREVIEW_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}


def _safe_name(filename: str) -> str:
    return Path(filename or "file").name


def _preview_media_type(filename: str) -> str:
    media_type = _PREVIEW_TYPES.get(Path(filename).suffix.lower())
    if not media_type:
        raise HTTPException(
            415,
            "Kiểu file này không được phép xem trước; hãy tải file xuống để mở.",
        )
    return media_type


def _inline_text_response(content: bytes, filename: str, media_type: str) -> Response:
    truncated = len(content) > TEXT_PREVIEW_LIMIT
    if truncated:
        content = content[:TEXT_PREVIEW_LIMIT]
    headers = {
        **_PREVIEW_SECURITY_HEADERS,
        "Content-Disposition": f"inline; filename*=utf-8''{quote(_safe_name(filename))}",
        "X-Preview-Truncated": "true" if truncated else "false",
    }
    return Response(content=content, media_type=media_type, headers=headers)


def _preview_file(target: Path, filename: str) -> Response:
    media_type = _preview_media_type(filename)
    if media_type in _TEXT_PREVIEW_TYPES:
        # Chỉ đọc hơn giới hạn đúng một byte để biết có bị cắt, không nạp toàn bộ
        # một file log khổng lồ rồi mới cắt ở bước tạo response.
        with target.open("rb") as source:
            content = source.read(TEXT_PREVIEW_LIMIT + 1)
        return _inline_text_response(content, filename, media_type)
    return FileResponse(
        target,
        media_type=media_type,
        filename=_safe_name(filename),
        content_disposition_type="inline",
        headers=_PREVIEW_SECURITY_HEADERS,
    )


@router.post("/upload", status_code=201)
async def upload_asset(file: UploadFile = File(...), note: str = Form("")):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(file.filename)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest = ASSETS_DIR / stored_name

    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            out.write(chunk)

    asset_id = await create_asset(
        filename=safe_name,
        stored_path=stored_name,
        mime_type=file.content_type or "",
        size_bytes=size,
        source="upload",
        note=note,
    )
    asset = await get_asset(asset_id)
    # Kèm đường dẫn tuyệt đối: công cụ MCP (cut_product…) nhận input_path tuyệt
    # đối, nên nơi gọi phải biết file nằm ở đâu trên đĩa. Không trả ra thì Papa
    # upload xong vẫn phải mở Explorer mò tên file có tiền tố uuid.
    return {**asset, "abs_path": str(dest.resolve()),
            "download_url": f"/api/assets/{asset_id}/download"}


@router.get("/")
async def list_all():
    """Gom 3 nguồn về chung 1 danh sách, mỗi phần tử là MỘT NHÓM (1 lần chạy
    quy trình / 1 benchmark / 1 file upload) chứa bên trong danh sách `files`
    — không tách rời từng file thành 1 đơn vị riêng."""
    items: list[dict] = []

    for a in await list_assets():
        items.append({
            "id": f"upload-{a['id']}",
            "source": "upload",
            "name": a["filename"],
            "label": a["note"] or "",
            "created_at": a["created_at"],
            "deletable": True,
            "files": [{
                "name": a["filename"],
                "size_bytes": a["size_bytes"],
                "mime_type": a["mime_type"],
                "download_url": f"/api/assets/{a['id']}/download",
                "preview_url": f"/api/assets/{a['id']}/preview",
            }],
        })

    from core.project_storage import PROJECTS_DATA_DIR
    if PROJECTS_DATA_DIR.is_dir():
        for run_info_path in PROJECTS_DATA_DIR.glob("*/*/*/run_info.json"):
            try:
                info = json.loads(run_info_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            run_dir = run_info_path.parent
            run_id = info.get("run_id")
            files = []
            for step in info.get("steps", []):
                for key in ("text_file", "image_file"):
                    fname = step.get(key)
                    if not fname:
                        continue
                    fpath = run_dir / fname
                    files.append({
                        "name": fname,
                        "size_bytes": fpath.stat().st_size if fpath.exists() else 0,
                        "mime_type": "image/png" if key == "image_file" else "text/markdown",
                        "note": step.get("agent_name") or "",
                        "download_url": f"/api/workflow/runs/{run_id}/archive-file?path={fname}",
                        "preview_url": f"/api/assets/workflow-runs/{run_id}/preview?path={quote(fname)}",
                    })
            if not files:
                continue
            items.append({
                "id": f"workflow-{run_id}",
                "source": "workflow",
                "name": info.get("task_name") or f"Lần chạy #{run_id}",
                "label": info.get("project_name") or "Chưa gán dự án",
                "created_at": info.get("archived_at") or info.get("completed_at") or "",
                "deletable": False,
                "files": files,
            })

    for b in await list_benchmarks():
        results = await get_benchmark_results(b["id"])
        if not results:
            continue
        files = [{
            "name": f"{r['model']}.json",
            "size_bytes": 0,
            "mime_type": "application/json",
            "note": r.get("recommendation") or "",
            "download_url": f"/api/assets/benchmark-results/{r['id']}/download",
            "preview_url": f"/api/assets/benchmark-results/{r['id']}/preview",
        } for r in results]
        items.append({
            "id": f"benchmark-{b['id']}",
            "source": "benchmark",
            "name": b["name"],
            "label": f"{len(results)} model",
            "created_at": max(r["created_at"] for r in results),
            "deletable": False,
            "files": files,
        })

    items.sort(key=lambda i: i["created_at"], reverse=True)
    return {"assets": items}


@router.get("/benchmark-results/{result_id}/download")
async def download_benchmark_result(result_id: int):
    r = await get_benchmark_result(result_id)
    if not r:
        raise HTTPException(404, "Result not found")
    r["scores"] = json.loads(r.pop("scores_json", "{}") or "{}")
    r["responses"] = json.loads(r.pop("responses_json", "[]") or "[]")
    return JSONResponse(
        content=r,
        headers={"Content-Disposition": f'attachment; filename="benchmark-result-{result_id}.json"'},
    )


@router.get("/benchmark-results/{result_id}/preview")
async def preview_benchmark_result(result_id: int):
    r = await get_benchmark_result(result_id)
    if not r:
        raise HTTPException(404, "Result not found")
    r["scores"] = json.loads(r.pop("scores_json", "{}") or "{}")
    r["responses"] = json.loads(r.pop("responses_json", "[]") or "[]")
    content = json.dumps(r, ensure_ascii=False, indent=2).encode("utf-8")
    return _inline_text_response(
        content, f"benchmark-result-{result_id}.json", "application/json"
    )


@router.get("/workflow-runs/{run_id}/preview")
async def preview_workflow_file(run_id: int, path: str):
    from core.project_storage import get_or_create_run_dir

    try:
        run_dir = (await get_or_create_run_dir(run_id)).resolve()
    except ValueError:
        raise HTTPException(404, "Run not found")
    target = (run_dir / path).resolve()
    if run_dir not in target.parents or not target.is_file():
        raise HTTPException(404, "File not found")
    return _preview_file(target, target.name)


@router.get("/{asset_id}/download")
async def download_asset(asset_id: int):
    a = await get_asset(asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    target = ASSETS_DIR / a["stored_path"]
    if not target.is_file():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(target, filename=a["filename"])


@router.get("/{asset_id}/preview")
async def preview_asset(asset_id: int):
    a = await get_asset(asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    target = ASSETS_DIR / a["stored_path"]
    if not target.is_file():
        raise HTTPException(404, "File not found on disk")
    return _preview_file(target, a["filename"])


@router.delete("/{asset_id}", status_code=204)
async def remove_asset(asset_id: int):
    a = await get_asset(asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    target = ASSETS_DIR / a["stored_path"]
    if target.is_file():
        target.unlink()
    await delete_asset(asset_id)
