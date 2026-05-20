FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compilation and database support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements configuration
COPY backend/pyproject.toml ./

# Install python dependencies
RUN pip install --no-cache-dir .

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
