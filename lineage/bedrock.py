from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from lineage.parser import LineageInfo

MODEL_ID = "anthropic.claude-haiku-4-5-20251001"


class CredentialsError(RuntimeError):
    pass


class BedrockError(RuntimeError):
    pass


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
        return str(body["content"][0]["text"]).strip()
    except NoCredentialsError:
        raise CredentialsError(
            "AWS credentials not found. Configure them with:\n"
            "  aws configure\n"
            "or set the environment variables:\n"
            "  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION"
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        raise BedrockError(f"AWS Bedrock error ({code}): {exc}") from exc


def _build_prompt(lineage: LineageInfo, sql: str) -> str:
    joins_text = (
        ", ".join(f"{j['type']} JOIN {j['table']}" for j in lineage.joins)
        if lineage.joins
        else "none"
    )
    filters_text = "; ".join(lineage.filters) if lineage.filters else "none"

    return (
        "You are a data governance expert. Analyze the lineage below and write "
        "2-3 sentences describing what this query does, what data it consumes, "
        "and what it produces. Be concise and technical.\n\n"
        f"Original SQL:\n{sql}\n\n"
        "Extracted lineage:\n"
        f"- Source tables: {', '.join(lineage.source_tables) or 'none'}\n"
        f"- Target table: {lineage.target_table or 'direct query'}\n"
        f"- Columns read: {', '.join(lineage.columns_read) or 'none'}\n"
        f"- Joins: {joins_text}\n"
        f"- Filters: {filters_text}\n"
    )
