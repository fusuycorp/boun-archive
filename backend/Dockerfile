FROM python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy files needed for dependency installation
# We copy README.md because pyproject.toml references it
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./

# Create a dummy app directory to satisfy the build system 
# during the dependency-only install phase (caching)
RUN mkdir app && touch app/__init__.py

# Install dependencies
RUN uv pip install --system --no-cache .

# Now copy the actual source code
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
