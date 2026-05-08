import typer
from rich.console import Console

from lineage.formatter import print_lineage
from lineage.parser import extract_lineage

app = typer.Typer(help="Data lineage CLI — parse SQL and describe it with AWS Bedrock.")
console = Console(stderr=True)

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
    try:
        lineage = extract_lineage(sql, dialect=dialect)
    except Exception as exc:
        console.print(f"[bold red]Failed to parse SQL:[/bold red] {exc}")
        raise typer.Exit(code=EXIT_PARSE_ERROR)

    description = ""
    if not no_llm:
        from lineage.bedrock import BedrockError, CredentialsError, describe_lineage
        try:
            description = describe_lineage(lineage, sql, region=region)
        except CredentialsError as exc:
            console.print(f"[bold red]Credentials error:[/bold red] {exc}")
            raise typer.Exit(code=EXIT_CREDENTIALS_ERROR)
        except BedrockError as exc:
            console.print(f"[bold red]Bedrock error:[/bold red] {exc}")
            raise typer.Exit(code=EXIT_BEDROCK_ERROR)

    print_lineage(lineage, description)


if __name__ == "__main__":
    app()
