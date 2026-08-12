"""Lưu trữ kết quả từng lần chạy quy trình ra ổ đĩa, tổ chức theo dự án/quy
trình/lần chạy để tra cứu về sau. Đây là bản lưu trữ song song — DB
(workflow_outputs) vẫn là nguồn dữ liệu chính hiển thị trên UI, cây thư mục
này chỉ để archive/tải về.

Ảnh sinh ra trong lúc chạy quy trình (core/image_gen.py) được ghi thẳng vào
đây qua get_or_create_run_dir() — không còn lưu vào kho `/static/generated`
nữa. archive_workflow_run() chỉ ghi thêm phần text + run_info.json khi lượt
chạy kết thúc, dùng chung đúng thư mục đó.

Cấu trúc:
  data/projects/<du_an_slug>/<quy_trinh_slug>/<yyyymmdd_hhmmss>/
      run_info.json                  — metadata của lần chạy
      01_<nhan_vien_slug>.md          — nội dung text/post của từng bước
      01_<nhan_vien_slug>.png         — ảnh đi kèm bước đó (nếu có)

Quy trình chưa gắn dự án nào (project_id NULL) vẫn được lưu, vào
data/projects/_unassigned/<quy_trinh_slug>/...
"""
from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

from core.slugify import slugify

logger = logging.getLogger("xanax.project_storage")

PROJECTS_DATA_DIR = Path(__file__).parent.parent / "data" / "projects"
LEGACY_STATIC_DIR = Path(__file__).parent.parent / "data" / "legacy-static"

_IMG_MD_RE = re.compile(r'!\[([^\]]*)\]\(((?:https?://|/)[^\s)]+)\)')
_IMG_PATH_RE = re.compile(r'^(?:https?://|/)\S+\.(png|jpe?g|gif|webp)(\?\S*)?$', re.IGNORECASE)
_OWN_ARCHIVE_URL_RE = re.compile(r'^/api/workflow/runs/(\d+)/archive-file\?path=([^&\s)]+)$')

# Toàn bộ thời gian trong DB (started_at, created_at...) được ghi bằng UTC
# (datetime.utcnow() ở api/websocket_workflow.py). Việt Nam không có DST nên
# quy đổi cố định UTC+7 là đủ, không cần zoneinfo/tzdata.
_VN_OFFSET = timedelta(hours=7)

_run_dir_cache: dict[int, Path] = {}


def _parse_ts(value: str | None) -> datetime:
    """Parse timestamp UTC lưu trong DB và quy đổi sang giờ Việt Nam (UTC+7)."""
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + _VN_OFFSET
        except ValueError:
            pass
    return datetime.utcnow() + _VN_OFFSET


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


async def get_or_create_run_dir(run_id: int) -> Path:
    """Trả về (và tạo nếu chưa có) thư mục archive của 1 lần chạy quy trình.
    Dùng chung bởi image_gen (lưu ảnh ngay lúc sinh, giữa lúc quy trình đang
    chạy) và archive_workflow_run (lưu text lúc kết thúc) — đảm bảo cả 2 ghi
    đúng vào cùng 1 folder."""
    if run_id in _run_dir_cache:
        return _run_dir_cache[run_id]

    from hub.database import get_workflow_run, get_workflow_task, get_project

    run = await get_workflow_run(run_id)
    if not run:
        raise ValueError(f"Workflow run #{run_id} not found")
    task = await get_workflow_task(run["task_id"])
    project = await get_project(run["project_id"]) if run.get("project_id") else None

    project_slug = (project or {}).get("slug") or "_unassigned"
    task_slug = (task or {}).get("slug") or slugify((task or {}).get("name"), fallback="quy-trinh")
    run_time = _parse_ts(run.get("started_at") or run.get("created_at"))
    base_name = run_time.strftime("%Y%m%d_%H%M%S")

    base = PROJECTS_DATA_DIR / project_slug / task_slug
    run_dir = base / base_name
    marker = run_dir / ".run_id"
    if run_dir.exists() and marker.exists() and marker.read_text(encoding="utf-8").strip() != str(run_id):
        # Trùng giây với 1 run khác của cùng quy trình -> tách folder riêng
        run_dir = base / f"{base_name}_r{run_id}"
        marker = run_dir / ".run_id"

    run_dir.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(str(run_id), encoding="utf-8")

    _run_dir_cache[run_id] = run_dir
    return run_dir


def _resolve_local_static(url: str) -> Path | None:
    """Nếu url là 1 đường dẫn /static/... trên server này thì trả về path thật
    trên đĩa (chỉ còn dữ liệu lịch sử trước khi có get_or_create_run_dir),
    ngược lại (URL ngoài) trả về None."""
    if not url.startswith("/static/"):
        return None
    return LEGACY_STATIC_DIR / Path(url.removeprefix("/static/"))


def _own_archive_file(run_dir: Path, url: str) -> str | None:
    """Nếu url trỏ tới chính API archive-file của run này và file đã tồn tại
    sẵn trong run_dir (ảnh được image_gen ghi thẳng vào lúc sinh), trả về tên
    file — không cần copy lại."""
    m = _OWN_ARCHIVE_URL_RE.match(url)
    if not m:
        return None
    filename = unquote(m.group(2))
    return filename if (run_dir / filename).exists() else None


async def resolve_workflow_image_path(content: str) -> Path | None:
    """Resolve an image markdown/archive URL to its physical file.

    Only files inside the referenced workflow run directory are returned.  This
    deliberately does not accept arbitrary filesystem paths from workflow text.
    """
    match = _IMG_MD_RE.search(content or "")
    url = match.group(2) if match else (content or "").strip()
    own = _OWN_ARCHIVE_URL_RE.match(url)
    if not own:
        return None

    run_dir = await get_or_create_run_dir(int(own.group(1)))
    filename = unquote(own.group(2))
    candidate = (run_dir / filename).resolve()
    run_root = run_dir.resolve()
    try:
        candidate.relative_to(run_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _archive_one_output(run_dir: Path, o: dict) -> dict:
    step_order = o.get("step_order") or 0
    agent_slug = slugify(o.get("agent_name"), fallback=f"buoc-{step_order}")
    content = (o.get("edited_content") or o.get("output_content") or "").strip()

    entry = {
        "step_order": step_order,
        "agent_id": o.get("agent_id"),
        "agent_name": o.get("agent_name"),
        "status": o.get("status"),
        "pass_fail": o.get("pass_fail"),
        "notes": o.get("notes"),
        "text_file": None,
        "image_file": None,
    }

    if not content:
        return entry

    # Trường hợp cả output chỉ là 1 đường dẫn ảnh trần, không có text đi kèm
    if _IMG_PATH_RE.match(content):
        own = _own_archive_file(run_dir, content)
        if own:
            entry["image_file"] = own
            return entry
        src = _resolve_local_static(content)
        if src and src.exists():
            ext = Path(content).suffix or ".png"
            dest = _unique_path(run_dir / f"{step_order:02d}_{agent_slug}{ext}")
            shutil.copy2(src, dest)
            entry["image_file"] = dest.name
            return entry
        # ảnh ngoài/không tìm thấy file gốc -> vẫn lưu lại đường dẫn dạng text

    # Text (có thể kèm markdown ![]() trỏ tới ảnh)
    m = _IMG_MD_RE.search(content)
    if m:
        img_url = m.group(2)
        own = _own_archive_file(run_dir, img_url)
        if own:
            entry["image_file"] = own
        else:
            src = _resolve_local_static(img_url)
            if src and src.exists():
                ext = Path(img_url).suffix or ".png"
                img_dest = _unique_path(run_dir / f"{step_order:02d}_{agent_slug}{ext}")
                shutil.copy2(src, img_dest)
                entry["image_file"] = img_dest.name
                # Trỏ lại link ảnh trong file text sang bản đã copy tại chỗ, để
                # thư mục archive tự đủ (không phụ thuộc kho /static/generated cũ)
                content = content.replace(img_url, img_dest.name)

    text_dest = _unique_path(run_dir / f"{step_order:02d}_{agent_slug}.md")
    text_dest.write_text(content, encoding="utf-8")
    entry["text_file"] = text_dest.name
    return entry


async def archive_workflow_run(run_id: int) -> None:
    """Ghi run_info.json + nội dung text (ảnh đã được image_gen ghi sẵn từ lúc
    sinh) vào thư mục archive của lần chạy khi quy trình completed/failed.
    Bỏ qua nếu lần chạy chưa có output nào."""
    from hub.database import get_workflow_run, get_workflow_task, get_project, list_workflow_outputs

    try:
        run = await get_workflow_run(run_id)
        if not run:
            return
        outputs = await list_workflow_outputs(run_id)
        if not outputs:
            return

        task = await get_workflow_task(run["task_id"])
        project = await get_project(run["project_id"]) if run.get("project_id") else None
        if not task:
            return

        run_dir = await get_or_create_run_dir(run_id)
        steps = [_archive_one_output(run_dir, o) for o in outputs]

        run_info = {
            "run_id": run_id,
            "project_id": project["id"] if project else None,
            "project_name": project["name"] if project else None,
            "task_id": task["id"],
            "task_name": task["name"],
            "status": run.get("status"),
            "triggered_by": run.get("triggered_by"),
            "started_at": run.get("started_at"),
            "completed_at": run.get("completed_at"),
            "archived_at": (datetime.utcnow() + _VN_OFFSET).strftime("%Y-%m-%d %H:%M:%S"),
            "steps": steps,
        }
        (run_dir / "run_info.json").write_text(
            json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.exception("Archive lần chạy quy trình #%s thất bại", run_id)
