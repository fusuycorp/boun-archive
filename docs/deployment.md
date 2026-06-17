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
- **Backend**: 4 replicas (Python/FastAPI with `WEB_CONCURRENCY=4`).
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

## GitHub Actions Deployment (Custom Registry Redepolys)
Standard auto-deploy webhooks provided by Dokploy check for provider-specific headers (like `X-Hub-Signature-256` for GitHub) to verify request authenticity. Triggering these manually via generic `curl` calls inside CI/CD scripts will fail due to signature mismatch.

To trigger deployments programmatically after pushing a container to a custom repository, use Dokploy's REST API:

1. Create a Dokploy API key in **Settings > Profile > API/CLI**.
2. Save credentials as Secrets in your GitHub repo:
   * `DOKPLOY_API_KEY`: Your generated API key.
   * `DOKPLOY_URL`: Your Dokploy instance address (e.g. `https://dokploy.bountools.com`).
   * `DOKPLOY_APPLICATION_ID`: The application's unique ID.
3. In your `.github/workflows/deploy.yml` workflow, run the following command after container builds:

```yaml
- name: Trigger Dokploy Redeployment
  run: |
    curl -s -X POST "${{ secrets.DOKPLOY_URL }}/api/application.redeploy" \
      -H "x-api-key: ${{ secrets.DOKPLOY_API_KEY }}" \
      -H "Content-Type: application/json" \
      -d '{"applicationId": "${{ secrets.DOKPLOY_APPLICATION_ID }}"}'
```


## Troubleshooting
- **502 Bad Gateway**: Usually means the Backend is down or still starting. Check backend logs for `wait_for_services.py` status.
- **404 Not Found on API**: Check `nginx.conf` for trailing slashes in `proxy_pass`.
- **Meilisearch Crash**: Check if `MEILI_MASTER_KEY` is at least 16 bytes and ensure the memory limit is at least 2GB.
