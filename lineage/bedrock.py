from __future__ import annotations

import json

import boto3
from botocore.exceptions import NoCredentialsError, ClientError

from lineage.parser import LineageInfo

MODEL_ID = "anthropic.claude-haiku-4-5-20251001"


def describe_lineage(lineage: LineageInfo, sql: str, region: str = "us-east-1") -> str:
    prompt = _build_prompt(lineage, sql)
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )
        body = json.loads(response["body"].read())
        return body["content"][0]["text"].strip()
    except NoCredentialsError:
        raise RuntimeError(
            "Credenciais AWS não encontradas. Configure com:\n"
            "  aws configure\n"
            "ou defina as variáveis de ambiente:\n"
            "  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION"
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        raise RuntimeError(f"Erro ao chamar AWS Bedrock ({code}): {exc}") from exc


def _build_prompt(lineage: LineageInfo, sql: str) -> str:
    joins_text = (
        ", ".join(f"{j['type']} JOIN {j['table']}" for j in lineage.joins)
        if lineage.joins
        else "nenhum"
    )
    filters_text = "; ".join(lineage.filters) if lineage.filters else "nenhum"

    return (
        "Você é um especialista em governança de dados. Analise a linhagem abaixo "
        "e escreva em 2-3 frases o que esta query faz, quais dados ela consome e "
        "o que ela produz. Seja direto e técnico.\n\n"
        f"SQL original:\n{sql}\n\n"
        "Linhagem extraída:\n"
        f"- Tabelas fonte: {', '.join(lineage.source_tables) or 'nenhuma'}\n"
        f"- Tabela destino: {lineage.target_table or 'consulta direta'}\n"
        f"- Colunas lidas: {', '.join(lineage.columns_read) or 'nenhuma'}\n"
        f"- Joins: {joins_text}\n"
        f"- Filtros: {filters_text}\n"
    )
