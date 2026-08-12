"""
Tests — bước quy trình chỉ được ghi "thành công" khi việc đã thật sự làm.

Sự cố thật: nhân viên đăng Facebook (kỹ năng `facebook_post_page`, loại 'api')
được gán toàn model chạy qua CLI. Model CLI không nhận tools[] nên không một
request nào rời khỏi máy — nhưng nhân viên vẫn sinh ra chữ, không có lỗi nào,
và bước quy trình ghi "Đã chạy xong". Người dùng mở fanpage mới biết chưa có
bài nào.

Nguyên tắc bị vi phạm: log thành công phải dựa trên việc đã làm, không dựa trên
lời nhân viên tự thuật.
"""
import pytest

from core.skill_tools import (
    begin_api_call_tracking,
    collect_tool_invocations,
    end_api_call_tracking,
    record_tool_invocation,
)


class TestToolInvocationLedger:
    def test_records_calls_within_a_step(self):
        token = begin_api_call_tracking()
        try:
            assert collect_tool_invocations() == []
            record_tool_invocation("skill_api_facebook_post_page")
            assert collect_tool_invocations() == ["skill_api_facebook_post_page"]
        finally:
            end_api_call_tracking(token)

    def test_ledger_is_isolated_per_step(self):
        """Sổ của bước này không được rò sang bước kia — nếu không, một bước có
        gọi tool sẽ 'bảo lãnh' cho bước sau không gọi gì."""
        token = begin_api_call_tracking()
        record_tool_invocation("a")
        end_api_call_tracking(token)

        token2 = begin_api_call_tracking()
        try:
            assert collect_tool_invocations() == []
        finally:
            end_api_call_tracking(token2)

    def test_records_outside_tracking_is_harmless(self):
        """Gọi tool ngoài phạm vi 1 bước (vd phòng họp) không được ném lỗi."""
        record_tool_invocation("khong-trong-buoc-nao")
        assert collect_tool_invocations() == []


class TestStepFailsWithoutEvidence:
    """Ráp lại đúng phép kiểm mà bước agent dùng."""

    @staticmethod
    def _step_should_fail(required_tools, invoked):
        """Bản sao logic ở api/websocket_workflow.py cuối bước agent."""
        return bool(required_tools) and not (set(required_tools) & set(invoked))

    def test_required_tool_never_called_fails(self):
        assert self._step_should_fail({"skill_api_facebook_post_page"}, [])

    def test_required_tool_called_passes(self):
        assert not self._step_should_fail(
            {"skill_api_facebook_post_page"}, ["skill_api_facebook_post_page"]
        )

    def test_no_required_tool_passes(self):
        """Nhân viên chỉ có kỹ năng 'custom'/'mcp' — không có việc bắt buộc nào,
        không được đánh trượt họ."""
        assert not self._step_should_fail(set(), [])
        assert not self._step_should_fail(set(), ["cut_product"])

    def test_calling_only_an_optional_tool_still_fails(self):
        """Gọi công cụ tuỳ chọn không thay được việc bắt buộc."""
        assert self._step_should_fail({"skill_api_facebook_post_page"}, ["cut_product"])

    def test_failed_call_still_counts_as_evidence(self):
        """Gọi mà lỗi thì đã có nhánh api_failures đánh trượt với thông báo đúng
        nguyên nhân. Phép kiểm này không được cướp việc đó rồi báo sai lý do."""
        assert not self._step_should_fail(
            {"skill_api_facebook_post_page"}, ["skill_api_facebook_post_page"]
        )


class TestToolCallsAreRecordedWhereExecuted:
    """Sổ phải được ghi ở nơi tool THẬT SỰ chạy, không phải nơi model nói là nó
    gọi — chính chỗ đó mới là bằng chứng.

    Chạy qua `_stream_openai` thật, chỉ giả lập phần SSE của provider.
    """

    @pytest.fixture
    def fake_provider(self, monkeypatch):
        """Lượt 1 trả về một tool_call, lượt 2 trả về chữ."""
        rounds = []

        class FakeResponse:
            def __init__(self, lines):
                self._lines = lines

            def raise_for_status(self):
                pass

            async def aiter_lines(self):
                for line in self._lines:
                    yield line

        class FakeStream:
            def __init__(self, lines):
                self._lines = lines

            async def __aenter__(self):
                return FakeResponse(self._lines)

            async def __aexit__(self, *a):
                return False

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            def stream(self, method, url, headers=None, json=None):
                rounds.append(json)
                if len(rounds) == 1:
                    return FakeStream([
                        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1",'
                        '"function":{"name":"skill_api_facebook_post_page","arguments":"{}"}}]},'
                        '"finish_reason":"tool_calls"}]}',
                        "data: [DONE]",
                    ])
                return FakeStream([
                    'data: {"choices":[{"delta":{"content":"Đã đăng bài."}}]}',
                    "data: [DONE]",
                ])

        monkeypatch.setattr("core.model_pool_bridge.httpx.AsyncClient",
                            lambda *a, **k: FakeClient())
        return rounds

    @pytest.mark.asyncio
    async def test_records_invocation_when_tool_actually_runs(self, fake_provider, monkeypatch):
        import core.model_pool_bridge as mpb

        called = {}

        async def fake_call(name, args):
            called["name"] = name
            return {"ok": True}

        from core.hermes.tool_registry import tool_registry
        monkeypatch.setattr(tool_registry, "call", fake_call)

        token = begin_api_call_tracking()
        try:
            out = "".join([
                chunk async for chunk in mpb._stream_openai(
                    "http://x", "k", "m", [{"role": "user", "content": "đăng bài"}],
                    {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0},
                    tools=[{"type": "function",
                            "function": {"name": "skill_api_facebook_post_page",
                                         "parameters": {}}}],
                )
            ])
            assert called["name"] == "skill_api_facebook_post_page"
            assert collect_tool_invocations() == ["skill_api_facebook_post_page"]
            assert "Đã đăng bài." in out
        finally:
            end_api_call_tracking(token)

    @pytest.mark.asyncio
    async def test_records_even_when_tool_raises(self, fake_provider, monkeypatch):
        """Lời gọi CÓ xảy ra là sự thật dù nó ném lỗi. Không ghi sổ thì bước
        trông như 'chưa hề gọi' và báo sai nguyên nhân."""
        import core.model_pool_bridge as mpb

        async def boom(name, args):
            raise RuntimeError("Facebook từ chối token")

        from core.hermes.tool_registry import tool_registry
        monkeypatch.setattr(tool_registry, "call", boom)

        token = begin_api_call_tracking()
        try:
            [c async for c in mpb._stream_openai(
                "http://x", "k", "m", [{"role": "user", "content": "đăng bài"}],
                {"tokens_in": 0, "tokens_out": 0, "tokens_cache": 0},
                tools=[{"type": "function",
                        "function": {"name": "skill_api_facebook_post_page",
                                     "parameters": {}}}],
            )]
            assert collect_tool_invocations() == ["skill_api_facebook_post_page"]
        finally:
            end_api_call_tracking(token)


class TestOnlyApiSkillsAreMandatory:
    """Không phải công cụ nào cũng là việc bắt buộc.

    Rào chắn bản đầu bắt MỌI nhân viên có tool đều phải gọi tool, và nó đánh
    trượt oan nhân viên tạo ảnh: cô ấy có kèm skill MCP cắt ảnh nhưng lần chạy
    đó không cần cắt, trong khi bài viết và ảnh đều đã giao đủ. Quy trình dừng
    giữa chừng vì một việc chưa bao giờ được yêu cầu.
    """

    @pytest.fixture
    def skills(self, monkeypatch):
        table = {}

        async def fake_get_skill(sid):
            return table.get(sid)

        monkeypatch.setattr("api.websocket_workflow.get_skill", fake_get_skill)
        return table

    @pytest.mark.asyncio
    async def test_api_skill_is_required(self, skills):
        from api.websocket_workflow import _required_tool_names
        skills[7] = {"id": 7, "name": "facebook_post_page", "type": "api"}
        assert await _required_tool_names([7]) == {"skill_api_facebook_post_page"}

    @pytest.mark.asyncio
    async def test_mcp_skill_is_not_required(self, skills):
        """Skill cắt ảnh là công cụ dùng khi cần, không phải việc phải làm."""
        from api.websocket_workflow import _required_tool_names
        skills[11] = {"id": 11, "name": "cat_anh_san_pham", "type": "mcp"}
        assert await _required_tool_names([11]) == set()

    @pytest.mark.asyncio
    async def test_custom_skill_is_not_required(self, skills):
        from api.websocket_workflow import _required_tool_names
        skills[4] = {"id": 4, "name": "generate_post_image", "type": "custom"}
        assert await _required_tool_names([4]) == set()

    @pytest.mark.asyncio
    async def test_lexapro_real_config_is_not_blocked(self, skills):
        """Cấu hình thật của nhân viên tạo ảnh: 1 skill mcp + 1 skill custom.
        Không có việc bắt buộc nào, nên bước không được trượt."""
        from api.websocket_workflow import _required_tool_names
        skills[11] = {"id": 11, "name": "cat_anh_san_pham", "type": "mcp"}
        skills[4] = {"id": 4, "name": "generate_post_image", "type": "custom"}
        assert await _required_tool_names([11, 4]) == set()

    @pytest.mark.asyncio
    async def test_mixed_skills_keep_only_api(self, skills):
        from api.websocket_workflow import _required_tool_names
        skills[7] = {"id": 7, "name": "facebook_post_page", "type": "api"}
        skills[11] = {"id": 11, "name": "cat_anh_san_pham", "type": "mcp"}
        assert await _required_tool_names([7, 11]) == {"skill_api_facebook_post_page"}

    @pytest.mark.asyncio
    async def test_calling_an_optional_tool_does_not_satisfy_a_required_one(self, skills):
        """Gọi công cụ khác không thay được việc bắt buộc — nếu không, nhân viên
        chỉ cần tra cứu vu vơ là qua cửa."""
        from api.websocket_workflow import _required_tool_names
        skills[7] = {"id": 7, "name": "facebook_post_page", "type": "api"}
        skills[11] = {"id": 11, "name": "cat_anh_san_pham", "type": "mcp"}
        required = await _required_tool_names([7, 11])
        invoked = {"cut_product"}
        assert not (required & invoked), "phải vẫn tính là chưa làm việc bắt buộc"
