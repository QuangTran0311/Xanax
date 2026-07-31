import asyncio
import json

import aiosqlite

from api.routes.workflow import _ensure_webhook_token
from hub import database


def test_ensure_webhook_token_for_multi_trigger():
    raw = json.dumps({"triggers": {"webhook": {"enabled": True}}})
    config = json.loads(_ensure_webhook_token("schedule", raw))
    assert config["webhook_token"]
    assert config["triggers"]["webhook"]["webhook_token"] == config["webhook_token"]


def test_no_webhook_token_when_disabled():
    raw = json.dumps({"triggers": {"webhook": {"enabled": False}}})
    config = json.loads(_ensure_webhook_token("manual", raw))
    assert "webhook_token" not in config


def test_list_workflows_matches_enabled_map_and_active_status(monkeypatch, tmp_path):
    db_path = tmp_path / "triggers.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    async def scenario():
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "CREATE TABLE workflow_tasks ("
                "id INTEGER PRIMARY KEY, name TEXT, status TEXT, trigger_type TEXT, "
                "trigger_config_json TEXT)"
            )
            await db.executemany(
                "INSERT INTO workflow_tasks VALUES (?,?,?,?,?)",
                [
                    (1, "legacy", "active", "webhook", "{}"),
                    (2, "multi", "active", "schedule", json.dumps({
                        "triggers": {"webhook": {"enabled": True}}
                    })),
                    (3, "draft", "draft", "webhook", "{}"),
                    (4, "disabled", "active", "manual", json.dumps({
                        "triggers": {"webhook": {"enabled": False}}
                    })),
                ],
            )
            await db.commit()
        rows = await database.list_workflow_tasks_by_trigger("webhook")
        return [row["id"] for row in rows]

    assert asyncio.run(scenario()) == [1, 2]
