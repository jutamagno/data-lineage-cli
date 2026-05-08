from __future__ import annotations

from typing import Protocol

from lineage.parser import LineageInfo


class LLMProvider(Protocol):
    def describe(self, lineage: LineageInfo, sql: str) -> str:
        ...


class MockProvider:
    """In-process provider for tests and local development — no AWS required."""

    def __init__(self, response: str = "Mock LLM description.") -> None:
        self.response = response
        self.calls: list[tuple[LineageInfo, str]] = []

    def describe(self, lineage: LineageInfo, sql: str) -> str:
        self.calls.append((lineage, sql))
        return self.response
