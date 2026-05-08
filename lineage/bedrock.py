from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from lineage.parser import LineageInfo
from lineage.prompts import build_prompt

MODEL_ID = "anthropic.claude-haiku-4-5-20251001"


class CredentialsError(RuntimeError):
    pass


class BedrockError(RuntimeError):
    pass


class BedrockProvider:
    def __init__(self, region: str = "us-east-1", prompt_version: str = "v1") -> None:
        self.region = region
        self.prompt_version = prompt_version

    def describe(self, lineage: LineageInfo, sql: str) -> str:
        prompt = build_prompt(lineage, sql, version=self.prompt_version)
        try:
            client = boto3.client("bedrock-runtime", region_name=self.region)
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
