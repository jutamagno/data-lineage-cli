# data-lineage-cli

A command-line tool that parses SQL queries, automatically extracts data lineage (tables, columns, joins, filters), and uses AWS Bedrock to generate a plain-English description of what the query does.

Built for data governance and data engineering teams who need to document and audit SQL pipelines without manual effort.

---

## Why it matters

Data governance is a growing requirement for organizations handling sensitive or regulated data. Manually mapping the lineage of hundreds of SQL queries is not feasible — this tool automates that extraction and uses LLMs to produce human-readable descriptions, making cataloging, auditing, and documentation significantly easier.

---

## Installation

### Prerequisites
- Docker (recommended)
- or Python 3.12+ with a virtual environment

### With Docker (recommended)

```bash
git clone https://github.com/<your-username>/data-lineage-cli.git
cd data-lineage-cli
docker build -t lineage-cli .
```

### With a virtual environment

```bash
git clone https://github.com/<your-username>/data-lineage-cli.git
cd data-lineage-cli
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## AWS configuration

To use the Bedrock LLM description feature, configure your AWS credentials:

```bash
aws configure
```

Or export the environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

The model used is `anthropic.claude-haiku-4-5-20251001` via AWS Bedrock. Make sure model access is enabled in the Bedrock console for your account.

---

## Usage

### Syntax

```bash
# Docker
docker run --rm lineage-cli "SQL" [--no-llm] [--dialect DIALECT] [--region REGION]

# Local (with venv active)
python main.py "SQL" [--no-llm] [--dialect DIALECT] [--region REGION]
```

### Examples

**Simple SELECT with filter:**
```bash
docker run --rm lineage-cli "SELECT name, email FROM users WHERE active = true" --no-llm
```

**JOIN with LLM description:**
```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION \
  lineage-cli "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'paid'"
```

**INSERT INTO with SELECT:**
```bash
docker run --rm lineage-cli \
  "INSERT INTO summary SELECT region, sum(amount) FROM sales GROUP BY region" \
  --no-llm
```

**BigQuery dialect:**
```bash
docker run --rm lineage-cli \
  "SELECT user_id FROM \`project.dataset.orders\` WHERE status = 'paid'" \
  --dialect bigquery --no-llm
```

### Expected output

```
Detected Lineage
╭────────────────────┬────────────────────────────────────────╮
│ Field              │ Value                                  │
├────────────────────┼────────────────────────────────────────┤
│ Sources            │ users, orders                          │
├────────────────────┼────────────────────────────────────────┤
│ Target             │ (direct query)                         │
├────────────────────┼────────────────────────────────────────┤
│ Columns read       │ name, total, id, user_id, status       │
├────────────────────┼────────────────────────────────────────┤
│ Joins              │ INNER JOIN orders                      │
├────────────────────┼────────────────────────────────────────┤
│ Filters            │ o.status = 'paid'                      │
╰────────────────────┴────────────────────────────────────────╯

╭─ LLM-generated description ────────────────────────────────╮
│                                                             │
│  This query joins customer data (users) with their paid     │
│  orders (orders), returning the customer name and order     │
│  total. The join is on user id, filtered to orders with     │
│  status 'paid'.                                             │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
```

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  SQL input  │────▶│   sqlglot    │────▶│  AWS Bedrock    │────▶│ Rich output  │
│  (CLI arg)  │     │  (parser.py) │     │  (bedrock.py)   │     │(formatter.py)│
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                          │                       │
                    LineageInfo            plain-English
                    (structured)           description
```

**Flow:**
1. The SQL query is received as a positional argument via Typer
2. `parser.py` uses sqlglot to build the AST and extract a `LineageInfo` object
3. `bedrock.py` builds a structured prompt and calls Claude Haiku via boto3
4. `formatter.py` renders a table and panel in the terminal using Rich

---

## Tests

```bash
# Docker
docker run --rm --entrypoint pytest lineage-cli tests/ -v

# Local (with venv active)
pytest tests/ -v
```

Test coverage: simple SELECT, INNER JOIN, LEFT JOIN with multiple filters, INSERT INTO, CREATE TABLE AS SELECT, BigQuery dialect, and explicit column list in INSERT.

---

## Technical decisions

| Decision | Reason |
|---|---|
| **sqlglot** over regex | Regex breaks on complex queries (subqueries, aliases, CTEs). sqlglot produces a full AST and supports multiple dialects reliably. |
| **Claude Haiku** via Bedrock | Best cost-to-quality ratio for short descriptions (2-3 sentences). Bedrock keeps data within AWS infrastructure, important for compliance-restricted environments. |
| **Typer** over argparse | Cleaner declarative API, auto-formatted help output, and native support for boolean flags like `--no-llm`. |
| **Rich** for output | Colored tables and panels improve lineage readability without heavy dependencies. |
| **`--no-llm` flag** | Allows using the parser and formatter without any AWS credentials — useful for CI and local development. |

---

## Project structure

```
data-lineage-cli/
├── lineage/
│   ├── __init__.py
│   ├── parser.py        # extracts tables, columns, joins, filters via sqlglot
│   ├── bedrock.py       # AWS Bedrock client, calls Claude Haiku
│   └── formatter.py     # formats colored output in the terminal with Rich
├── tests/
│   ├── __init__.py
│   └── test_parser.py
├── main.py              # Typer entrypoint
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Next steps

- Support for sequential multi-query analysis to detect lineage across pipeline steps
- JSON export for ingestion into data catalogs like OpenMetadata or DataHub
- `--watch` mode that monitors a `.sql` file and re-analyzes on save
- Description caching to avoid re-calling Bedrock for queries already seen
- CTE support (`WITH ... AS (...)`) in the parser
