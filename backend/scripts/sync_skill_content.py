"""Đồng bộ bản chép Markdown vào nội dung skill đang chạy trong database.

Ví dụ trên VPS (xem trước là mặc định; bình thường chỉ cần ``--apply``):

    sudo -u xanax /opt/xanax/.venv/bin/python /opt/xanax/backend/scripts/sync_skill_content.py generate_post_image
    sudo -u xanax /opt/xanax/.venv/bin/python /opt/xanax/backend/scripts/sync_skill_content.py generate_post_image --apply

Chỉ thêm ``--force`` khi script cảnh báo content có thể đã được sửa tay trên giao diện.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _configure_utf8_output() -> None:
    # Console Windows mặc định dùng cp1252; nếu không ép UTF-8, diff tiếng Việt
    # có thể làm script chết khi print. Đừng xoá đoạn này vì tưởng là thừa.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Một số luồng được redirect hoặc thay trong test không cho cấu hình lại.
            pass


_configure_utf8_output()


BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
SKILLS_DIR = BACKEND_DIR / "skills"
BACKUP_DIR = BACKEND_DIR / "data"
# Script thường được gọi bằng đường dẫn tuyệt đối từ một cwd bất kỳ trên VPS.
# Chèn backend theo vị trí file, không theo cwd hay sys.path[0], để import cùng
# cấu hình database mà app thật đang dùng (bẫy này từng làm hỏng bản 2.8.2).
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass(frozen=True)
class SkillRow:
    id: int
    name: str
    config_json: str
    config: dict[str, object]


def _default_database_path() -> Path:
    from hub.database import DB_PATH

    path = Path(DB_PATH)
    # App production chạy với WorkingDirectory=backend. Nếu cấu hình cũ còn dùng
    # path tương đối, neo cùng chỗ đó để việc gọi script từ /root hay /tmp không
    # vô tình mở một database khác.
    return path if path.is_absolute() else BACKEND_DIR / path


def _read_skill(connection: sqlite3.Connection, name: str) -> SkillRow | None:
    row = connection.execute(
        "SELECT id, name, config_json FROM skills WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        return None

    raw_config = row[2] or ""
    try:
        config = json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"config_json của skill '{name}' không phải JSON hợp lệ: {exc}"
        ) from exc
    if not isinstance(config, dict):
        raise ValueError(f"config_json của skill '{name}' phải là một JSON object")
    return SkillRow(id=row[0], name=row[1], config_json=raw_config, config=config)


def _normalize_newlines(content: str) -> str:
    """Chuẩn hoá CRLF/CR về LF để Git và SQLite không lệch giả."""
    return content.replace("\r\n", "\n").replace("\r", "\n")


def _git_history_contains(
    content: str, file_path: Path, repo_root: Path
) -> tuple[bool | None, str | None]:
    """Tìm content trong toàn bộ lịch sử Git; None nghĩa là không xác minh được."""
    try:
        relative = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None, "file nằm ngoài repository"

    git_prefix = [
        "git",
        "-c",
        f"safe.directory={repo_root.resolve().as_posix()}",
        "-C",
        str(repo_root),
    ]
    try:
        log_result = subprocess.run(
            [
                *git_prefix,
                "log",
                "--format=%H",
                "--",
                relative,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return None, f"không chạy được git: {exc}"
    if log_result.returncode != 0:
        detail = log_result.stderr.strip() or "git log trả về lỗi không rõ nguyên nhân"
        return None, detail

    expected = _normalize_newlines(content)
    commits = [line.strip() for line in log_result.stdout.splitlines() if line.strip()]
    for commit in commits:
        try:
            show_result = subprocess.run(
                [*git_prefix, "show", f"{commit}:{relative}"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            return None, f"không chạy được git: {exc}"
        if show_result.returncode != 0:
            detail = show_result.stderr.strip() or f"git show {commit} trả về lỗi"
            return None, detail
        if _normalize_newlines(show_result.stdout) == expected:
            return True, None

    return False, None


def _line_changes(old: str, new: str) -> tuple[int, int]:
    added = removed = 0
    matcher = difflib.SequenceMatcher(a=old.splitlines(), b=new.splitlines())
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            removed += old_end - old_start
        if tag in {"replace", "insert"}:
            added += new_end - new_start
    return added, removed


def _unified_diff(old: str, new: str, name: str, file_path: Path) -> str:
    lines = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"database:skills/{name}/config_json.content",
        tofile=str(file_path),
        lineterm="",
    )
    return "\n".join(lines)


def _backup_config(raw_config: str, name: str, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Tên skill đến từ DB nhưng vẫn lọc để không biến backup thành path traversal.
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = backup_dir / f"skill_{safe_name}_config_json_{timestamp}.json"
    path.write_text(raw_config, encoding="utf-8")
    return path


def sync_skill_content(
    *,
    name: str,
    file_path: Path,
    database_path: Path,
    backup_dir: Path,
    repo_root: Path = REPO_ROOT,
    apply: bool = False,
    force: bool = False,
) -> int:
    file_path = file_path.resolve()
    database_path = database_path.resolve()
    if not file_path.is_file():
        print(f"LỖI: Không tìm thấy file Markdown: {file_path}", file=sys.stderr)
        return 2
    if not database_path.is_file():
        # sqlite3.connect tự tạo file rỗng nếu sai đường dẫn; chặn việc đó để lỗi
        # cấu hình production không bị ngụy trang thành lỗi thiếu bảng.
        print(f"LỖI: Không tìm thấy database: {database_path}", file=sys.stderr)
        return 2

    file_content = file_path.read_text(encoding="utf-8")
    try:
        with sqlite3.connect(database_path) as connection:
            skill = _read_skill(connection, name)
            if skill is None:
                print(
                    f"LỖI: Không có skill tên '{name}' trong database; không tạo mới.",
                    file=sys.stderr,
                )
                return 3

            current_content = skill.config.get("content", "")
            if not isinstance(current_content, str):
                print(
                    f"LỖI: config_json.content của skill '{name}' phải là chuỗi.",
                    file=sys.stderr,
                )
                return 2

            added, removed = _line_changes(current_content, file_content)
            print(_unified_diff(current_content, file_content, name, file_path))
            print(f"\nThống kê: +{added} dòng, -{removed} dòng")

            history_match, git_error = _git_history_contains(
                current_content, file_path, repo_root
            )
            needs_force = history_match is not True
            if history_match is False:
                print(
                    "\nCẢNH BÁO: content trong database không khớp bất kỳ phiên bản "
                    "nào trong lịch sử Git của file Markdown.",
                    file=sys.stderr,
                )
                print(
                    "Có dấu hiệu skill đã được sửa tay trên giao diện; ghi đè có thể "
                    "làm mất thay đổi đó.",
                    file=sys.stderr,
                )
            elif history_match is None:
                print(
                    "\nCẢNH BÁO: Không thể kiểm tra lịch sử Git của file Markdown; "
                    "không thể xác minh content trong database từng được đồng bộ từ repo.",
                    file=sys.stderr,
                )
                print(f"Chi tiết lỗi Git: {git_error}", file=sys.stderr)

            if needs_force:
                print(
                    "Nếu chủ ý ghi đè bằng --force, config_json cũ sẽ được sao lưu trong: "
                    f"{backup_dir.resolve()}",
                    file=sys.stderr,
                )

            if current_content == file_content:
                print("Nội dung đã đồng bộ; database không cần thay đổi.")
                return 0
            if not apply:
                print("DRY-RUN: database chưa bị thay đổi. Dùng --apply để yêu cầu ghi.")
                if needs_force:
                    print("Khi áp dụng trường hợp cảnh báo này còn cần thêm --force.")
                return 0
            if needs_force and not force:
                print(
                    "LỖI: Từ chối ghi vì content database không được xác nhận trong "
                    "lịch sử Git. Kiểm tra diff rồi chạy lại với --apply --force nếu "
                    "chủ ý ghi đè.",
                    file=sys.stderr,
                )
                return 4

            updated_config = dict(skill.config)
            updated_config["content"] = file_content
            updated_raw = json.dumps(updated_config, ensure_ascii=False)

            backup_path = _backup_config(skill.config_json, name, backup_dir.resolve())
            print(f"Đã sao lưu config_json cũ: {backup_path}")

            # So sánh config_json cũ trong UPDATE để một lần sửa qua giao diện xảy
            # ra sau lúc in diff không bị transaction này âm thầm đè mất.
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE skills SET config_json = ? WHERE id = ? AND config_json = ?",
                (updated_raw, skill.id, skill.config_json),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                print(
                    "LỖI: Skill đã thay đổi sau khi đọc; không ghi. Hãy xem diff lại.",
                    file=sys.stderr,
                )
                return 5
            connection.commit()

            verified = _read_skill(connection, name)
            if verified is None or verified.config.get("content") != file_content:
                print(
                    "LỖI: Kiểm tra sau khi ghi thất bại; dùng bản sao lưu để phục hồi.",
                    file=sys.stderr,
                )
                return 5
    except (sqlite3.Error, OSError, ValueError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2

    print(f"Đã đồng bộ content cho skill '{name}'. Các khoá config_json khác được giữ nguyên.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="tên khớp chính xác cột skills.name")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="file .md; mặc định backend/skills/<name>.md",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="chỉ xem diff (mặc định)")
    mode.add_argument("--apply", action="store_true", help="sao lưu rồi ghi database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="cho phép --apply khi content DB không khớp hoặc không kiểm được lịch sử Git",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="đường dẫn SQLite; mặc định lấy từ cấu hình HUB_DATABASE_URL",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=BACKUP_DIR,
        help="nơi lưu config_json cũ (mặc định backend/data)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    file_path = args.file or (SKILLS_DIR / f"{args.name}.md")
    database_path = args.database or _default_database_path()
    return sync_skill_content(
        name=args.name,
        file_path=file_path,
        database_path=database_path,
        backup_dir=args.backup_dir,
        apply=args.apply,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
