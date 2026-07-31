# Deployment Documentation

This document outlines the architecture and deployment strategy for the BOUN-ARCHIVE application on Docker Swarm/Dokploy.

## Infrastructure Overview
- **Orchestration**: Docker Swarm (via Dokploy Stacks).
- **Nodes**:
  - `tanri`: Handles public-facing services (Nginx, Frontend).
  - `worky`: Handles data-intensive services (Backend, PostgreSQL, Redis, Meilisearch).
- **Hardware Profile**: 8 CPU / 16GB RAM per node.

## Scaling for High Concurrency (10k Users)
The system is configured to handle up to 10,000 concurrent users using the following strategy:

### Service Replicas
- **Backend**: 4 replicas (Python/FastAPI; `WEB_CONCURRENCY=4` is passed to Uvicorn workers by the entrypoint).
- **Frontend**: 3 replicas (SvelteKit).
- **Nginx**: 2 replicas (High Availability).
- **Database/Search**: Single instances (1 replica) with high resource reservations.

### Resource Allocation
- **PostgreSQL**: 4GB Limit / 2GB Reservation. Optimized with `shared_buffers` and `effective_cache_size`.
- **Meilisearch**: 6GB Limit / 2GB Reservation.
- **Backend**: 2GB Limit / 1GB Reservation.
- **Frontend**: 1GB Limit / 512MB Reservation.

## Routing Logic (Nginx)
The system uses a single entry point (Nginx) on port 3000 (mapped to 80/443 externally).

- **Frontend**: Requests to `/` are proxied to the SvelteKit upstream.
- **API**: Requests to `/api/` are stripped of the `/api` prefix using an Nginx `rewrite` and forwarded to the backend. This preserves the full path (e.g., `/v1/search`).
  - *Example*: `bountools.com/api/v1/terms` -> `backend:8000/v1/terms`.
- **Performance**: Nginx is tuned with `worker_connections 20000` and uses runtime DNS resolution via `resolver 127.0.0.11` to prevent startup crashes if upstreams are not yet healthy.

## Key Stability Fixes
1. **Meilisearch Pathing**: Always use the default `/data.ms` internal path for the database volume to avoid version inference errors.
2. **Config Versioning**: Docker Swarm `configs` are immutable. The current stable version is **`nginx_config_v3`**. When updating `nginx.conf`, increment the version name in `docker-stack.yml`.
3. **Wait for Services**: The backend includes a `wait_for_services.py` script that ensures PostgreSQL, Redis, and Meilisearch are healthy before starting the application. It uses a **Redis-based Distributed Lock** to coordinate initialization across multiple replicas.

## GitHub Actions Deployment (Custom Registry Redeploys)
Programmatic redeployment on Dokploy after pushing container builds to a custom registry is triggered via Dokploy's **Compose REST API** (`POST /api/compose.redeploy`).

### Prerequisites
1. Create a Dokploy API key in **Settings > Profile > API/CLI**.
2. Configure credentials as Repository Secrets in GitHub:
   * `DOKPLOY_API_KEY`: Your generated API key (Required).
   * `DOKPLOY_URL`: Dokploy instance URL (defaults to `https://dokploy.bogazici.app`).
   * `DOKPLOY_COMPOSE_ID`: Unique compose stack ID (defaults to `FnoW3VW_TLpX8sXKPL60v`).

The `.github/workflows/deploy.yml` workflow calls `POST /api/compose.redeploy` passing `composeId`, using `curl -f -s -S` to fail fast on HTTP errors.


## Troubleshooting
- **502 Bad Gateway**: Usually means the Backend is down or still starting. Check backend logs for `wait_for_services.py` status.
- **404 Not Found on API**: Check `nginx.conf` for trailing slashes in `proxy_pass`.
- **Meilisearch Crash**: Check if `MEILI_MASTER_KEY` is at least 16 bytes and ensure the memory limit is at least 2GB.
