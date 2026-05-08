import typer
from rich.console import Console

from lineage.parser import extract_lineage
from lineage.formatter import print_lineage

app = typer.Typer(help="Data lineage CLI — parse SQL and describe it with AWS Bedrock.")
console = Console(stderr=True)


@app.command()
def analyze(
    sql: str = typer.Argument(..., help="SQL query to analyze"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the Bedrock LLM call"),
    dialect: str = typer.Option("", "--dialect", help="SQL dialect: '' (default), bigquery, spark"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region for Bedrock"),
):
    try:
        lineage = extract_lineage(sql, dialect=dialect)
    except Exception as exc:
        console.print(f"[bold red]Failed to parse SQL:[/bold red] {exc}")
        raise typer.Exit(code=1)

    description = ""
    if not no_llm:
        try:
            from lineage.bedrock import describe_lineage
            description = describe_lineage(lineage, sql, region=region)
        except RuntimeError as exc:
            console.print(f"[bold yellow]Warning:[/bold yellow] {exc}")

    print_lineage(lineage, description)


if __name__ == "__main__":
    app()
