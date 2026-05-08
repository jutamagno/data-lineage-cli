import typer
from rich.console import Console

from lineage.parser import extract_lineage
from lineage.formatter import print_lineage

app = typer.Typer(help="Ferramenta de linhagem de dados com LLM via AWS Bedrock.")
console = Console(stderr=True)


@app.command()
def analyze(
    sql: str = typer.Argument(..., help="Query SQL para analisar"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Pula chamada ao Bedrock"),
    dialect: str = typer.Option("", "--dialect", help="Dialeto SQL: '' (padrão), bigquery, spark"),
    region: str = typer.Option("us-east-1", "--region", help="Região AWS para o Bedrock"),
):
    try:
        lineage = extract_lineage(sql, dialect=dialect)
    except Exception as exc:
        console.print(f"[bold red]Erro ao analisar SQL:[/bold red] {exc}")
        raise typer.Exit(code=1)

    description = ""
    if not no_llm:
        try:
            from lineage.bedrock import describe_lineage
            description = describe_lineage(lineage, sql, region=region)
        except RuntimeError as exc:
            console.print(f"[bold yellow]Aviso:[/bold yellow] {exc}")

    print_lineage(lineage, description)


if __name__ == "__main__":
    app()
