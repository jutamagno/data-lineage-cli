# data-lineage-cli

Uma ferramenta de linha de comando que analisa queries SQL, extrai automaticamente a linhagem de dados (tabelas, colunas, joins, filtros) e usa AWS Bedrock para gerar uma descrição em linguagem natural.

Útil para equipes de governança e engenharia de dados que precisam documentar e auditar pipelines SQL sem esforço manual.

---

## Por que é relevante

A governança de dados é um requisito crescente em organizações que lidam com dados sensíveis ou regulados. Mapear manualmente a linhagem de centenas de queries SQL é inviável — esta ferramenta automatiza essa extração e usa LLMs para produzir descrições legíveis por humanos, facilitando catalogação, auditoria e documentação.

---

## Instalação

### Pré-requisitos
- Docker (recomendado)
- ou Python 3.12+ com virtualenv

### Com Docker (recomendado)

```bash
git clone https://github.com/<seu-usuario>/data-lineage-cli.git
cd data-lineage-cli
docker build -t lineage-cli .
```

### Com virtualenv

```bash
git clone https://github.com/<seu-usuario>/data-lineage-cli.git
cd data-lineage-cli
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuração AWS

Para usar a geração de descrição via Bedrock, configure suas credenciais AWS:

```bash
aws configure
```

Ou exporte as variáveis de ambiente:

```bash
export AWS_ACCESS_KEY_ID=sua_key
export AWS_SECRET_ACCESS_KEY=sua_secret
export AWS_DEFAULT_REGION=us-east-1
```

O modelo usado é `anthropic.claude-haiku-4-5-20251001` via AWS Bedrock. Certifique-se de que o acesso ao modelo está habilitado no console do Bedrock na sua conta.

---

## Uso

### Sintaxe

```bash
# Docker
docker run --rm lineage-cli "SQL" [--no-llm] [--dialect DIALETO] [--region REGIAO]

# Local (com venv ativo)
python main.py "SQL" [--no-llm] [--dialect DIALETO] [--region REGIAO]
```

### Exemplos

**SELECT simples com filtro:**
```bash
docker run --rm lineage-cli "SELECT name, email FROM users WHERE active = true" --no-llm
```

**JOIN entre tabelas com descrição do LLM:**
```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION \
  lineage-cli "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'paid'"
```

**INSERT INTO com SELECT:**
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

### Saída esperada

```
Linhagem detectada
╭────────────────────┬────────────────────────────────────────╮
│ Campo              │ Valor                                  │
├────────────────────┼────────────────────────────────────────┤
│ Fontes             │ users, orders                          │
├────────────────────┼────────────────────────────────────────┤
│ Destino            │ (consulta direta)                      │
├────────────────────┼────────────────────────────────────────┤
│ Colunas lidas      │ name, total, id, user_id, status       │
├────────────────────┼────────────────────────────────────────┤
│ Joins              │ INNER JOIN orders                      │
├────────────────────┼────────────────────────────────────────┤
│ Filtros            │ o.status = 'paid'                      │
╰────────────────────┴────────────────────────────────────────╯

╭─ Descrição gerada pelo LLM ────────────────────────────────╮
│                                                             │
│  Esta query combina dados de clientes (users) com seus      │
│  pedidos pagos (orders), retornando nome do cliente e       │
│  valor total. A junção é feita pelo id do usuário,          │
│  filtrando apenas pedidos com status 'paid'.                │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
```

---

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  SQL input  │────▶│   sqlglot    │────▶│  AWS Bedrock    │────▶│ Rich output  │
│  (CLI arg)  │     │  (parser.py) │     │  (bedrock.py)   │     │(formatter.py)│
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                          │                       │
                    LineageInfo             descrição em
                    (estruturado)           linguagem natural
```

**Fluxo:**
1. A query SQL é recebida como argumento posicional via Typer
2. `parser.py` usa sqlglot para construir a AST e extrair `LineageInfo`
3. `bedrock.py` monta um prompt estruturado e chama Claude Haiku via boto3
4. `formatter.py` renderiza tabela e painel no terminal com Rich

---

## Testes

```bash
# Docker
docker run --rm --entrypoint pytest lineage-cli tests/ -v

# Local (com venv ativo)
pytest tests/ -v
```

Os testes cobrem: SELECT simples, INNER JOIN, LEFT JOIN com múltiplos filtros, INSERT INTO, CREATE TABLE AS SELECT, dialeto BigQuery e extração de colunas escritas.

---

## Decisões técnicas

| Decisão | Motivo |
|---|---|
| **sqlglot** em vez de regex | Regex quebra em queries complexas (subqueries, aliases, CTEs). sqlglot produz uma AST completa e suporta múltiplos dialetos de forma confiável. |
| **Claude Haiku** via Bedrock | Haiku tem o melhor custo-benefício para descrições curtas (2-3 frases). Bedrock mantém os dados dentro da infra AWS, importante para ambientes com restrições de compliance. |
| **Typer** em vez de argparse | API declarativa mais limpa, help automático formatado, e suporte nativo a flags booleanas como `--no-llm`. |
| **Rich** para output | Terminal com cores e tabelas melhora a leitura da linhagem sem adicionar dependências pesadas. |
| **--no-llm flag** | Permite usar o parser e o formatter sem nenhuma dependência de credenciais AWS, útil para CI e desenvolvimento local. |

---

## Estrutura do projeto

```
data-lineage-cli/
├── lineage/
│   ├── __init__.py
│   ├── parser.py        # extrai tabelas, colunas, joins, filtros via sqlglot
│   ├── bedrock.py       # cliente AWS Bedrock, chama Claude Haiku
│   └── formatter.py     # formata saída colorida no terminal com Rich
├── tests/
│   ├── __init__.py
│   └── test_parser.py
├── main.py              # entrypoint Typer
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Próximos passos

- Suporte a múltiplas queries em sequência para detectar linhagem entre steps de um pipeline
- Exportar resultado em JSON para ingestão em catálogos como OpenMetadata ou DataHub
- Modo `--watch` que monitora um arquivo `.sql` e reanalisa ao salvar
- Cache de descrições para não rechamar o Bedrock para queries já vistas
- Suporte a CTEs (`WITH ... AS (...)`) no parser
