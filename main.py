import time
from pathlib import Path

import typer

from lineage.batch import analyze_batch
from lineage.formatter import print_lineage, print_stats
from lineage.history import get_stats, record_run, sql_hash
from lineage.log import configure as configure_logging
from lineage.log import get_logger
from lineage.output import render_json, render_json_batch, render_mermaid, render_openmetadata
from lineage.parser import extract_lineage

configure_logging()
log = get_logger()

app = typer.Typer(help="Data lineage CLI — parse SQL and describe it with AWS Bedrock or Ollama.")

EXIT_PARSE_ERROR = 2
EXIT_CREDENTIALS_ERROR = 3
EXIT_BEDROCK_ERROR = 4

_DEMO_SQL: list[tuple[str, str]] = [
    (
        "Simple JOIN",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'paid'",
    ),
    (
        "Aggregate with filter",
        "SELECT region, SUM(amount) AS total FROM sales WHERE year = 2024 GROUP BY region",
    ),
    (
        "CTE",
        "WITH recent AS (SELECT id, amount FROM transactions WHERE created_at > '2024-01-01') "
        "SELECT id, amount FROM recent",
    ),
    (
        "INSERT INTO … SELECT",
        "INSERT INTO summary (region, total) SELECT region, SUM(amount) FROM sales GROUP BY region",
    ),
    (
        "UNION",
        "SELECT id, name FROM customers UNION SELECT id, name FROM prospects",
    ),
    (
        "CREATE TABLE AS SELECT",
        "CREATE TABLE report AS SELECT c.name, SUM(o.total) AS revenue "
        "FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name",
    ),
]


@app.command()
def analyze(
    sql: str = typer.Argument(..., help="SQL query to analyze"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the LLM call (same as --provider none)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache and always call the LLM"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect: '' (default), bigquery, spark"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region for Bedrock"),
    output: str = typer.Option("text", "--output", help="Output format: text, json, openmetadata, mermaid"),
    provider: str = typer.Option("", "--provider", help="LLM provider: bedrock, ollama, none"),
    ollama_model: str = typer.Option("llama3.2", "--ollama-model", help="Ollama model name"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Ollama base URL"),
) -> None:
    """Parse and describe a single SQL query."""
    bound = log.bind(sql_hash=sql_hash(sql), dialect=dialect or "default")

    try:
        lineage = extract_lineage(sql, dialect=dialect)
    except Exception as exc:
        bound.error("sql_parse_failed", error=str(exc))
        record_run(sql, dialect, llm_used=False, error=str(exc))
        raise typer.Exit(code=EXIT_PARSE_ERROR)

    # Resolve effective provider: explicit --provider wins, else respect --no-llm
    effective = provider if provider else ("none" if no_llm else "bedrock")

    description = ""
    latency_ms: int | None = None

    if effective == "bedrock":
        from lineage.bedrock import BedrockError, BedrockProvider, CredentialsError
        from lineage.cache import get_cached, set_cached

        cached = None if no_cache else get_cached(sql, dialect)
        if cached:
            description = cached
            bound.info("cache_hit")
        else:
            bedrock = BedrockProvider(region=region)
            t0 = time.monotonic()
            try:
                description = bedrock.describe(lineage, sql)
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

    elif effective == "ollama":
        from lineage.providers import OllamaProvider

        ollama = OllamaProvider(model=ollama_model, base_url=ollama_url)
        t0 = time.monotonic()
        description = ollama.describe(lineage, sql)
        latency_ms = int((time.monotonic() - t0) * 1000)
        bound.info("ollama_call_succeeded", latency_ms=latency_ms)

    record_run(sql, dialect, llm_used=effective != "none", latency_ms=latency_ms)

    if output == "json":
        typer.echo(render_json(lineage, sql, description))
    elif output == "openmetadata":
        typer.echo(render_openmetadata(lineage, sql))
    elif output == "mermaid":
        typer.echo(render_mermaid(lineage))
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


@app.command()
def demo() -> None:
    """Run built-in example queries to explore lineage extraction (no AWS required)."""
    from rich.console import Console
    from rich.rule import Rule

    console = Console()
    for label, sql in _DEMO_SQL:
        console.print(Rule(f"[bold cyan]{label}[/bold cyan]"))
        console.print(f"[dim]{sql}[/dim]\n")
        try:
            lineage = extract_lineage(sql)
            print_lineage(lineage, "")
        except Exception as exc:
            console.print(f"[red]Parse error:[/red] {exc}")
        console.print()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", help="Port to listen on"),
) -> None:
    """Start the FastAPI HTTP server (requires pip install '.[server]')."""
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "uvicorn is not installed. Install it with:\n"
            "  pip install 'data-lineage-cli[server]'",
            err=True,
        )
        raise typer.Exit(code=1)

    uvicorn.run("lineage.server:app", host=host, port=port, reload=False)


@app.command()
def dbt(
    sql: str = typer.Argument(..., help="dbt SQL model with Jinja2 tags to strip"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect"),
    output: str = typer.Option("text", "--output", help="Output format: text, json, openmetadata, mermaid"),
) -> None:
    """Analyze a dbt SQL model — strips {{ ref() }}, {{ source() }}, and {% %} tags before parsing."""
    from lineage.dbt import strip_jinja

    cleaned = strip_jinja(sql)
    if not cleaned:
        typer.echo("Empty SQL after stripping Jinja2 tags.", err=True)
        raise typer.Exit(code=1)

    try:
        lineage = extract_lineage(cleaned, dialect=dialect)
    except Exception as exc:
        typer.echo(f"Parse error: {exc}", err=True)
        raise typer.Exit(code=EXIT_PARSE_ERROR)

    if output == "json":
        typer.echo(render_json(lineage, cleaned))
    elif output == "openmetadata":
        typer.echo(render_openmetadata(lineage, cleaned))
    elif output == "mermaid":
        typer.echo(render_mermaid(lineage))
    else:
        print_lineage(lineage, "")


if __name__ == "__main__":
    app()
