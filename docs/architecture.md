# DECP Architecture

This document explains the current technical foundation of the Department
Engineering Cloud (DECP) platform, in plain language.

As of Phase 2, the platform has its first real feature: authentication
and user management (registration, login, JWT-protected endpoints, and
basic role-based access control for `student` / `faculty` / `admin`).
File storage, project hosting, and the admin dashboard are still future
phases. See [`docs/database.md`](./database.md) for details on the
`users` table, password hashing, and the authentication flow.

## 1. What each service does

The platform is split into four containers, each with one job:

- **nginx** — the single public entry point. It's the only service exposed
  to your browser. It looks at the request path and forwards ("proxies")
  it to either the frontend or the backend.
- **frontend** — a React + TypeScript app (built with Vite) that renders
  the web page you see, including login/registration/dashboard, and talks
  to the backend over HTTP.
- **backend** — a FastAPI (Python) application that exposes an API: a
  health check, and now `/api/auth/*` and `/api/users/*` for
  authentication and user data.
- **postgres** — a PostgreSQL database. It now stores the `users` table
  (see `docs/database.md`), created and versioned through Alembic
  migrations rather than by hand.

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
  ├── "/"      → forwarded to the frontend container (React app)
  └── "/api/*" → forwarded to the backend container (FastAPI)
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
├── main.py           # assembles the FastAPI app and routers
├── config.py         # reads all settings from environment variables
├── db/database.py    # SQLAlchemy engine, session, declarative Base
├── models/user.py    # ORM model -- the users table's structure
├── schemas/user.py   # Pydantic request/response shapes (API contract)
├── api/auth.py        # POST /api/auth/register, /login
├── api/users.py        # GET /api/users/me, and a role-protected example
└── auth/
    ├── security.py     # password hashing, JWT create/decode
    └── dependencies.py # get_current_user, require_role
```

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
