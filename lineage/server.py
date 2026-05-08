from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from lineage.output import lineage_to_dict
from lineage.parser import extract_lineage

app = FastAPI(title="data-lineage-cli", version="0.1.0")


class AnalyzeRequest(BaseModel):
    sql: str
    dialect: str = ""
    no_llm: bool = True
    region: str = "us-east-1"


class BatchRequest(BaseModel):
    queries: list[str]
    dialect: str = ""
    no_llm: bool = True
    region: str = "us-east-1"


@app.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest) -> dict[str, object]:
    try:
        lineage = extract_lineage(req.sql, dialect=req.dialect)
    except Exception as exc:
        return {"error": str(exc), "sql": req.sql}

    description = ""
    if not req.no_llm:
        from lineage.bedrock import BedrockProvider
        description = BedrockProvider(region=req.region).describe(lineage, req.sql)

    return lineage_to_dict(lineage, req.sql, description=description)


@app.post("/batch")
def batch_endpoint(req: BatchRequest) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for sql in req.queries:
        try:
            lineage = extract_lineage(sql, dialect=req.dialect)
            description = ""
            if not req.no_llm:
                from lineage.bedrock import BedrockProvider
                description = BedrockProvider(region=req.region).describe(lineage, sql)
            results.append(lineage_to_dict(lineage, sql, description=description))
        except Exception as exc:
            results.append({"error": str(exc), "sql": sql})
    return results


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
