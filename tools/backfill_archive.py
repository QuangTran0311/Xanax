"""One-off: archive tất cả lượt chạy quy trình (completed/failed, có project_id)
đã tồn tại từ trước khi có core/project_storage.py, ra data/projects/...

Chạy 1 lần: python tools/backfill_archive.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hub.database import init_db, list_workflow_runs
from core.project_storage import archive_workflow_run, PROJECTS_DATA_DIR


async def main():
    await init_db()  # đảm bảo cột slug + backfill slug cho projects/workflow_tasks đã chạy
    runs = await list_workflow_runs(limit=10_000)
    targets = [r for r in runs if r.get("project_id") and r["status"] in ("completed", "failed")]
    print(f"Tìm thấy {len(targets)} lượt chạy cần archive (trong tổng {len(runs)} lượt chạy).")
    ok = 0
    for r in targets:
        before = set(PROJECTS_DATA_DIR.rglob("run_info.json"))
        await archive_workflow_run(r["id"])
        after = set(PROJECTS_DATA_DIR.rglob("run_info.json"))
        if after - before:
            ok += 1
        else:
            print(f"  [bo qua] run #{r['id']} ({r.get('task_name')}) - khong co output hoac loi")
    print(f"Da archive {ok}/{len(targets)} lot chay vao {PROJECTS_DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
