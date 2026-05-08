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


class OllamaProvider:
    """Local LLM via Ollama HTTP API — no AWS required."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        prompt_version: str = "v1",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.prompt_version = prompt_version

    def describe(self, lineage: LineageInfo, sql: str) -> str:
        import json
        import urllib.request

        from lineage.prompts import build_prompt

        prompt = build_prompt(lineage, sql, version=self.prompt_version)
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            return str(body["response"]).strip()
