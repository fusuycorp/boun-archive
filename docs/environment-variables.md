# Environment Variables Reference

These variables must be configured in the Dokploy Stack "Environment" tab.

## Database (PostgreSQL)
| Variable | Value | Description |
|----------|-------|-------------|
| `POSTGRES_USER` | `boun_user` | Database admin user. |
| `POSTGRES_PASSWORD` | `********` | Database admin password. |
| `POSTGRES_DB` | `boun_archive` | Main database name. |
| `DATABASE_URL` | `postgresql://boun_user:password@db:5432/boun_archive` | Connection string for Backend. |

## Search & Cache
| Variable | Value | Description |
|----------|-------|-------------|
| `MEILI_MASTER_KEY` | `(min 16 chars)` | Master key for Meilisearch production mode. |
| `MEILI_URL` | `http://meilisearch:7700` | Internal URL for Backend. |
| `REDIS_URL` | `redis://redis:6379` | Internal URL for Backend caching. |

## Frontend (Public)
| Variable | Value | Description |
|----------|-------|-------------|
| `PUBLIC_API_URL` | `https://bountools.com/api` | The base URL the browser uses to reach the API. |
| `CORS_ORIGINS` | `https://bountools.com` | Allowed origins for FastAPI. |

## Internal Port Defaults
These are usually provided in `docker-stack.yml` but can be overridden:
- `BACKEND_PORT`: `8000`
- `FRONTEND_PORT`: `3000`
- `DB_PORT`: `5432`
- `MEILI_PORT`: `7700`
