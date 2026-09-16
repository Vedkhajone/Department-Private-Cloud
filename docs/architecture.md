# DECP Architecture

This document explains the current technical foundation of the Department
Engineering Cloud (DECP) platform, in plain language.

As of Phase 4, the platform has authentication and user management,
personal cloud storage, and **Universal Website Hosting & Deployment**
-- students can upload a ZIP and get a live static site or a running
Flask/FastAPI/Node.js app, each isolated in its own Docker container.
The admin dashboard is still a future phase. See
[`docs/database.md`](./database.md) for the database tables and
authentication/storage flows, and
[`docs/WEBSITE-HOSTING.md`](./WEBSITE-HOSTING.md) for the full website
hosting architecture (this document only summarizes it in section 11
below).

## 1. What each service does

The platform is split into four containers, each with one job:

- **nginx** — the single public entry point. It's the only service exposed
  to your browser. It looks at the request path and forwards ("proxies")
  it to either the frontend or the backend.
- **frontend** — a React + TypeScript app (built with Vite) that renders
  the web page you see, including login/registration/dashboard, and talks
  to the backend over HTTP.
- **backend** — a FastAPI (Python) application that exposes an API:
  a health check, `/api/auth/*` and `/api/users/*` for authentication,
  `/api/folders/*`, `/api/files/*`, and `/api/storage/usage` for
  personal cloud storage, and now `/api/websites/*` for website
  hosting/deployment plus the public `/sites/*` and `/apps/*` routes
  that actually serve deployed websites. It also talks to the Docker
  daemon (via a socket mounted only into this container) to build and
  run isolated containers for dynamic websites.
- **postgres** — a PostgreSQL database. It stores the `users`,
  `folders`, `files`, and `websites` tables (see `docs/database.md`)
  — metadata only, never file contents — created and versioned through
  Alembic migrations rather than by hand.

## 2. How Docker Compose connects the services

`docker-compose.yml` defines all four services and starts them together
on a shared, private Docker network. Inside that network, containers
reach each other **by service name** instead of an IP address — for
example, the backend connects to Postgres at host `postgres`, and NGINX
proxies to the backend at `backend:8000` and the frontend at
`frontend:5173`. Docker's internal DNS resolves those names automatically.

This means nothing is hardcoded to "localhost" or a specific IP, which is
exactly what makes the same `docker-compose.yml` work unchanged on the
department Ubuntu server.

## 3. Browser request flow

```
Browser
  │
  ▼
NGINX (port 8080 on your machine → port 80 in the container)
  ├── "/"        → forwarded to the frontend container (React app)
  ├── "/api/*"   → forwarded to the backend container (FastAPI)
  ├── "/sites/*" → forwarded to the backend (serves static websites)
  └── "/apps/*"  → forwarded to the backend (proxies to dynamic
                    websites' isolated containers)
```

Your browser only ever talks to NGINX. It never connects to the FastAPI
backend or the frontend dev server directly — NGINX hides those details
and presents one unified address to the outside world.

## 4. Why PostgreSQL uses a persistent volume

Containers are meant to be disposable — you can delete and recreate them
at any time without worrying about losing anything **inside** the
container's own filesystem, because normally you shouldn't be keeping
anything important there.

Database data is the exception: it must survive even when the container
is removed. Docker volumes solve this by storing the data **outside** the
container, on the host machine, and "mounting" it into the container at
a known path (`/var/lib/postgresql/data`). When you run
`docker compose down` followed by `docker compose up`, Postgres starts a
brand-new container, but it reattaches to the same volume and sees all
of its previous data.

## 5. Why NGINX is placed in front of the application

Putting NGINX in front of everything gives us:

- **One entry point** — the browser only needs to know one address, not
  separate ports for the frontend and backend.
- **No exposed internal ports** — the FastAPI and Vite dev server ports
  are never published to the outside world, only reachable inside the
  Docker network.
- **A natural place to add things later** — HTTPS/TLS, rate limiting,
  caching, and routing rules can all be added at the NGINX layer without
  touching the frontend or backend code.

## 6. Difference between a Docker image and a Docker container

- A **Docker image** is a read-only template — a snapshot of a filesystem
  plus instructions on how to run something (e.g. "Python 3.12 with these
  dependencies installed, run `uvicorn` on start"). Images are built once
  from a `Dockerfile` and can be reused anywhere.
- A **Docker container** is a running (or stopped) instance of an image —
  the same relationship as a class and an object, or a program and a
  process. You can start multiple containers from the same image, and
  each one runs independently.

`docker compose up` builds the images (if needed) and then starts one
container per service defined in `docker-compose.yml`.

## 7. Why this architecture can later be moved to the department Ubuntu server

Every service runs the same way regardless of the host operating system,
because Docker abstracts away the differences between Windows and Linux
at the container level. As long as Docker Engine and Docker Compose are
installed on the department server:

- The same `docker-compose.yml`, Dockerfiles, and source code can be
  copied over (e.g. via `git clone`) and run with the same commands.
- Configuration differences (like real database passwords) are handled
  through the `.env` file, which is never committed to Git — so the
  server gets its own `.env` with production values, while the rest of
  the codebase stays identical.
- Nothing in the setup depends on Windows-only tools or paths, which is
  why development happens through Docker even on a Windows PC — the
  containers themselves are always Linux-based.

This is the core benefit of containerizing the project from day one:
"it works on my machine" becomes "it works in this container," which is
true everywhere Docker runs.

## 8. Backend module layout

The backend is split by responsibility instead of living in one file:

```
backend/app/
├── main.py             # assembles the FastAPI app and routers
├── config.py           # reads all settings from environment variables
├── db/database.py      # SQLAlchemy engine, session, declarative Base
├── models/
│   ├── user.py          # users table
│   ├── folder.py         # folders table (logical grouping only)
│   └── file.py            # files table (metadata only, no file bytes)
├── schemas/
│   ├── user.py           # user request/response shapes
│   ├── folder.py          # folder request/response shapes
│   ├── file.py             # file request/response shapes
│   └── storage.py          # storage usage response shape
├── api/
│   ├── auth.py            # POST /api/auth/register, /login
│   ├── users.py            # GET /api/users/me, and a role-protected example
│   ├── folders.py           # /api/folders/* endpoints
│   ├── files.py              # /api/files/* endpoints
│   └── storage.py             # GET /api/storage/usage
├── auth/
│   ├── security.py         # password hashing, JWT create/decode
│   └── dependencies.py      # get_current_user, require_role
├── storage/
│   ├── paths.py             # safe on-disk path resolution (no user input touches paths)
│   └── service.py            # folder/file business logic: ownership, quota, CRUD
└── deploy/                    # website hosting (Phase 4)
    ├── paths.py                # safe on-disk path resolution for websites
    ├── zip_safety.py            # safe ZIP validation/extraction
    ├── slug.py                   # server-generated, unique URL slugs
    ├── detection.py                # deterministic static/dynamic framework detection
    ├── builder.py                   # DECP-controlled Dockerfile templates
    ├── containers.py                 # Docker SDK: build/run/stop/remove containers+networks
    └── service.py                     # deployment orchestration, ownership, lifecycle
```

`api/websites.py` (management: deploy/list/start/stop/restart/logs/
delete) and `api/public_sites.py` (the public `/sites/*` and `/apps/*`
routes that actually serve a website) sit alongside the other routers
in `api/`.

This separation means, for example, that the users *table* (`models`)
can change independently of what the *API* exposes (`schemas`) -- the
password hash is a real database column, but `UserOut` (the schema used
in responses) simply never includes it, so it can't leak by accident.

## 9. Authentication architecture

```
Register:  password → Argon2 hash → stored in "users.password_hash"
Login:     password + stored hash → verified → JWT issued
Request:   Authorization: Bearer <JWT> → verified → user identified
```

- Registration and login are public endpoints (`/api/auth/register`,
  `/api/auth/login`).
- Login returns a signed JSON Web Token (JWT) containing the user's id
  and role, plus an expiry time.
- The frontend stores that token and sends it as an `Authorization:
  Bearer <token>` header on every request to a protected endpoint.
- A FastAPI dependency (`get_current_user`) decodes and validates the
  token on each request; `require_role(...)` builds on top of it to
  restrict specific endpoints to specific roles.

Full detail -- including exactly what's in the token, how role checks
work, and why passwords are hashed rather than encrypted -- is in
[`docs/database.md`](./database.md).

## 10. Personal cloud storage architecture

```
PostgreSQL                          Filesystem (STORAGE_ROOT)
-----------                         --------------------------
folders table                       (no mirror -- folders are
  (logical hierarchy only)           purely a database concept)

files table                         STORAGE_ROOT/users/<user_id>/<uuid>
  name = "essay.docx"      ------->   actual file bytes live here,
  storage_path = "<uuid>"             named by a random UUID, not by
                                       the display name
```

The database stores **metadata** (names, folder hierarchy, size, who
owns what); the filesystem stores **file contents**. The two are linked
only by `files.storage_path`, an opaque, server-generated identifier
-- never a user-supplied name or path. This is also why renaming a
file is instant and never touches disk: only the database row changes.

**Where files actually live:** Docker Compose mounts a host directory
(`STORAGE_HOST_PATH`, e.g. `./storage-data` in development) into the
backend container at `STORAGE_ROOT` (`/cloud-data`). Files are never
stored inside the Docker image or an ephemeral container filesystem,
so they survive container restarts and `docker compose down` / `up`
the same way the Postgres volume does. Moving to the department server
means changing only `STORAGE_HOST_PATH` in `.env` to a real, durable
path on that machine -- no code changes.

**Path safety:** every physical path is built from two trusted,
server-controlled values only -- the authenticated user's numeric id
and a randomly generated UUID -- and `app/storage/paths.py` double-
checks the resolved path never escapes `STORAGE_ROOT` before it's
used. A file or folder's *display name* (which a user does control)
is validated (no `/`, `\`, null bytes, `.`/`..`) but never becomes part
of a filesystem path in the first place, so path traversal isn't
merely blocked -- there's no path derived from user input to traverse
with.

**Quota:** each user has a `storage_limit` (stored in the `users`
table, in megabytes; see `docs/database.md`). Every upload recalculates
the user's current usage from the `files` table and rejects the
upload (`413`) if it would exceed the quota -- checked both before
writing (using existing usage) and while streaming (so a single huge
upload can't blow past the limit before the check catches up).

## 11. Website hosting architecture (summary)

Full detail is in [`docs/WEBSITE-HOSTING.md`](./WEBSITE-HOSTING.md).
In short:

```
ZIP upload
   │
   ▼
Safe extraction (reject traversal/absolute paths/symlinks, size/count limits)
   │
   ▼
Deterministic detection: static (HTML or built React/Vite) vs.
dynamic (Flask/FastAPI/Node.js) -- no AI/LLM involved
   │
   ├── static  → files moved into STORAGE_ROOT/websites/<user>/<id>/
   │             served directly by the backend at /sites/<slug>
   │
   └── dynamic → DECP-controlled Dockerfile generated (a student's own
                 Dockerfile, if any, is never used) → image built →
                 an isolated container started on its own dedicated
                 Docker network → reachable at /apps/<slug>, proxied
                 by the backend to the container by name (never via a
                 published host port)
```

Dynamic containers get no Docker socket, no host filesystem mount, no
DECP secrets, and their own network with no route to Postgres or to
any other student's container -- see WEBSITE-HOSTING.md's "Security
model" section for the complete picture. A Docker build can take a
while, so it runs as a background task after the API responds
immediately with `status: "building"`; the frontend polls until it
becomes `online` (or `failed`, with a reason).
