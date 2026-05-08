from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from lineage.parser import LineageInfo

console = Console()


def print_lineage(lineage: LineageInfo, description: str) -> None:
    _print_structure_table(lineage)
    _print_description(description)


def _print_structure_table(lineage: LineageInfo) -> None:
    table = Table(
        title="Linhagem detectada",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold white",
    )
    table.add_column("Campo", style="bold", min_width=18)
    table.add_column("Valor", min_width=40)

    sources = ", ".join(lineage.source_tables) if lineage.source_tables else "(nenhuma)"
    table.add_row("Fontes", f"[bold blue]{sources}[/bold blue]")

    target = lineage.target_table if lineage.target_table else "(consulta direta)"
    table.add_row("Destino", f"[bold green]{target}[/bold green]")

    cols_read = ", ".join(lineage.columns_read) if lineage.columns_read else "(nenhuma)"
    table.add_row("Colunas lidas", cols_read)

    if lineage.columns_written:
        cols_written = ", ".join(lineage.columns_written)
        table.add_row("Colunas escritas", cols_written)

    if lineage.joins:
        join_lines = "\n".join(
            f"{j['type']} JOIN {j['table']}" for j in lineage.joins
        )
        table.add_row("Joins", join_lines)

    if lineage.filters:
        filter_text = "\n".join(
            f"[yellow]{f}[/yellow]" for f in lineage.filters
        )
        table.add_row("Filtros", filter_text)

    console.print()
    console.print(table)


def _print_description(description: str) -> None:
    if not description:
        return

    panel = Panel(
        description,
        title="[bold cyan]Descrição gerada pelo LLM[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
