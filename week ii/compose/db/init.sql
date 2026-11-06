-- Runs only the first time the pgdata volume is created
CREATE TABLE IF NOT EXISTS todos (
    id         SERIAL PRIMARY KEY,
    title      TEXT        NOT NULL,
    done       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO todos (title, done) VALUES
    ('Read the Docker Compose documentation', TRUE),
    ('Run docker compose up -d --build', FALSE),
    ('Scale the backend to three copies', FALSE),
    ('Stop the database and watch what happens', FALSE);
