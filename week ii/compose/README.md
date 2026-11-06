# Todo stack: a multi-container demo with Docker Compose

A small todo list built from five containers that talk to each other over Compose networks.

| Service    | Image / build              | Role                                                  | Networks      |
|------------|----------------------------|-------------------------------------------------------|---------------|
| `frontend` | `./frontend` (Node, nginx) | Serves the React app, proxies `/api` to the backend   | front         |
| `backend`  | `./backend` (Python)       | FastAPI REST API                                      | front, back   |
| `db`       | `postgres:16-alpine`       | Stores the todos (volume `pgdata`)                    | back          |
| `redis`    | `redis:7-alpine`           | Caches the todo list, counts requests (volume `redisdata`) | back     |
| `adminer`  | `adminer:4`                | Database UI, only with `--profile debug`              | back, tools   |

```
browser ──:8080──▶ frontend (nginx) ──/api──▶ backend ──▶ db
                         front network         │    back network (internal)
                                               └──▶ redis
```

The `back` network is `internal: true`, so the database and Redis have no route to the outside world and the browser cannot reach them. Only the frontend publishes a port.

## Run it

Requires Docker Desktop (or Docker Engine with the Compose plugin).

```bash
docker compose up -d --build      # build images and start everything
docker compose ps                 # all services should become "healthy"
```

Open http://localhost:8080.

The database password is a Compose secret read from `secrets/db_password.txt`. It is mounted at `/run/secrets/db_password` in `db` and `backend` and never appears in `compose.yaml` or in an image. The file is git-ignored; a fresh clone needs `cp secrets/db_password.txt.example secrets/db_password.txt`.

## Things to try in class

```bash
# Startup order: db and redis must be healthy before backend starts, backend before frontend
docker compose up -d && docker compose ps

# Service discovery by name: the backend reaches "db" and "redis" through Docker DNS
docker compose exec backend getent hosts db redis

# Segmentation: the frontend is not on the back network, so this fails
docker compose exec frontend ping -c1 db

# Scale the API; the "Answered by container" line in the UI changes between refreshes
docker compose up -d --scale backend=3

# Redis as a cache: compare cache hits and misses, then look inside Redis
docker compose exec redis redis-cli keys '*'

# Failure: stop Redis. The app keeps working (no cache, no stats)
docker compose stop redis      # ...then: docker compose start redis

# Failure: stop the database. Reads may still come from the cache for up to 30 s, writes fail with 503
docker compose stop db         # ...then: docker compose start db  (no backend restart needed)

# Database UI on http://127.0.0.1:8081 (server: db, user: todo, database: todos)
docker compose --profile debug up -d

# Persistence
docker compose down            # containers removed, volumes kept: todos survive
docker compose down -v         # volumes removed too: back to the four seed todos
```

## API

| Method | Path               | Purpose                                         |
|--------|--------------------|-------------------------------------------------|
| GET    | `/api/todos`       | List todos (cached in Redis for 30 s)           |
| POST   | `/api/todos`       | Create, body `{"title": "..."}`                 |
| PATCH  | `/api/todos/{id}`  | Update, body `{"done": true}` and/or `{"title": "..."}` |
| DELETE | `/api/todos/{id}`  | Delete                                          |
| GET    | `/api/health`      | 200 when the database answers, 503 otherwise (used by the healthcheck) |
| GET    | `/api/stats`       | Request counter, cache hits/misses, which container answered |

Interactive API docs (Swagger UI): http://localhost:8080/api/docs

## Files

```
compose.yaml            the whole system in one file
.env / .env.example     values for ${TAG} and ${APP_PORT} in compose.yaml
secrets/                db_password.txt (git-ignored) and an example
db/init.sql             table and seed data, runs once on an empty volume
backend/                FastAPI app, Dockerfile, requirements.txt
frontend/               React (Vite) app, multi-stage Dockerfile, nginx.conf
```

## Developing without Docker

```bash
cd backend && pip install -r requirements.txt
DB_HOST=localhost REDIS_HOST=localhost DB_PASSWORD=lab-only-password uvicorn app.main:app --reload
cd frontend && npm install && npm run dev     # http://localhost:5173, /api proxied to :8000
```

## Troubleshooting

- `docker compose ps` shows `backend` as unhealthy: check `docker compose logs backend db`. Most often the password in `secrets/db_password.txt` changed after the `pgdata` volume was created; the database keeps its first password. Run `docker compose down -v` to start over.
- Port 8080 already in use: change `APP_PORT` in `.env`.
- Edited `db/init.sql` but nothing changed: it only runs on an empty volume (`docker compose down -v`).
