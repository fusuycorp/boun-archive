FROM python:3.11-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN mkdir app && touch app/__init__.py
RUN uv pip install --system --no-cache ".[scripts]"

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy actual source code
COPY backend/app/ ./app/
COPY backend/wait_for_services.py ./
COPY backend/entrypoint.sh ./

# Copy migration scripts and data seeds
COPY scripts/ ./scripts/
COPY schedules.db ./
COPY departments.csv ./

# Create a non-root user and set permissions
RUN groupadd -r python && useradd -r -g python python && \
    chown -R python:python /app && \
    chmod +x entrypoint.sh

USER python

EXPOSE 8000

# Execute entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
