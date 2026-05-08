from lineage.parser import LineageInfo
from lineage.providers import LLMProvider, MockProvider


def test_mock_returns_configured_response():
    provider = MockProvider(response="test description")
    lineage = LineageInfo(source_tables=["users"])
    assert provider.describe(lineage, "SELECT 1") == "test description"


def test_mock_default_response():
    provider = MockProvider()
    assert provider.describe(LineageInfo(), "SELECT 1") == "Mock LLM description."


def test_mock_records_calls():
    provider = MockProvider()
    lineage = LineageInfo(source_tables=["orders"])

    provider.describe(lineage, "SELECT id FROM orders")
    provider.describe(lineage, "SELECT name FROM orders")

    assert len(provider.calls) == 2
    assert provider.calls[0][1] == "SELECT id FROM orders"
    assert provider.calls[1][1] == "SELECT name FROM orders"


def test_mock_satisfies_protocol():
    provider: LLMProvider = MockProvider()
    result = provider.describe(LineageInfo(), "SELECT 1")
    assert isinstance(result, str)


def test_mock_call_receives_lineage():
    provider = MockProvider()
    lineage = LineageInfo(source_tables=["users"], target_table="summary")

    provider.describe(lineage, "SELECT 1")

    recorded_lineage, _ = provider.calls[0]
    assert recorded_lineage.source_tables == ["users"]
    assert recorded_lineage.target_table == "summary"


# --- OllamaProvider ---

import json  # noqa: E402

import pytest  # noqa: E402

from lineage.providers import OllamaProvider  # noqa: E402


def test_ollama_describe_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"response": "  hello world  "}).encode()

    class _Resp:
        def read(self) -> bytes:
            return body
        def __enter__(self) -> "_Resp":
            return self
        def __exit__(self, *args: object) -> None:
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda _req: _Resp())
    result = OllamaProvider().describe(LineageInfo(), "SELECT 1")
    assert result == "hello world"


def test_ollama_posts_model_and_stream_false(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    captured: list[urllib.request.Request] = []
    body = json.dumps({"response": "ok"}).encode()

    class _Resp:
        def read(self) -> bytes:
            return body
        def __enter__(self) -> "_Resp":
            return self
        def __exit__(self, *args: object) -> None:
            pass

    def fake_urlopen(req: urllib.request.Request) -> _Resp:
        captured.append(req)
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    OllamaProvider(model="mistral", base_url="http://myserver:11434").describe(
        LineageInfo(), "SELECT 1"
    )

    assert len(captured) == 1
    req = captured[0]
    assert "myserver:11434" in req.full_url
    payload = json.loads(req.data)
    assert payload["model"] == "mistral"
    assert payload["stream"] is False


def test_ollama_has_describe_method() -> None:
    provider = OllamaProvider()
    assert callable(provider.describe)
