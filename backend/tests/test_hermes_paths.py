from pathlib import Path

from core import hermes_paths


def _clear_path_env(monkeypatch):
    for name in ("HERMES_HOME", "LOCALAPPDATA", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(name, raising=False)


def test_explicit_home_has_highest_priority(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("HERMES_HOME", str(explicit))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "windows"))
    monkeypatch.setattr(hermes_paths.platform, "system", lambda: "Windows")

    assert hermes_paths.hermes_home() == explicit


def test_windows_keeps_local_app_data_location(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    local_app_data = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(hermes_paths.platform, "system", lambda: "Windows")

    assert hermes_paths.hermes_home() == local_app_data / "hermes"


def test_windows_without_local_app_data_returns_none(monkeypatch):
    _clear_path_env(monkeypatch)
    monkeypatch.setattr(hermes_paths.platform, "system", lambda: "Windows")

    assert hermes_paths.hermes_home() is None


def test_linux_prefers_xdg_config_home(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setattr(hermes_paths.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

    assert hermes_paths.hermes_home() == xdg / "hermes"


def test_linux_uses_config_then_existing_legacy_home(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(hermes_paths.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    assert hermes_paths.hermes_home() == home / ".config" / "hermes"

    legacy = home / ".hermes"
    legacy.mkdir()
    assert hermes_paths.hermes_home() == legacy
