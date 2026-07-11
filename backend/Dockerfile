# syntax=docker/dockerfile:1
FROM python:3.12.7-slim-bookworm AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.7-slim-bookworm AS runtime

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --shell /usr/sbin/nologin --no-create-home app && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
WORKDIR /app
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
