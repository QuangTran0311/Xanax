"""API Routes – Tài sản: file upload thủ công + tổng hợp kết quả (workflow
archive, benchmark) đang nằm rải rác trong DB/đĩa, gom về một nơi để xem/tải.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from hub.database import (
    create_asset, list_assets, get_asset, delete_asset,
    list_benchmarks, get_benchmark_results, get_benchmark_result,
)

router = APIRouter()

ASSETS_DIR = Path(__file__).parent.parent.parent / "data" / "assets"


def _safe_name(filename: str) -> str:
    return Path(filename or "file").name


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
    return await get_asset(asset_id)


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


@router.get("/{asset_id}/download")
async def download_asset(asset_id: int):
    a = await get_asset(asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    target = ASSETS_DIR / a["stored_path"]
    if not target.is_file():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(target, filename=a["filename"])


@router.delete("/{asset_id}", status_code=204)
async def remove_asset(asset_id: int):
    a = await get_asset(asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    target = ASSETS_DIR / a["stored_path"]
    if target.is_file():
        target.unlink()
    await delete_asset(asset_id)
