import { Fragment, useEffect, useState } from "react";

const api = async (path, options = {}) => {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? null : res.json();
};

export default function App() {
  const [todos, setTodos] = useState([]);
  const [title, setTitle] = useState("");
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      setTodos(await api("/todos"));
      setStats(await api("/stats"));
      setError("");
    } catch (e) {
      setError(`Backend problem: ${e.message}`);
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, []);

  const run = async (fn) => {
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(`Backend problem: ${e.message}`);
    }
  };

  const add = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    run(async () => {
      await api("/todos", { method: "POST", body: JSON.stringify({ title }) });
      setTitle("");
    });
  };

  const toggle = (t) =>
    run(() => api(`/todos/${t.id}`, { method: "PATCH", body: JSON.stringify({ done: !t.done }) }));
  const remove = (t) => run(() => api(`/todos/${t.id}`, { method: "DELETE" }));

  const open = todos.filter((t) => !t.done).length;

  return (
    <main>
      <header>
        <h1>Todo</h1>
        <p className="muted">React · FastAPI · PostgreSQL · Redis, wired with Docker Compose</p>
      </header>

      <form onSubmit={add}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What needs doing?" />
        <button type="submit">Add</button>
      </form>

      {error && <p className="error">{error}</p>}

      <ul>
        {todos.map((t) => (
          <li key={t.id} className={t.done ? "done" : ""}>
            <label>
              <input type="checkbox" checked={t.done} onChange={() => toggle(t)} />
              <span>{t.title}</span>
            </label>
            <button className="link" onClick={() => remove(t)} aria-label={`Delete ${t.title}`}>
              ×
            </button>
          </li>
        ))}
      </ul>
      <p className="muted">{open} open · {todos.length} total</p>

      {stats && (
        <section className="stats">
          <h2>Under the hood</h2>
          <dl>
            <dt>Answered by container</dt><dd><code>{stats.served_by}</code></dd>
            <dt>API requests (Redis counter)</dt><dd>{stats.requests ?? "Redis down"}</dd>
            <dt>Cache hits / misses</dt><dd>{stats.cache_hits ?? "-"} / {stats.cache_misses ?? "-"}</dd>
          </dl>
          {stats.by_host && Object.keys(stats.by_host).length > 1 && (
            <>
              <h3>Requests per backend replica</h3>
              <dl>
                {Object.entries(stats.by_host).map(([host, n]) => (
                  <Fragment key={host}><dt><code>{host}</code></dt><dd>{n}</dd></Fragment>
                ))}
              </dl>
            </>
          )}
        </section>
      )}
    </main>
  );
}
