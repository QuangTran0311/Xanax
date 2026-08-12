"""One-off: viết lại các link /static/generated/xxx.png còn sót trong DB
(workflow_outputs.output_content / edited_content) sang API archive-file, dựa
vào run_info.json đã archive sẵn (tools/backfill_archive.py). Chạy trước khi
dọn kho `/static/generated` cũ, để lịch sử không bị vỡ ảnh trên UI.

Chạy 1 lần: python tools/rewrite_generated_links.py
"""
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

from hub.database import DB_PATH, init_db
from core.project_storage import get_or_create_run_dir

_STATIC_IMG_RE = re.compile(r'/static/generated/[\w.-]+\.(?:png|jpe?g|gif|webp)', re.IGNORECASE)


async def main():
    await init_db()
    updated = 0
    skipped = 0
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, run_id, step_order, output_content, edited_content FROM workflow_outputs"
        ) as cur:
            rows = await cur.fetchall()

        for row in rows:
            oc, ec = row["output_content"] or "", row["edited_content"] or ""
            if not (_STATIC_IMG_RE.search(oc) or _STATIC_IMG_RE.search(ec)):
                continue

            run_dir = await get_or_create_run_dir(row["run_id"])
            info_path = run_dir / "run_info.json"
            if not info_path.exists():
                print(f"  [bo qua] output #{row['id']}: khong co run_info.json ({run_dir})")
                skipped += 1
                continue
            info = json.loads(info_path.read_text(encoding="utf-8"))
            step = next((s for s in info["steps"] if s["step_order"] == row["step_order"]), None)
            if not step or not step.get("image_file"):
                print(f"  [bo qua] output #{row['id']}: khong tim thay image_file cho step {row['step_order']}")
                skipped += 1
                continue

            new_url = f"/api/workflow/runs/{row['run_id']}/archive-file?path={step['image_file']}"
            new_oc = _STATIC_IMG_RE.sub(new_url, oc) if oc else oc
            new_ec = _STATIC_IMG_RE.sub(new_url, ec) if ec else ec
            if new_oc != oc or new_ec != ec:
                await db.execute(
                    "UPDATE workflow_outputs SET output_content = ?, edited_content = ? WHERE id = ?",
                    (new_oc, new_ec, row["id"]),
                )
                updated += 1
        await db.commit()

    print(f"Da rewrite {updated} workflow_outputs, bo qua {skipped}.")


if __name__ == "__main__":
    asyncio.run(main())
