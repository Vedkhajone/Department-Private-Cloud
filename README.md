# Department Engineering Cloud (DECP)

**A private, department-owned cloud platform for students — built from scratch and fully containerized.**

DECP is a self-hosted platform that gives students a personal cloud
workspace on department-owned hardware: authentication and accounts,
personal file storage, project hosting, a project repository, an admin
dashboard, resource monitoring, and automated deployments/backups —
all running on a department Ubuntu server instead of a third-party
cloud service.

Students can register an account, log in, and access their own space
on the platform, with role-based access for students, faculty, and
admins.

---

## Architecture

```
Browser
   │
   ▼
 NGINX   (single public entry point)
   ├── /        → React + TypeScript frontend (Vite)
   └── /api/*   → FastAPI backend
                      │
                      ▼
                 PostgreSQL
```

Every service — frontend, backend, database, reverse proxy — runs in
its own Docker container, orchestrated with Docker Compose. Containers
talk to each other by service name over a private Docker network, so
the exact same setup that runs on a personal PC during development
runs unchanged on the department Ubuntu server.

---

## Tech stack

| Layer | Technology |
|---|---|
| Reverse proxy | NGINX |
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Auth | JWT (PyJWT), Argon2 password hashing (pwdlib) |
| Orchestration | Docker, Docker Compose |


## Documentation

| Doc | Covers |
|---|---|
| [`Department-Engineering-Cloud/README.md`](./Department-Engineering-Cloud/README.md) | Setup, running, stopping, logs, troubleshooting |
| [`docs/architecture.md`](./Department-Engineering-Cloud/docs/architecture.md) | How the containers fit together, request flow, images vs. containers |
| [`docs/database.md`](./Department-Engineering-Cloud/docs/database.md) | Users table, password hashing, JWT auth flow |
| [`docs/FILE-GUIDE.md`](./docs/FILE-GUIDE.md) | What every file and folder in the project does |

---

## Project layout

```
Department-Private-Cloud/
├── docs/
│   └── FILE-GUIDE.md
└── Department-Engineering-Cloud/
    ├── backend/          # FastAPI app (auth, users, db, schemas)
    ├── frontend/         # React + TypeScript (Vite)
    ├── nginx/             # Reverse proxy config
    ├── docs/               # Architecture & database docs
    ├── docker-compose.yml
    └── README.md
```
