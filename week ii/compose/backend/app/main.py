"""Todo API: FastAPI + PostgreSQL (data) + Redis (cache and counters)."""
import json
import os
import socket

import psycopg
import redis
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel


def read_secret(name: str, default: str = "") -> str:
    """Read VAR_FILE if set (Compose secret), otherwise VAR."""
    path = os.getenv(f"{name}_FILE")
    if path:
        with open(path) as f:
            return f.read().strip()
    return os.getenv(name, default)


DB_DSN = (
    f"host={os.getenv('DB_HOST', 'db')} "
    f"dbname={os.getenv('DB_NAME', 'todos')} "
    f"user={os.getenv('DB_USER', 'todo')} "
    f"password={read_secret('DB_PASSWORD')} "
    "connect_timeout=3"
)
cache = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379,
                    decode_responses=True, socket_timeout=2)
CACHE_KEY = "todos:all"
HOSTNAME = socket.gethostname()  # container ID: shows which replica answered

app = FastAPI(title="Todo API", docs_url="/api/docs", openapi_url="/api/openapi.json")


def db():
    # New connection per request: simple, and survives database restarts.
    return psycopg.connect(DB_DSN, row_factory=dict_row)


def to_json(rows):
    return [{**r, "created_at": r["created_at"].isoformat()} for r in rows]


class TodoIn(BaseModel):
    title: str


class TodoPatch(BaseModel):
    title: str | None = None
    done: bool | None = None


@app.middleware("http")
async def count_requests(request, call_next):
    try:
        cache.incr("stats:requests")
        cache.hincrby("stats:by_host", HOSTNAME, 1)
    except redis.RedisError:
        pass  # stats are optional; the API keeps working without Redis
    return await call_next(request)


@app.get("/api/health")
def health():
    status = {"host": HOSTNAME}
    try:
        with db() as conn:
            conn.execute("SELECT 1")
        status["db"] = "ok"
    except psycopg.Error:
        status["db"] = "down"
    try:
        cache.ping()
        status["redis"] = "ok"
    except redis.RedisError:
        status["redis"] = "down"
    if status["db"] != "ok":
        raise HTTPException(503, status)
    return status


@app.get("/api/todos")
def list_todos():
    try:
        cached = cache.get(CACHE_KEY)
        if cached:
            cache.incr("stats:cache_hits")
            return json.loads(cached)
        cache.incr("stats:cache_misses")
    except redis.RedisError:
        pass
    try:
        with db() as conn:
            rows = conn.execute(
                "SELECT id, title, done, created_at FROM todos ORDER BY id"
            ).fetchall()
    except psycopg.OperationalError:
        raise HTTPException(503, "database unavailable")
    data = to_json(rows)
    try:
        cache.set(CACHE_KEY, json.dumps(data), ex=30)
    except redis.RedisError:
        pass
    return data


def invalidate():
    try:
        cache.delete(CACHE_KEY)
    except redis.RedisError:
        pass


@app.post("/api/todos", status_code=201)
def create_todo(todo: TodoIn):
    title = todo.title.strip()
    if not title:
        raise HTTPException(422, "title must not be empty")
    try:
        with db() as conn:
            row = conn.execute(
                "INSERT INTO todos (title) VALUES (%s) "
                "RETURNING id, title, done, created_at", (title,)
            ).fetchone()
    except psycopg.OperationalError:
        raise HTTPException(503, "database unavailable")
    invalidate()
    return to_json([row])[0]


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, patch: TodoPatch):
    try:
        with db() as conn:
            row = conn.execute(
                "UPDATE todos SET title = COALESCE(%s, title), "
                "done = COALESCE(%s, done) WHERE id = %s "
                "RETURNING id, title, done, created_at",
                (patch.title, patch.done, todo_id),
            ).fetchone()
    except psycopg.OperationalError:
        raise HTTPException(503, "database unavailable")
    if row is None:
        raise HTTPException(404, "todo not found")
    invalidate()
    return to_json([row])[0]


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    try:
        with db() as conn:
            cur = conn.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
    except psycopg.OperationalError:
        raise HTTPException(503, "database unavailable")
    if cur.rowcount == 0:
        raise HTTPException(404, "todo not found")
    invalidate()


@app.get("/api/stats")
def stats():
    try:
        return {
            "served_by": HOSTNAME,
            "requests": int(cache.get("stats:requests") or 0),
            "cache_hits": int(cache.get("stats:cache_hits") or 0),
            "cache_misses": int(cache.get("stats:cache_misses") or 0),
            "by_host": {k: int(v) for k, v in cache.hgetall("stats:by_host").items()},
        }
    except redis.RedisError:
        return {"served_by": HOSTNAME, "redis": "down"}
