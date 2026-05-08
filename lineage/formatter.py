from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lineage.parser import LineageInfo

console = Console()


def print_lineage(lineage: LineageInfo, description: str) -> None:
    _print_structure_table(lineage)
    _print_description(description)


def _print_structure_table(lineage: LineageInfo) -> None:
    table = Table(
        title="Detected Lineage",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold white",
    )
    table.add_column("Field", style="bold", min_width=18)
    table.add_column("Value", min_width=40)

    sources = ", ".join(lineage.source_tables) if lineage.source_tables else "(none)"
    table.add_row("Sources", f"[bold blue]{sources}[/bold blue]")

    target = lineage.target_table if lineage.target_table else "(direct query)"
    table.add_row("Target", f"[bold green]{target}[/bold green]")

    cols_read = ", ".join(lineage.columns_read) if lineage.columns_read else "(none)"
    table.add_row("Columns read", cols_read)

    if lineage.columns_written:
        cols_written = ", ".join(lineage.columns_written)
        table.add_row("Columns written", cols_written)

    if lineage.joins:
        join_lines = "\n".join(
            f"{j['type']} JOIN {j['table']}" for j in lineage.joins
        )
        table.add_row("Joins", join_lines)

    if lineage.filters:
        filter_text = "\n".join(
            f"[yellow]{f}[/yellow]" for f in lineage.filters
        )
        table.add_row("Filters", filter_text)

    if lineage.column_lineage:
        edges_text = "\n".join(
            f"[dim]{e.source_table}.{e.source_col}[/dim] → [bold]{e.target_col}[/bold]"
            for e in lineage.column_lineage
        )
        table.add_row("Column lineage", edges_text)

    console.print()
    console.print(table)


def _print_description(description: str) -> None:
    if not description:
        return

    panel = Panel(
        description,
        title="[bold cyan]LLM-generated description[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def print_stats(stats: dict[str, object]) -> None:
    summary = Table(title="Usage Statistics", box=box.ROUNDED, show_lines=True, title_style="bold white")
    summary.add_column("Metric", style="bold", min_width=22)
    summary.add_column("Value", min_width=20)

    summary.add_row("Total runs", str(stats["total_runs"]))
    summary.add_row("LLM calls", f"[cyan]{stats['llm_calls']}[/cyan]")
    summary.add_row("Runs without LLM", str(stats["no_llm_runs"]))
    summary.add_row("Errors", f"[red]{stats['errors']}[/red]" if stats["errors"] else "0")

    latency = stats["avg_latency_ms"]
    summary.add_row("Avg Bedrock latency", f"{latency} ms" if latency is not None else "—")
    summary.add_row("Estimated Bedrock cost", f"[green]${stats['estimated_cost_usd']}[/green]")

    console.print()
    console.print(summary)

    recent: list[tuple[str, str, str, int, int | None]] = stats["recent"]  # type: ignore[assignment]
    if not recent:
        return

    history = Table(title="Last 10 runs", box=box.SIMPLE, title_style="bold white")
    history.add_column("Hash", style="dim", min_width=14)
    history.add_column("Dialect", min_width=10)
    history.add_column("Timestamp", min_width=26)
    history.add_column("LLM", min_width=5)
    history.add_column("Latency", min_width=10)

    for row in recent:
        h, dialect, ts, llm_used, latency_ms = row
        history.add_row(
            h,
            dialect,
            ts,
            "[cyan]yes[/cyan]" if llm_used else "no",
            f"{latency_ms} ms" if latency_ms is not None else "—",
        )

    console.print()
    console.print(history)
