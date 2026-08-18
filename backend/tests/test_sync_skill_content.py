"""Kiểm tra công cụ đồng bộ skill mà không bao giờ chạm database thật."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from scripts import sync_skill_content as syncer


def _tao_database(path: Path, *, name: str = "write_post", content: str = "bản git") -> str:
    raw = json.dumps(
        {"content": content, "image_pool_id": 17, "nested": {"giu_nguyen": True}},
        ensure_ascii=False,
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE skills (id INTEGER PRIMARY KEY, name TEXT UNIQUE, config_json TEXT)"
        )
        connection.execute(
            "INSERT INTO skills (name, config_json) VALUES (?, ?)", (name, raw)
        )
    return raw


def _doc_config(path: Path, name: str = "write_post") -> dict:
    with sqlite3.connect(path) as connection:
        raw = connection.execute(
            "SELECT config_json FROM skills WHERE name = ?", (name,)
        ).fetchone()[0]
    return json.loads(raw)


def _tao_repo_git(tmp_path: Path, committed: str = "bản git") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    skill_file = repo / "backend" / "skills" / "write_post.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(committed, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Xanax Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "-m",
            "mốc test",
        ],
        check=True,
    )
    return repo, skill_file


def _commit_file(repo: Path, skill_file: Path, content: str, message: str) -> None:
    skill_file.write_text(content, encoding="utf-8", newline="")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Xanax Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "-m",
            message,
        ],
        check=True,
    )


def test_db_khop_ban_lich_su_cu_thi_apply_khong_can_force_va_giu_khoa_khac(
    tmp_path, capsys
):
    repo, skill_file = _tao_repo_git(tmp_path, committed="bản git\ndòng cũ\n")
    _commit_file(repo, skill_file, "nội dung mới\ndòng hai\n", "bản mới")
    database = tmp_path / "tam.db"
    raw_cu = _tao_database(database, content="bản git\r\ndòng cũ\r\n")
    backup_dir = tmp_path / "backup"

    dry_run = syncer.sync_skill_content(
        name="write_post",
        file_path=skill_file,
        database_path=database,
        backup_dir=backup_dir,
        repo_root=repo,
    )

    assert dry_run == 0
    assert _doc_config(database)["content"] == "bản git\r\ndòng cũ\r\n"
    assert not backup_dir.exists()
    output = capsys.readouterr().out
    assert "--- database:skills/write_post/config_json.content" in output
    assert "Thống kê: +2 dòng, -2 dòng" in output
    assert "DRY-RUN" in output

    applied = syncer.sync_skill_content(
        name="write_post",
        file_path=skill_file,
        database_path=database,
        backup_dir=backup_dir,
        repo_root=repo,
        apply=True,
    )

    assert applied == 0
    config = _doc_config(database)
    assert config["content"] == "nội dung mới\ndòng hai\n"
    assert config["image_pool_id"] == 17
    assert config["nested"] == {"giu_nguyen": True}
    backups = list(backup_dir.glob("skill_write_post_config_json_*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == raw_cu
    assert str(backups[0]) in capsys.readouterr().out


def test_db_lech_ban_git_bi_chan_den_khi_co_force(tmp_path, capsys):
    repo, skill_file = _tao_repo_git(tmp_path)
    skill_file.write_text("nội dung release", encoding="utf-8")
    database = tmp_path / "tam.db"
    _tao_database(database, content="đã sửa trên giao diện")
    backup_dir = tmp_path / "backup"

    blocked = syncer.sync_skill_content(
        name="write_post",
        file_path=skill_file,
        database_path=database,
        backup_dir=backup_dir,
        repo_root=repo,
        apply=True,
    )

    assert blocked != 0
    assert _doc_config(database)["content"] == "đã sửa trên giao diện"
    assert not backup_dir.exists()
    error = capsys.readouterr().err
    assert "sửa tay trên giao diện" in error
    assert str(backup_dir.resolve()) in error
    assert "--apply --force" in error

    forced = syncer.sync_skill_content(
        name="write_post",
        file_path=skill_file,
        database_path=database,
        backup_dir=backup_dir,
        repo_root=repo,
        apply=True,
        force=True,
    )

    assert forced == 0
    assert _doc_config(database)["content"] == "nội dung release"
    assert len(list(backup_dir.glob("*.json"))) == 1


def test_khong_co_git_thi_canh_bao_va_chan_den_khi_co_force(tmp_path, capsys):
    repo = tmp_path / "khong-phai-repo"
    skill_file = repo / "backend" / "skills" / "write_post.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("nội dung release", encoding="utf-8")
    database = tmp_path / "tam.db"
    _tao_database(database)
    backup_dir = tmp_path / "backup"

    result = syncer.sync_skill_content(
        name="write_post",
        file_path=skill_file,
        database_path=database,
        backup_dir=backup_dir,
        repo_root=repo,
        apply=True,
    )

    assert result != 0
    assert _doc_config(database)["content"] == "bản git"
    assert not backup_dir.exists()
    error = capsys.readouterr().err
    assert "Không thể kiểm tra lịch sử Git" in error
    assert "--apply --force" in error


def test_skill_khong_ton_tai_thoat_khac_khong_va_khong_tu_tao(tmp_path, capsys):
    repo, skill_file = _tao_repo_git(tmp_path)
    database = tmp_path / "tam.db"
    _tao_database(database)

    result = syncer.sync_skill_content(
        name="khong_co",
        file_path=skill_file,
        database_path=database,
        backup_dir=tmp_path / "backup",
        repo_root=repo,
        apply=True,
        force=True,
    )

    assert result != 0
    assert "không tạo mới" in capsys.readouterr().err
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM skills").fetchone()[0] == 1


def test_script_chay_bang_duong_dan_tuyet_doi_tu_cwd_bat_ky(tmp_path):
    database = tmp_path / "tam.db"
    _tao_database(database)
    skill_file = tmp_path / "write_post.md"
    skill_file.write_text("nội dung mới", encoding="utf-8")
    cwd_khac = tmp_path / "cwd-khac"
    cwd_khac.mkdir()
    script = Path(syncer.__file__).resolve()
    env = os.environ.copy()
    env["HUB_DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
    # Mô phỏng đúng console Windows mặc định để bắt hồi quy khi in diff tiếng Việt.
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, str(script), "write_post", str(skill_file)],
        cwd=cwd_khac,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "DRY-RUN" in result.stdout
    assert "nội dung mới" in result.stdout
    assert _doc_config(database)["content"] == "bản git"
