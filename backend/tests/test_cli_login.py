import json

import pytest

import core.cli_login as cli_login
from core.cli_login import (
    CliLoginManager,
    CliLoginSession,
    CodexLoginSession,
    LoginSessionConflict,
    parse_jsonrpc_line,
)
from core.provider_errors import safe_provider_error


def test_parse_verified_codex_jsonrpc_messages():
    initialized = parse_jsonrpc_line(
        '{"id":1,"result":{"userAgent":"codex","codexHome":"C:\\\\Users\\\\Quang\\\\.codex",'
        '"platformFamily":"windows","platformOs":"windows"}}'
    )
    started = parse_jsonrpc_line(
        '{"id":2,"result":{"type":"chatgptDeviceCode","loginId":"login-123",'
        '"verificationUrl":"https://auth.openai.com/codex/device","userCode":"29CZ-8JBHP"}}'
    )
    completed = parse_jsonrpc_line(
        '{"method":"account/login/completed","params":{"loginId":"login-123",'
        '"success":true,"error":null}}'
    )

    assert initialized["id"] == 1
    assert initialized["result"]["platformFamily"] == "windows"
    assert started["result"] == {
        "type": "chatgptDeviceCode",
        "loginId": "login-123",
        "verificationUrl": "https://auth.openai.com/codex/device",
        "userCode": "29CZ-8JBHP",
    }
    assert completed["method"] == "account/login/completed"
    assert completed["params"]["success"] is True
    assert parse_jsonrpc_line("not json") is None
    assert parse_jsonrpc_line("[]") is None


@pytest.mark.asyncio
async def test_codex_completion_notification_is_read_into_terminal_event():
    session = CodexLoginSession({"id": 7, "api_style": "codex_cli", "cli_config_dir": ""})
    session._login_id = "login-123"

    await session._handle_message(parse_jsonrpc_line(
        '{"method":"account/login/completed","params":{"loginId":"login-123",'
        '"success":true,"error":null}}'
    ))

    assert await session.next_event() == {"type": "completed", "success": True, "error": None}
    assert session.done.is_set()


class _FakeSession(CliLoginSession):
    async def start(self):
        return {"type": "started"}


@pytest.mark.asyncio
async def test_only_one_login_session_per_model_pool_entry(monkeypatch):
    manager = CliLoginManager()
    monkeypatch.setattr(manager, "_make_session", lambda entry: _FakeSession(entry))
    entry = {"id": 42, "api_style": "codex_cli"}

    first, _ = await manager.start(entry)
    with pytest.raises(LoginSessionConflict):
        await manager.start(entry)

    await manager.release(42, first)
    second, _ = await manager.start(entry)
    assert second is not first
    await manager.release(42, second)


@pytest.mark.parametrize("credential_path", [
    r"C:\\Users\\Quang\\accounts\\codex-main",
    "/home/xanax/.claude/accounts/main",
])
def test_safe_provider_error_redacts_credential_paths_and_secrets(credential_path):
    raw = (
        f"failed at {credential_path} CODEX_HOME={credential_path} "
        "refresh_token=top-secret Bearer abc.def.ghi"
    )

    safe = safe_provider_error(raw, {"cli_config_dir": credential_path})

    assert credential_path not in safe
    assert "top-secret" not in safe
    assert "abc.def.ghi" not in safe
    assert "CODEX_HOME" not in safe


def test_safe_provider_error_redacts_normalized_config_path():
    path = r"C:\Users\Quang\accounts\codex-main"
    safe = safe_provider_error(
        "failed under c:/users/quang/accounts/codex-main",
        {"cli_config_dir": path},
    )
    assert "users/quang/accounts" not in safe.lower()


class _FakeCodexStatusProcess:
    instances = []

    def __init__(self, command, env, *, use_pty):
        self.read_chunks = []
        self.methods = []
        self.terminated = False
        self.instances.append(self)

    async def start(self):
        return None

    async def write(self, data):
        message = json.loads(data)
        method = message.get("method")
        if "id" not in message:
            return
        self.methods.append(method)
        request_id = message["id"]
        results = {
            "initialize": {"userAgent": "codex"},
            "account/read": {
                "account": {"type": "chatgpt", "email": "private@example.com"},
                "requiresOpenaiAuth": True,
            },
            "getAuthStatus": {
                "authMethod": "chatgpt", "authToken": None, "requiresOpenaiAuth": True,
            },
        }
        response = json.dumps({"id": request_id, "result": results[method]}) + "\n"
        self.read_chunks.append(response.encode())

    async def read(self):
        return self.read_chunks.pop(0) if self.read_chunks else b""

    async def terminate(self):
        self.terminated = True


@pytest.mark.asyncio
async def test_codex_auth_status_uses_account_read_as_primary_source(monkeypatch):
    _FakeCodexStatusProcess.instances.clear()
    monkeypatch.setattr(cli_login, "_InteractiveProcess", _FakeCodexStatusProcess)

    status = await cli_login._codex_auth_status({"api_style": "codex_cli"})

    process = _FakeCodexStatusProcess.instances[-1]
    assert status == {
        "api_style": "codex_cli", "logged_in": True, "status": "logged_in",
    }
    assert process.methods == ["initialize", "account/read"]
    assert process.terminated is True


@pytest.mark.asyncio
async def test_codex_auth_status_buffers_chunks_and_falls_back_to_auth_method(monkeypatch):
    class FakeFallbackProcess(_FakeCodexStatusProcess):
        async def write(self, data):
            message = json.loads(data)
            method = message.get("method")
            if "id" not in message:
                return
            self.methods.append(method)
            request_id = message["id"]
            results = {
                "initialize": {"userAgent": "codex"},
                "account/read": {"account": None, "requiresOpenaiAuth": True},
                "getAuthStatus": {
                    "authMethod": "chatgpt", "authToken": None,
                    "requiresOpenaiAuth": True,
                },
            }
            unrelated = json.dumps({"id": request_id + 100, "result": {}}) + "\n"
            response = json.dumps({"id": request_id, "result": results[method]}) + "\n"
            chunk = (unrelated + response).encode()
            midpoint = len(chunk) // 2
            self.read_chunks.extend([chunk[:midpoint], chunk[midpoint:]])

    FakeFallbackProcess.instances.clear()
    monkeypatch.setattr(cli_login, "_InteractiveProcess", FakeFallbackProcess)

    status = await cli_login._codex_auth_status({"api_style": "codex_cli"})

    process = FakeFallbackProcess.instances[-1]
    assert status["logged_in"] is True
    assert process.methods == ["initialize", "account/read", "getAuthStatus"]
    assert process.terminated is True


@pytest.mark.asyncio
async def test_claude_auth_status_parses_pretty_printed_json(monkeypatch):
    async def fake_stream_proc(command, env=None, timeout=None):
        output = json.dumps({
            "loggedIn": True,
            "authMethod": "claude.ai",
            "apiProvider": "firstParty",
            "email": "private@example.com",
            "subscriptionType": "pro",
        }, indent=2)
        for line in output.splitlines():
            yield "stdout", line
        yield "exit", "0"

    monkeypatch.setattr(cli_login, "stream_proc", fake_stream_proc)

    status = await cli_login._claude_auth_status({"api_style": "claude_cli"})

    assert status == {
        "api_style": "claude_cli",
        "logged_in": True,
        "status": "logged_in",
        "auth_method": "claude.ai",
        "subscription_type": "pro",
    }
