FROM python:3.12-slim AS base
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[aws,watch,server,dev]"

FROM base AS lint
RUN ruff check lineage/ main.py tests/ \
    && mypy lineage/ main.py

FROM lint AS test
RUN pytest tests/ -v

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=test /app/pyproject.toml /app/main.py ./
COPY --from=test /app/lineage ./lineage/
RUN pip install --no-cache-dir ".[aws,watch,server]"
ENTRYPOINT ["python", "main.py"]
