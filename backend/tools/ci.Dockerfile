# trunk-ignore-all(trivy/DS-0002,checkov/CKV_DOCKER_3): Disposable fixtures need root to read the private manifest and write owned volumes.
FROM ghcr.io/astral-sh/uv:0.11.2 AS uv
FROM python:3.13-bookworm
COPY --from=uv /uv /usr/local/bin/uv
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libmariadb-dev libpq-dev libmagic1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra test --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
HEALTHCHECK CMD python --version || exit 1
