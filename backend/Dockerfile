FROM python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv pip install --system --no-cache -e .

# Copy backend source modules and scripts
COPY backend/app/ ./app/
COPY backend/wait_for_services.py ./
COPY backend/entrypoint.sh ./

# Copy migration scripts and data seeds
COPY scripts/ ./scripts/
COPY schedules.db ./
COPY departments.csv ./

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Execute entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
