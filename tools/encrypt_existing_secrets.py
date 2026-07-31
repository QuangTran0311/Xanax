"""Mã hoá các secret đang nằm plaintext trong bảng skills (chạy một lần).

Trước khi có core/secret_crypto.py, api_key/token của skill được lưu nguyên văn
trong xanax.db. Script này mã hoá chúng tại chỗ. Chạy lại nhiều lần vô hại —
giá trị đã mã hoá sẽ bị bỏ qua.

    python tools/encrypt_existing_secrets.py            # xem trước, không ghi
    python tools/encrypt_existing_secrets.py --apply    # ghi thật
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.secret_crypto import SECRET_CONFIG_KEYS, encrypt_secret_config, is_encrypted  # noqa: E402


async def main(apply: bool) -> int:
    from hub.database import DB_PATH, init_db, list_skills, update_skill

    await init_db()
    skills = await list_skills()

    todo = []
    for skill in skills:
        try:
            config = json.loads(skill.get("config_json") or "{}")
        except Exception:
            print(f"  ! skill #{skill['id']} '{skill['name']}': config_json hỏng, bỏ qua")
            continue
        plain = [k for k in SECRET_CONFIG_KEYS if config.get(k) and not is_encrypted(config[k])]
        if plain:
            todo.append((skill, config, plain))

    if not todo:
        print("Không có secret plaintext nào — không cần làm gì.")
        return 0

    print(f"Tìm thấy {len(todo)} skill có secret chưa mã hoá:")
    for skill, config, plain in todo:
        detail = ", ".join(f"{k} (dài {len(str(config[k]))})" for k in plain)
        print(f"  - #{skill['id']} '{skill['name']}' ({skill['type']}): {detail}")

    if not apply:
        print("\nXem trước, CHƯA ghi gì. Chạy lại với --apply để thực hiện.")
        return 0

    backup = Path(str(DB_PATH) + f".bak_before_encrypt_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy(DB_PATH, backup)
    print(f"\nĐã backup DB: {backup.name}")

    for skill, config, _ in todo:
        await update_skill(skill["id"], config_json=json.dumps(encrypt_secret_config(config)))
        print(f"  ✓ mã hoá xong #{skill['id']} '{skill['name']}'")

    # Xác minh: đọc lại và kiểm tra giải mã ra đúng giá trị ban đầu
    from core.secret_crypto import decrypt_secret
    ok = True
    for skill, original, plain in todo:
        row = next((s for s in await list_skills() if s["id"] == skill["id"]), None)
        stored = json.loads(row.get("config_json") or "{}") if row else {}
        for key in plain:
            if not is_encrypted(stored.get(key, "")):
                print(f"  ✗ #{skill['id']}.{key} chưa được mã hoá"); ok = False
            elif decrypt_secret(stored[key]) != original[key]:
                print(f"  ✗ #{skill['id']}.{key} giải mã KHÔNG khớp giá trị gốc"); ok = False
    print("\n✓ Xác minh: giải mã lại khớp giá trị gốc." if ok
          else "\n✗ Có vấn đề — khôi phục từ file backup ở trên.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main("--apply" in sys.argv)))
