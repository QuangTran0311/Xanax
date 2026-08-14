from hub import server
from hub.config import Settings, settings
from hub.database import _database_path_from_url


def test_cookie_secure_defaults_to_production_but_can_be_overridden(monkeypatch):
    # conftest ghim cookie không Secure cho các HTTP client tích hợp. Test đơn vị
    # này cần quan sát đúng giá trị mặc định của Settings, độc lập với ghim đó.
    monkeypatch.delenv("HUB_COOKIE_SECURE", raising=False)

    assert Settings(_env_file=None, debug=False).secure_cookie_enabled is True
    assert Settings(_env_file=None, debug=True).secure_cookie_enabled is False
    assert Settings(
        _env_file=None,
        debug=False,
        cookie_secure=False,
    ).secure_cookie_enabled is False


def test_production_docs_are_disabled(monkeypatch):
    monkeypatch.setattr(settings, "debug", False)
    app = server.create_app()

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_guard_uses_settings_model_defaults(monkeypatch):
    fields = type(settings).model_fields
    monkeypatch.setattr(settings, "secret_key", fields["secret_key"].default)
    monkeypatch.setattr(settings, "api_key", fields["api_key"].default)
    monkeypatch.setattr(settings, "admin_pass", fields["admin_pass"].default)

    issues = server._configuration_issues(creating_default_user=True)
    assert any("HUB_SECRET_KEY" in issue for issue in issues)
    assert any("HUB_API_KEY" in issue for issue in issues)
    assert any("XANAX_ADMIN_PASS" in issue for issue in issues)


def test_xanax_admin_values_are_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("XANAX_ADMIN_USER", "quan-tri")
    monkeypatch.setenv("XANAX_ADMIN_PASS", "mat-khau-manh")

    loaded = Settings(_env_file=None)
    assert loaded.admin_user == "quan-tri"
    assert loaded.admin_pass == "mat-khau-manh"


def test_database_url_is_used_by_aiosqlite_layer():
    assert _database_path_from_url("sqlite+aiosqlite:///D:/data/xanax.db").as_posix() == (
        "D:/data/xanax.db"
    )
    assert _database_path_from_url("sqlite+aiosqlite:///:memory:") == ":memory:"
