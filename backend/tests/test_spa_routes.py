"""Test route cuối phục vụ SPA và file tĩnh ở gốc frontend/dist."""

import pytest
from httpx import ASGITransport, AsyncClient

from hub import server


@pytest.fixture
async def spa_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>SPA test</html>", encoding="utf-8")
    monkeypatch.setattr(server, "_frontend_dist_path", dist)

    app = server.create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, dist


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/.git/config", "/.env"])
async def test_hidden_path_returns_404(spa_client, path):
    client, _ = spa_client
    assert (await client.get(path)).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/hub", "/projects/123", "/projects/1.5/tasks"])
async def test_client_route_returns_spa_index(spa_client, path):
    client, _ = spa_client
    response = await client.get(path)

    assert response.status_code == 200
    assert response.text == "<html>SPA test</html>"
    assert response.headers["cache-control"] == "no-store, must-revalidate"


@pytest.mark.asyncio
async def test_missing_static_file_returns_404(spa_client):
    client, _ = spa_client
    assert (await client.get("/khong-ton-tai.js")).status_code == 404


@pytest.mark.asyncio
async def test_static_file_at_dist_root_is_served(spa_client):
    client, dist = spa_client
    (dist / "manifest.json").write_text('{"name":"Xanax"}', encoding="utf-8")

    response = await client.get("/manifest.json")

    assert response.status_code == 200
    assert response.json() == {"name": "Xanax"}
    assert "cache-control" not in response.headers


@pytest.mark.asyncio
async def test_encoded_path_traversal_returns_404(spa_client, tmp_path):
    client, _ = spa_client
    outside = tmp_path / "bi-mat.txt"
    outside.write_text("khong-duoc-doc", encoding="utf-8")

    response = await client.get("/..%2fbi-mat.txt")

    assert response.status_code == 404
    assert "khong-duoc-doc" not in response.text


@pytest.mark.asyncio
async def test_symlink_outside_dist_returns_404(spa_client, tmp_path):
    client, dist = spa_client
    outside = tmp_path / "ben-ngoai.txt"
    outside.write_text("khong-duoc-doc", encoding="utf-8")
    link = dist / "lien-ket.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Môi trường không cho phép tạo symlink: {exc}")

    response = await client.get("/lien-ket.txt")

    assert response.status_code == 404
    assert "khong-duoc-doc" not in response.text


@pytest.mark.asyncio
async def test_well_known_is_not_blocked_as_hidden(spa_client):
    client, dist = spa_client
    well_known = dist / ".well-known"
    well_known.mkdir()
    (well_known / "security.txt").write_text("Contact: mailto:security@example.test", encoding="utf-8")

    response = await client.get("/.well-known/security.txt")

    assert response.status_code == 200
    assert response.text == "Contact: mailto:security@example.test"


@pytest.mark.asyncio
async def test_missing_react_build_keeps_returning_404(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_frontend_dist_path", tmp_path / "dist-khong-ton-tai")
    app = server.create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/hub")

    assert response.status_code == 404
    assert "React build not found" in response.text
