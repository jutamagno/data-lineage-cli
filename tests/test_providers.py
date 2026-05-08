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
