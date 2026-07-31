import asyncio
from pathlib import Path

import httpx
import pytest

from core import project_storage
from core.skill_tools import (
    _facebook_photos_endpoint,
    _is_facebook_page_post_skill,
    _make_api_skill_handler,
    reset_workflow_image_path,
    set_workflow_image_path,
)


def test_facebook_skill_detection_and_photos_endpoint():
    skill = {"name": "facebook_post_page"}
    endpoint = "https://graph.facebook.com/v19.0/123/feed"
    assert _is_facebook_page_post_skill(skill, endpoint)
    assert _facebook_photos_endpoint(endpoint) == "https://graph.facebook.com/v19.0/123/photos"

    other = {"name": "generic_webhook"}
    assert not _is_facebook_page_post_skill(other, "https://example.com/feed")


def test_resolve_workflow_image_path_rejects_traversal(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    image = run_dir / "post.png"
    image.write_bytes(b"png")

    async def fake_run_dir(run_id):
        assert run_id == 42
        return run_dir

    monkeypatch.setattr(project_storage, "get_or_create_run_dir", fake_run_dir)
    content = "Caption\n\n![Ảnh](/api/workflow/runs/42/archive-file?path=post.png)"
    assert asyncio.run(project_storage.resolve_workflow_image_path(content)) == image.resolve()
    assert asyncio.run(project_storage.resolve_workflow_image_path(
        "![Ảnh](/api/workflow/runs/42/archive-file?path=../secret.png)"
    )) is None


def test_facebook_handler_uploads_multipart(monkeypatch, tmp_path):
    projects = tmp_path / "projects"
    image = projects / "p" / "run" / "post.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image-bytes")
    monkeypatch.setattr(project_storage, "PROJECTS_DATA_DIR", projects)

    captured = {}

    async def fake_post(self, url, **kwargs):
        kwargs["uploaded_bytes"] = kwargs["files"]["source"][1].read()
        captured.update(url=url, **kwargs)
        return httpx.Response(200, text='{"id":"1"}', request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    handler = _make_api_skill_handler(
        "https://graph.facebook.com/v19.0/123/feed",
        "POST",
        "secret-token",
        {},
        facebook_page_post=True,
    )
    result = asyncio.run(handler(
        body={"message": "Caption body"}, image_path=str(image), caption="Full caption",
    ))

    assert result == '{"id":"1"}'
    assert captured["url"].endswith("/123/photos")
    assert captured["data"] == {"caption": "Full caption", "access_token": "secret-token"}
    assert captured["files"]["source"][0] == "post.png"
    assert captured["uploaded_bytes"] == b"image-bytes"
    assert "Authorization" not in captured["headers"]


def test_facebook_handler_uses_workflow_image_fallback(monkeypatch, tmp_path):
    projects = tmp_path / "projects"
    image = projects / "p" / "post.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    monkeypatch.setattr(project_storage, "PROJECTS_DATA_DIR", projects)

    seen = {}

    async def fake_post(self, url, **kwargs):
        seen["filename"] = kwargs["files"]["source"][0]
        return httpx.Response(200, text="ok", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    handler = _make_api_skill_handler(
        "https://graph.facebook.com/v19.0/123/feed", "POST", "token", {},
        facebook_page_post=True,
    )
    token = set_workflow_image_path(str(image))
    try:
        assert asyncio.run(handler(body={"message": "Caption"})) == "ok"
    finally:
        reset_workflow_image_path(token)
    assert seen["filename"] == "post.png"


def test_generic_api_handler_remains_json(monkeypatch):
    captured = {}

    async def fake_request(self, method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200, text="ok", request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    handler = _make_api_skill_handler(
        "https://example.com/hook", "POST", "token", {}, facebook_page_post=False,
    )
    assert asyncio.run(handler(body={"hello": "world"})) == "ok"
    assert captured["json"] == {"hello": "world"}
    assert captured["headers"]["Authorization"] == "Bearer token"
