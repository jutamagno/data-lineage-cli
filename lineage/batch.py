from __future__ import annotations

from pathlib import Path

from lineage.output import lineage_to_dict
from lineage.parser import LineageInfo, extract_lineage


def split_sql(content: str) -> list[str]:
    return [part.strip() for part in content.split(";") if part.strip()]


def analyze_batch(
    file: Path,
    dialect: str = "",
    no_llm: bool = False,
    no_cache: bool = False,
    region: str = "us-east-1",
) -> list[dict[str, object]]:
    content = file.read_text()
    queries = split_sql(content)
    results: list[dict[str, object]] = []

    for sql in queries:
        try:
            lineage = extract_lineage(sql, dialect=dialect)
        except Exception as exc:
            results.append({"sql": sql, "error": str(exc)})
            continue

        description, err = _get_description(sql, lineage, no_llm, no_cache, dialect, region)
        if err:
            results.append(lineage_to_dict(lineage, sql, error=err))
        else:
            results.append(lineage_to_dict(lineage, sql, description=description))

    return results


def _get_description(
    sql: str,
    lineage: LineageInfo,
    no_llm: bool,
    no_cache: bool,
    dialect: str,
    region: str,
) -> tuple[str, str]:
    if no_llm:
        return "", ""

    from lineage.bedrock import BedrockError, BedrockProvider, CredentialsError
    from lineage.cache import get_cached, set_cached

    cached = None if no_cache else get_cached(sql, dialect)
    if cached:
        return cached, ""

    provider = BedrockProvider(region=region)
    try:
        description = provider.describe(lineage, sql)
        if not no_cache:
            set_cached(sql, dialect, description)
        return description, ""
    except (CredentialsError, BedrockError) as exc:
        return "", str(exc)
