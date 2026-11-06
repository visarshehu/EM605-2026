# Where does container data go? Three MySQL examples

Containers are **ephemeral**: when you remove a container, everything written inside
it is gone. A database you cannot keep is not much of a database, so Docker gives you
two ways to keep data *outside* the container's own writable layer:

| Example | Flag | Who manages the storage | Survives `docker rm`? |
|---------|------|-------------------------|-----------------------|
| `01-no-volume.sh`    | *(none)*                              | Nobody — data lives in the container layer | ❌ No  |
| `02-named-volume.sh` | `-v dbdata:/var/lib/mysql`            | **Docker** (a named volume)                | ✅ Yes |
| `03-bind-mount.sh`   | `-v "$(pwd)/mysql-data:/var/lib/mysql"` | **You** (a folder on your computer)      | ✅ Yes |

```
             container writable layer          named volume            bind mount
             (dies with the container)       (Docker-managed)      (a folder you own)

  mysqld ──▶ /var/lib/mysql                  /var/lib/mysql  ◀──┐   /var/lib/mysql  ◀──┐
                                                                │                      │
                                             docker volume ─────┘   ./mysql-data ──────┘
```

The rule to remember: **`-v SOURCE:PATH-INSIDE-CONTAINER`**. If `SOURCE` is a plain
name it is a *named volume*; if it is a path (starts with `/` or `./` or `$(pwd)`) it
is a *bind mount*.

All three examples run the same `mysql:8` image with the same password and database,
so the only thing that changes is how storage is attached.

## Prerequisites

Docker Desktop running. No Compose needed — these are plain `docker run` commands.

```bash
chmod +x *.sh      # once, to make the scripts executable
```

---

## Example 1 — no volume (data is lost)

```bash
./01-no-volume.sh
```

This starts MySQL with **no** storage attached. It works fine... until the container
is removed. Prove it:

```bash
# 1. Wait for it to be ready, then write a row
docker exec -it mysql-novol mysql -uroot -psecret demo \
  -e "CREATE TABLE t (msg VARCHAR(50)); INSERT INTO t VALUES ('I will not survive');"

# 2. Read it back — it's there
docker exec -it mysql-novol mysql -uroot -psecret demo -e "SELECT * FROM t;"

# 3. Remove the container and start a fresh one
docker rm -f mysql-novol
./01-no-volume.sh

# 4. The table is gone
docker exec -it mysql-novol mysql -uroot -psecret demo -e "SELECT * FROM t;"
#   ERROR 1146 (42S02): Table 'demo.t' doesn't exist
```

**Lesson:** the container's writable layer is deleted with the container. Never keep a
real database this way.

---

## Example 2 — named volume (Docker keeps the data)

```bash
./02-named-volume.sh
```

Same container, but `-v dbdata:/var/lib/mysql` tells Docker to store `/var/lib/mysql`
in a **named volume** called `dbdata`. Repeat the test — this time the row survives:

```bash
docker exec -it mysql-named mysql -uroot -psecret demo \
  -e "CREATE TABLE t (msg VARCHAR(50)); INSERT INTO t VALUES ('I survive rm');"

docker rm -f mysql-named
./02-named-volume.sh      # fresh container, same volume

docker exec -it mysql-named mysql -uroot -psecret demo -e "SELECT * FROM t;"
#   +--------------+
#   | msg          |
#   +--------------+
#   | I survive rm |
#   +--------------+
```

Inspect the volume Docker is managing for you:

```bash
docker volume ls                 # dbdata appears in the list
docker volume inspect dbdata     # see its Mountpoint (inside the Docker VM)
```

**Lesson:** this is the normal way to persist a database. You do not pick where the
files live — Docker does — and the data outlives any single container.

To really start over, remove the volume too:

```bash
docker rm -f mysql-named
docker volume rm dbdata
```

---

## Example 3 — bind mount (a folder on your computer)

```bash
./03-bind-mount.sh
```

Here `-v "$(pwd)/mysql-data:/var/lib/mysql"` maps a folder **on your machine** into the
container. The database files appear in `./mysql-data`, where you can see them:

```bash
ls mysql-data        # ib_logfile*, mysql/, demo/, ... MySQL's actual files
```

The data survives `docker rm -f` exactly like the named volume — but now *you* own the
folder, can back it up with `cp`, and can see it grow. The trade-off is that you are
responsible for the path, and bind-mounting a database is sensitive to host filesystem
permissions.

**Lesson:** bind mounts are great when you want the files right there in your project —
source code you are editing, config files, a folder to inspect. For databases a named
volume is usually the better choice; this example exists so you can *see* the files.

Clean up (this deletes the data folder):

```bash
docker rm -f mysql-bind
rm -rf mysql-data
```

---

## Named volume vs. bind mount — when to use which

- **Named volume** — Docker-managed, portable, good default for **databases** and any
  state you just need to persist and don't need to open by hand.
- **Bind mount** — a specific folder you control, good for **editing files live**
  (source code, HTML, config) where you want changes on the host to show up inside the
  container immediately.

Both use the same flag; the only difference is whether the left side of `-v` is a
**name** or a **path**.
