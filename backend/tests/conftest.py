"""Fixture chung: mọi test dùng database tạm, không chạm vào dữ liệu vận hành."""
import shutil

import pytest

from api.routes.auth import login_rate_limiter
from core import project_storage
from hub import database


@pytest.fixture(scope="session")
async def database_template(tmp_path_factory):
    template_path = tmp_path_factory.mktemp("database-template") / "xanax-test.db"
    original_path = database.DB_PATH
    database.DB_PATH = template_path
    try:
        await database.init_db()
    finally:
        database.DB_PATH = original_path
    return template_path


@pytest.fixture(autouse=True)
async def isolated_database(database_template, tmp_path, monkeypatch):
    test_database = tmp_path / "xanax-test.db"
    shutil.copyfile(database_template, test_database)
    monkeypatch.setattr(database, "DB_PATH", test_database)
    monkeypatch.setattr(project_storage, "PROJECTS_DATA_DIR", tmp_path / "projects")
    project_storage._run_dir_cache.clear()
    login_rate_limiter.reset()
    yield
    project_storage._run_dir_cache.clear()
    login_rate_limiter.reset()
