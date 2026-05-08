import time
from pathlib import Path

import typer

from lineage.batch import analyze_batch
from lineage.formatter import print_lineage, print_stats
from lineage.history import get_stats, record_run, sql_hash
from lineage.log import configure as configure_logging
from lineage.log import get_logger
from lineage.output import render_json, render_json_batch, render_openmetadata
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
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache and always call Bedrock"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect: '' (default), bigquery, spark"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region for Bedrock"),
    output: str = typer.Option("text", "--output", help="Output format: text or json"),
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
        from lineage.bedrock import BedrockError, BedrockProvider, CredentialsError
        from lineage.cache import get_cached, set_cached

        cached = None if no_cache else get_cached(sql, dialect)
        if cached:
            description = cached
            bound.info("cache_hit")
        else:
            provider = BedrockProvider(region=region)
            t0 = time.monotonic()
            try:
                description = provider.describe(lineage, sql)
                latency_ms = int((time.monotonic() - t0) * 1000)
                bound.info("llm_call_succeeded", latency_ms=latency_ms)
                if not no_cache:
                    set_cached(sql, dialect, description)
            except CredentialsError as exc:
                bound.error("aws_credentials_missing", error=str(exc))
                record_run(sql, dialect, llm_used=True, error=str(exc))
                raise typer.Exit(code=EXIT_CREDENTIALS_ERROR)
            except BedrockError as exc:
                bound.error("bedrock_call_failed", error=str(exc))
                record_run(sql, dialect, llm_used=True, error=str(exc))
                raise typer.Exit(code=EXIT_BEDROCK_ERROR)

    record_run(sql, dialect, llm_used=not no_llm, latency_ms=latency_ms)

    if output == "json":
        typer.echo(render_json(lineage, sql, description))
    elif output == "openmetadata":
        typer.echo(render_openmetadata(lineage, sql))
    else:
        print_lineage(lineage, description)


@app.command()
def batch(
    file: Path = typer.Argument(..., help=".sql file with queries separated by ;"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the Bedrock LLM call"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region for Bedrock"),
    watch: bool = typer.Option(False, "--watch", help="Re-analyze on file save (requires watchdog)"),
) -> None:
    """Analyze all queries in a .sql file and print a JSON array."""
    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(code=1)

    if watch:
        _watch_file(file, no_llm=no_llm, no_cache=no_cache, dialect=dialect, region=region)
    else:
        results = analyze_batch(file, dialect=dialect, no_llm=no_llm, no_cache=no_cache, region=region)
        typer.echo(render_json_batch(results))


def _watch_file(
    file: Path,
    no_llm: bool,
    no_cache: bool,
    dialect: str,
    region: str,
) -> None:
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        typer.echo(
            "watchdog is not installed. Install it with:\n"
            "  pip install 'data-lineage-cli[watch]'",
            err=True,
        )
        raise typer.Exit(code=1)

    def _run() -> None:
        results = analyze_batch(file, dialect=dialect, no_llm=no_llm, no_cache=no_cache, region=region)
        typer.echo(render_json_batch(results))

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event: object) -> None:
            src = getattr(event, "src_path", None)
            if src and Path(str(src)).resolve() == file.resolve():
                _run()

    _run()

    observer = Observer()
    observer.schedule(_Handler(), str(file.parent), recursive=False)
    observer.start()
    typer.echo(f"Watching {file} — press Ctrl+C to stop.", err=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@app.command()
def stats() -> None:
    """Show usage statistics from local history."""
    print_stats(get_stats())


if __name__ == "__main__":
    app()
