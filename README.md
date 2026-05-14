# data-lineage-cli

[![CI](https://github.com/jutamagno/data-lineage-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/jutamagno/data-lineage-cli/actions/workflows/ci.yml)

A command-line tool that parses SQL queries, extracts data lineage (tables, columns, joins, filters, column-level mappings), and uses an LLM (AWS Bedrock or local Ollama) to generate plain-English descriptions.

Built for data engineering and governance teams who need to document and audit SQL pipelines without manual effort.

---

## Features

- **SQL parsing** — extracts source tables, target tables, columns read/written, joins, filters, CTEs, UNION branches, and subqueries
- **Column-level lineage** — traces `source_table.source_col → target_col` mappings using `sqlglot.lineage`
- **LLM descriptions** — calls Claude Haiku via AWS Bedrock, or any local model via Ollama
- **Description cache** — SQLite cache (`~/.lineage-cli/cache.db`) avoids redundant LLM calls
- **Run history** — records every execution in `~/.lineage-cli/history.db`; view with the `stats` command
- **Batch mode** — analyze all queries in a `.sql` file, output a JSON array
- **File watcher** — `--watch` re-analyzes a `.sql` file on every save
- **Structured logging** — JSON logs in pipelines, colored output in the terminal
- **Multiple output formats** — `text` (Rich table), `json`, `openmetadata`, `mermaid`
- **FastAPI HTTP server** — expose `/analyze` and `/batch` endpoints over HTTP
- **dbt support** — strip `{{ ref() }}`, `{{ source() }}`, and `{% %}` tags before parsing
- **Demo command** — run six built-in example queries with no AWS required

---

## Installation

### With Docker (recommended)

The Dockerfile enforces a `lint → test → runtime` gate: ruff, mypy, and pytest must all pass before the runtime image is built.

```bash
git clone https://github.com/jutamagno/data-lineage-cli.git
cd data-lineage-cli
docker build -t lineage-cli .
```

### With pip / uv

```bash
pip install ".[aws]"                      # core + AWS Bedrock
pip install ".[aws,watch]"                # + file watcher (watchdog)
pip install ".[aws,watch,server]"         # + FastAPI HTTP server
pip install ".[aws,watch,server,dev]"     # + dev tools (pytest, mypy, ruff, hypothesis)
```

---

## AWS configuration

Required only for LLM descriptions via Bedrock. Skip with `--no-llm` or `--provider none` during development, or use Ollama for fully local operation.

```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

Model: `anthropic.claude-haiku-4-5-20251001` via AWS Bedrock. Enable model access in the Bedrock console for your account.

---

## Ollama (local LLM, no AWS)

Run any model locally with [Ollama](https://ollama.com):

```bash
ollama pull llama3.2
python main.py analyze "SELECT region, sum(amount) FROM sales GROUP BY region" \
  --provider ollama --ollama-model llama3.2
```

Options: `--ollama-model` (default `llama3.2`) and `--ollama-url` (default `http://localhost:11434`).

---

## Commands

### `demo` — explore lineage extraction without AWS

```bash
python main.py demo
```

Runs six built-in example queries (JOIN, aggregate, CTE, INSERT, UNION, CREATE TABLE AS) and prints the parsed lineage for each. No AWS credentials required.

---

### `analyze` — parse and describe a single query

```
python main.py analyze "SQL" [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--no-llm` | off | Skip the LLM call |
| `--provider` | `""` | LLM provider: `bedrock`, `ollama`, `none` |
| `--ollama-model` | `llama3.2` | Ollama model name |
| `--ollama-url` | `http://localhost:11434` | Ollama base URL |
| `--no-cache` | off | Force a fresh LLM call even if cached |
| `--dialect` | `""` | SQL dialect: `bigquery`, `spark`, etc. |
| `--region` | `us-east-1` | AWS region for Bedrock |
| `--output` | `text` | Output format: `text`, `json`, `openmetadata`, `mermaid` |

**Examples:**

```bash
# Rich table output (no LLM)
python main.py analyze "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id" --no-llm

# Local LLM via Ollama
python main.py analyze "SELECT region, sum(amount) FROM sales GROUP BY region" --provider ollama

# With AWS Bedrock
python main.py analyze "SELECT region, sum(amount) FROM sales GROUP BY region"

# JSON output
python main.py analyze "SELECT t.amount AS total FROM transactions t" --no-llm --output json

# Mermaid graph
python main.py analyze "INSERT INTO summary SELECT region, sum(amount) FROM sales GROUP BY region" \
  --no-llm --output mermaid

# OpenMetadata-compatible column lineage payload
python main.py analyze "INSERT INTO summary SELECT region, sum(amount) FROM sales GROUP BY region" \
  --no-llm --output openmetadata

# BigQuery dialect
python main.py analyze "SELECT user_id FROM \`project.dataset.orders\`" --dialect bigquery --no-llm
```

**With Docker:**
```bash
docker run --rm lineage-cli analyze "SELECT name FROM users WHERE active = true" --no-llm
docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
  lineage-cli analyze "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
```

---

### `batch` — analyze all queries in a `.sql` file

```
python main.py batch FILE [OPTIONS]
```

Splits the file on `;`, runs `analyze` on each query, and outputs a JSON array. Parse errors per query are captured as `{"sql": ..., "error": ...}` without aborting the batch.

| Option | Default | Description |
|---|---|---|
| `--no-llm` | off | Skip Bedrock for all queries |
| `--no-cache` | off | Force fresh calls |
| `--dialect` | `""` | SQL dialect |
| `--region` | `us-east-1` | AWS region |
| `--watch` | off | Re-analyze on file save (requires `pip install ".[watch]"`) |

```bash
python main.py batch queries.sql --no-llm
python main.py batch queries.sql --watch   # stays running, reprints on save
```

---

### `dbt` — analyze a dbt SQL model

```
python main.py dbt "SQL" [OPTIONS]
```

Strips `{{ ref('...') }}`, `{{ source('...', '...') }}`, and `{% ... %}` Jinja2 tags before parsing. The cleaned SQL is then analyzed as a normal query.

```bash
python main.py dbt "SELECT o.id FROM {{ ref('orders') }} o JOIN {{ source('crm', 'customers') }} c ON o.customer_id = c.id" --no-llm

python main.py dbt "SELECT id FROM {{ ref('users') }}" --output mermaid
```

---

### `serve` — start the HTTP server

```
python main.py serve [--host HOST] [--port PORT]
```

Starts a FastAPI server. Requires `pip install ".[server]"`.

```bash
python main.py serve --port 8000
```

See [HTTP API](#http-api) below.

---

### `stats` — show usage statistics

```
python main.py stats
```

Displays total runs, LLM calls, cache hits, average Bedrock latency, estimated cost, and the last 10 runs from `~/.lineage-cli/history.db`.

---

## HTTP API

Start the server: `python main.py serve`

### `POST /analyze`

```json
{
  "sql": "SELECT id FROM users",
  "dialect": "",
  "no_llm": true,
  "region": "us-east-1"
}
```

Returns the same JSON structure as `--output json`.

### `POST /batch`

```json
{
  "queries": ["SELECT id FROM users", "SELECT name FROM orders"],
  "no_llm": true
}
```

Returns a JSON array of lineage results.

### `GET /health`

```json
{"status": "ok"}
```

---

## Output formats

### `--output text` (default)

```
╭────────────────────┬──────────────────────────────────────────╮
│ Field              │ Value                                    │
├────────────────────┼──────────────────────────────────────────┤
│ Sources            │ users, orders                            │
├────────────────────┼──────────────────────────────────────────┤
│ Target             │ (direct query)                           │
├────────────────────┼──────────────────────────────────────────┤
│ Columns read       │ name, total, id, user_id, status         │
├────────────────────┼──────────────────────────────────────────┤
│ Joins              │ INNER JOIN orders                        │
├────────────────────┼──────────────────────────────────────────┤
│ Filters            │ o.status = 'paid'                        │
├────────────────────┼──────────────────────────────────────────┤
│ Column lineage     │ users.id → id                            │
│                    │ orders.total → total                     │
╰────────────────────┴──────────────────────────────────────────╯
```

### `--output json`

```json
{
  "source_tables": ["users", "orders"],
  "target_table": null,
  "columns_read": ["name", "total"],
  "columns_written": [],
  "joins": [{"type": "INNER", "table": "orders"}],
  "filters": ["o.status = 'paid'"],
  "column_lineage": [
    {"source_table": "users", "source_col": "id", "target_col": "id"},
    {"source_table": "orders", "source_col": "total", "target_col": "total"}
  ],
  "sql": "SELECT ...",
  "description": "This query joins..."
}
```

### `--output mermaid`

Emits a Mermaid `graph LR` diagram. If column-level lineage is available, shows column edges; otherwise shows table-level edges.

```
graph LR
  transactions_amount["transactions.amount"] --> summary_total["summary.total"]
```

Paste into any Mermaid renderer (GitHub markdown, Notion, mermaid.live) to visualize the pipeline.

### `--output openmetadata`

Emits an OpenMetadata-compatible `columnsLineage` payload grouped by source table:

```json
[
  {
    "fromTable": "transactions",
    "toTable": "summary",
    "lineageDetails": {
      "sql": "INSERT INTO summary SELECT ...",
      "columnsLineage": [
        {"fromColumns": ["transactions.amount"], "toColumn": "total"}
      ]
    }
  }
]
```

---

## Parser capabilities

| SQL construct | Supported |
|---|---|
| `SELECT` with aliases, expressions, `*` | Yes |
| `INSERT INTO ... SELECT` | Yes |
| `CREATE TABLE ... AS SELECT` | Yes |
| `JOIN` (INNER, LEFT, RIGHT, FULL, CROSS) | Yes |
| `WHERE` with multiple `AND` conditions | Yes |
| CTEs (`WITH x AS (...)`) | Yes |
| `UNION` / `UNION ALL` | Yes |
| Subqueries in `FROM` | Yes |
| BigQuery, Spark dialects | Yes |
| Column-level lineage | Best-effort via `sqlglot.lineage` |
| dbt Jinja2 (`ref`, `source`, block tags) | Yes (via `dbt` command) |

---

## Architecture

```
CLI (main.py / Typer)
        │
        ├── analyze ──▶ parser.py ──▶ LineageInfo + ColumnEdge[]
        │                   │               │
        │               sqlglot AST    sqlglot.lineage
        │                   │
        │            bedrock.py ──▶ AWS Bedrock (Claude Haiku)
        │            providers.py ──▶ OllamaProvider / MockProvider
        │            cache.py   ──▶ ~/.lineage-cli/cache.db
        │            history.py ──▶ ~/.lineage-cli/history.db
        │            formatter.py ──▶ Rich terminal output
        │            output.py ──▶ JSON / OpenMetadata / Mermaid
        │
        ├── batch ──▶ batch.py ──▶ split_sql → [analyze each]
        │                │
        │            watchdog (optional, --watch)
        │
        ├── dbt ──▶ dbt.py ──▶ strip_jinja → analyze
        │
        ├── serve ──▶ server.py ──▶ FastAPI (/analyze, /batch, /health)
        │
        └── stats ──▶ history.py ──▶ formatter.py
```

**Key modules:**

| File | Responsibility |
|---|---|
| `lineage/parser.py` | AST traversal, `LineageInfo`, `ColumnEdge`, column lineage extraction |
| `lineage/bedrock.py` | AWS Bedrock client (`BedrockProvider`) |
| `lineage/providers.py` | `LLMProvider` protocol, `MockProvider`, `OllamaProvider` |
| `lineage/prompts.py` | Versioned prompt builder (`build_prompt(lineage, sql, version="v1")`) |
| `lineage/cache.py` | SQLite description cache |
| `lineage/history.py` | SQLite run history and stats |
| `lineage/batch.py` | Multi-query file analysis |
| `lineage/dbt.py` | Jinja2 tag stripper for dbt models |
| `lineage/server.py` | FastAPI app — `/analyze`, `/batch`, `/health` |
| `lineage/output.py` | JSON, OpenMetadata, and Mermaid serialization |
| `lineage/formatter.py` | Rich table and panel rendering |
| `lineage/log.py` | structlog — JSON in CI, colored in TTY |

---

## Tests

```bash
# Docker (lint + typecheck + tests run automatically at build time)
docker build -t lineage-cli .

# Local
pytest tests/ -v
```

**112 tests** covering:

- SQL parsing: SELECT, INSERT, CREATE, JOIN, WHERE, CTEs, UNION, subqueries, BigQuery dialect
- Column-level lineage: `ColumnEdge` extraction and graceful fallback
- LLM providers: `MockProvider`, `OllamaProvider` (mocked urllib), protocol compliance
- Prompt building: version selection, content assertions
- Cache: SQLite key isolation, overwrite, miss
- History: recording, stats aggregation, cost estimation
- Formatter: Rich table fields, column lineage display, LLM panel
- Output: JSON serialization, OpenMetadata format, Mermaid graph
- Batch: SQL splitting, error isolation per query
- dbt: Jinja2 tag stripping (`ref`, `source`, block tags)
- Server: FastAPI `/analyze`, `/batch`, `/health` endpoints via TestClient
- Property-based (Hypothesis): 300 generated queries, parser never raises

---

## Technical decisions

| Decision | Reason |
|---|---|
| **sqlglot** for parsing | Full AST — handles CTEs, UNION, subqueries, and 20+ dialects reliably |
| **`sqlglot.lineage`** for column lineage | Official API, traces column provenance through aliases and aggregates |
| **Claude Haiku via Bedrock** | Best cost-to-quality for short descriptions; data stays within AWS |
| **OllamaProvider via stdlib urllib** | No extra dependencies — works offline with any Ollama model |
| **SQLite for cache and history** | Zero infrastructure, portable, sufficient for local use |
| **`LLMProvider` protocol** | Enables `MockProvider` and `OllamaProvider` in tests without AWS credentials |
| **Versioned prompts** | `build_prompt(lineage, sql, version="v1")` — prompts can be improved without breaking callers |
| **structlog** | JSON in CI/pipelines, colored in terminal — same code, no branches |
| **Hypothesis** for property tests | Catches parser regressions across random SQL shapes, not just fixed examples |
| **Multi-stage Dockerfile** | `lint → test → runtime` — build fails if ruff, mypy, or pytest fail |
| **FastAPI + Pydantic** | Typed request/response models, automatic OpenAPI docs at `/docs` |
| **dbt Jinja2 stripper** | Regex-based, no Jinja2 dependency — handles `ref`, `source`, and block tags |
| **Optional deps `[aws]`, `[watch]`, `[server]`** | Core package has no cloud or OS dependencies; heavy deps are opt-in |
