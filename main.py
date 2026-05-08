import time

import typer

from lineage.formatter import print_lineage, print_stats
from lineage.history import get_stats, record_run, sql_hash
from lineage.log import configure as configure_logging
from lineage.log import get_logger
from lineage.parser import extract_lineage

configure_logging()
log = get_logger()

app = typer.Typer(help="Data lineage CLI — parse SQL and describe it with AWS Bedrock.")

EXIT_PARSE_ERROR = 2
EXIT_CREDENTIALS_ERROR = 3
EXIT_BEDROCK_ERROR = 4


@app.command()
def analyze(
    sql: str = typer.Argument(..., help="SQL query to analyze"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the Bedrock LLM call"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect: '' (default), bigquery, spark"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region for Bedrock"),
) -> None:
    bound = log.bind(sql_hash=sql_hash(sql), dialect=dialect or "default")

    try:
        lineage = extract_lineage(sql, dialect=dialect)
    except Exception as exc:
        bound.error("sql_parse_failed", error=str(exc))
        record_run(sql, dialect, llm_used=False, error=str(exc))
        raise typer.Exit(code=EXIT_PARSE_ERROR)

    description = ""
    latency_ms: int | None = None

    if not no_llm:
        from lineage.bedrock import BedrockError, CredentialsError, describe_lineage

        t0 = time.monotonic()
        try:
            description = describe_lineage(lineage, sql, region=region)
            latency_ms = int((time.monotonic() - t0) * 1000)
            bound.info("llm_call_succeeded", latency_ms=latency_ms)
        except CredentialsError as exc:
            bound.error("aws_credentials_missing", error=str(exc))
            record_run(sql, dialect, llm_used=True, error=str(exc))
            raise typer.Exit(code=EXIT_CREDENTIALS_ERROR)
        except BedrockError as exc:
            bound.error("bedrock_call_failed", error=str(exc))
            record_run(sql, dialect, llm_used=True, error=str(exc))
            raise typer.Exit(code=EXIT_BEDROCK_ERROR)

    record_run(sql, dialect, llm_used=not no_llm, latency_ms=latency_ms)
    print_lineage(lineage, description)


@app.command()
def stats() -> None:
    """Show usage statistics from local history."""
    print_stats(get_stats())


if __name__ == "__main__":
    app()
