# DECP Website Hosting (Phase 4)

This document explains Universal Website Hosting & Deployment: how a
student's ZIP becomes a live website, in beginner-friendly terms.

## What a student can deploy

| Category | Detected by | Served by |
|---|---|---|
| Static HTML/CSS/JS | `index.html` at the ZIP root | Files served directly by the backend |
| Built React/Vite app | `dist/index.html` | Only the `dist/` contents are deployed; files served directly |
| Flask | `requirements.txt` (containing `flask`) + `app.py`/`main.py` | An isolated Docker container |
| FastAPI | `requirements.txt` (containing `fastapi`) + `app.py`/`main.py` | An isolated Docker container |
| Node.js | `package.json` with a `"start"` script | An isolated Docker container |

Anything that doesn't match one of these is rejected with a specific
error explaining what's missing -- detection never guesses (see
"Deterministic detection" below).

## The deploy flow, end to end

```
ZIP upload
   │
   ▼
Stream to a temp file, enforcing MAX_WEBSITE_ZIP_SIZE_BYTES while streaming
   │
   ▼
Safe extraction to a temp staging directory (app/deploy/zip_safety.py)
   │  -- rejects path traversal, absolute paths, symlinks,
   │     too many files, or too much extracted data
   ▼
Deterministic framework detection (app/deploy/detection.py)
   │
   ├── static ──► move files into permanent storage ──► status = online
   │              (fast enough to finish inside the request)
   │
   └── dynamic ─► create the `websites` row, status = building,
                  return the response immediately
                       │
                       ▼ (runs as a FastAPI BackgroundTask, after
                          the HTTP response has already gone out)
                  Move the validated project into permanent storage
                       │
                  Generate a DECP-controlled Dockerfile
                  (a student-supplied Dockerfile, if any, is ignored)
                       │
                  docker build → image
                       │
                  Create a dedicated Docker network for this website
                       │
                  docker run → isolated container, resource-limited
                       │
                  status = online (or failed, with error_message set)
```

The frontend's "My Websites" page polls `GET /api/websites` every few
seconds while any website is `pending`/`building`, so the UI updates
to `online`/`failed` on its own without the student needing to refresh.

## Static deployment, in detail

1. The extracted (and now-validated) project directory is moved,
   file by file, into `STORAGE_ROOT/websites/<user_id>/<website_id>/`
   -- a directory that persists on the host (see "Storage" below).
2. The `websites` row's `status` becomes `online` and `public_url`
   becomes `/sites/<slug>/` -- **with a trailing slash**. This matters:
   a page's relative asset links (`<link href="style.css">`) resolve
   against the *directory* the browser thinks it's in, so serving
   `index.html` at `/sites/<slug>` (no slash) would make those links
   resolve against `/sites/` instead and silently 404 -- the site
   would appear to have "lost" its CSS/JS even though the files are
   on disk. `GET /sites/<slug>` (no trailing slash) 307-redirects to
   `/sites/<slug>/` for exactly this reason, the same way a normal web
   server handles a directory URL; `public_url` is stored with the
   slash already in place so "Open Website" skips that extra redirect.
3. A request to `/sites/<slug>/<path>` (see "Routing" below) resolves
   `<path>` against that directory, defaulting to `index.html` for the
   slash-terminated slug or any subdirectory. The resolved path is
   checked to still be inside that website's own directory before
   anything is read from disk -- the same containment guard used
   throughout the storage layer (`app/storage/paths.py`), applied here
   too.

## Dynamic deployment, in detail

**Framework detection is deterministic** (`app/deploy/detection.py`):
it looks only for specific files (`requirements.txt` containing
`flask`/`fastapi`, or `package.json` with a `start` script) plus a
matching entry point. No AI/LLM involvement, and no framework is ever
guessed -- an ambiguous project is rejected with a message explaining
exactly what's missing. This is intentional: a wrong guess would mean
either a failed deployment or, worse, running code in a way its author
didn't intend.

**Controlled image builds** (`app/deploy/builder.py`): DECP never
executes a student-supplied Dockerfile, even if the ZIP contains one.
Instead, one of three small, fixed Dockerfile templates is generated
based on the detected framework:

```dockerfile
# Flask (generated)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]      # or main.py
```

(FastAPI and Node.js follow the same shape -- see `builder.py` for the
exact templates.) This means a student can never inject arbitrary
`FROM`/`RUN`/`VOLUME` instructions into the build.

**Build context isolation**: the Docker build only ever sees the
validated, extracted project directory -- never DECP's own source
code, `.env`, other students' files, or database credentials. Nothing
outside that one directory is copied into the build context, because
nothing outside it is ever passed to `docker build`.

**Container creation** (`app/deploy/containers.py`, via the Docker
SDK/`docker-py`):

```
docker build  →  decp-site-<website-id>:latest
docker network create  →  decp-app-<website-id>
docker run --network decp-app-<website-id> \
           --restart unless-stopped \
           --memory 512m --cpus 1.0 --pids-limit 100 \
           --cap-drop ALL --security-opt no-new-privileges \
           -e PORT=<internal-port> \
           decp-site-<website-id>:latest
```

No `-p`/published host port is used at all -- see "Port management"
below.

## Security model

### Docker socket

`/var/run/docker.sock` is mounted into the **backend** container only
(`docker-compose.yml`). It is never mounted into a student container.
A student's code has no way to talk to the Docker daemon, start other
containers, or affect any container besides its own.

### Network isolation

Every dynamic website gets its **own** Docker bridge network, created
at deploy time and named after the website's id
(`decp-app-<website-id>`). The backend connects itself to that network
(so it can reverse-proxy to the container by name); the student's
container joins *only* that network.

Consequences:
- The student's container has no route to PostgreSQL, to the backend's
  other traffic, or to any *other* student's container -- each
  website is network-isolated from every other website, not just from
  the core services.
- The backend reaches the container using Docker's built-in per-network
  DNS (the container's name resolves to its IP on that network) --
  never via a port published on the host.

**Known limitation**: the container's outbound internet access is not
restricted (needed for `pip install`/`npm install` during the image
build, and left open at runtime too, in this phase). A malicious
student app could still make outbound network calls to the internet.
Fully sandboxing egress (e.g. an explicit allowlist, or blocking it
entirely and only allowing it during the build step) is a reasonable
hardening step for a later phase -- documented here rather than
pretended away.

### No secrets reach student containers

A dynamic container's only environment variable is `PORT` (the port
its own app should listen on). It never receives `JWT_SECRET`,
`POSTGRES_PASSWORD`, or any other DECP configuration -- those exist
only in the backend container's environment, which is never shared
with anything the container-creation code sets up for a student app.

### No host filesystem access

Student containers get **no volume mounts at all** -- not `/`, not
`/cloud-data`, not the Docker socket, nothing. Everything the
container needs (its code, its dependencies) was already baked into
its image at build time; there's no live filesystem link back to the
host or to any other user's data.

### Resource limits

Applied to every dynamic container, all configurable via environment
variables (`.env.example`):

| Limit | Variable | Default |
|---|---|---|
| CPU | `CONTAINER_CPU_LIMIT` | 1.0 (one core) |
| Memory | `CONTAINER_MEMORY_LIMIT_MB` | 512 MB |
| Process count | `CONTAINER_PIDS_LIMIT` | 100 |
| Docker build timeout | `DOCKER_BUILD_TIMEOUT_SECONDS` | 300s |

Every container also runs with all Linux capabilities dropped
(`cap_drop: ALL`) and `no-new-privileges` set, on top of the CPU/
memory/process limits above.

### Ownership and cross-user isolation

Every website operation goes through
`app.deploy.service.get_owned_website`, which filters by **both** the
website's id *and* `owner_id == current_user.id` in the same database
query. A website belonging to another user looks exactly like one that
doesn't exist (`404`), the same pattern used throughout Phases 2-3.
The owner is always the authenticated user from the JWT -- the deploy
endpoint has no `owner_id` field a client could set.

### ZIP safety

See `app/deploy/zip_safety.py`. Before extracting a single byte:
- Every entry's resolved destination path is checked to remain inside
  the extraction directory (the actual traversal guard; explicit
  rejection of `..` components, absolute paths, and backslash paths
  is added on top as defense in depth).
- Symlink entries are rejected outright.
- Total file count and total uncompressed size are checked against
  `MAX_WEBSITE_FILES` / `MAX_WEBSITE_EXTRACTED_SIZE_BYTES`.
- The ZIP itself is capped at `MAX_WEBSITE_ZIP_SIZE_BYTES`, enforced
  while it's being streamed to disk (so an oversized upload is
  rejected before it's ever fully written).

## Port management

DECP does **not** allocate host ports for student apps at all -- no
port pool, no `-p 8101:5000`. Instead, every dynamic container listens
on a fixed, framework-determined port *inside its own network*
(`internal_port` in the `websites` table: 5000 for Flask, 8000 for
FastAPI, 3000 for Node), and the backend reaches it by container name
over that website's dedicated network. This is the "service discovery
instead of a host port pool" approach -- it sidesteps port-conflict
bookkeeping entirely, and (as a side effect) means nothing about a
student's app is ever reachable directly from outside Docker.

## NGINX routing

```
Browser
   │
   ▼
 NGINX
   ├── /            → React frontend
   ├── /api/         → FastAPI backend (existing)
   ├── /sites/<slug> → FastAPI backend → serves static files
   └── /apps/<slug>  → FastAPI backend → reverse-proxies to the
                        website's container
```

`/sites/` and `/apps/` are both forwarded to the backend exactly like
`/api/` already was -- **no NGINX configuration change is ever needed
when a new website is deployed**. The backend resolves the slug (from
the `websites` table) to either a directory on disk or a container to
proxy to, at request time. This is what makes the system extensible:
adding a new framework later only touches `app/deploy/`, never
`nginx/nginx.conf`.

`public_url` is stored as a **relative path** (`/sites/my-portfolio`,
never `http://localhost:8080/sites/my-portfolio`), so it keeps working
unchanged if the department server's IP or hostname changes -- the
browser resolves a relative link against whatever address it's
currently viewing DECP from.

## Storage

```
STORAGE_ROOT/
├── users/
│   └── <user_id>/                 (personal files -- Phase 3)
└── websites/
    └── <user_id>/
        └── <website_id>/
            ├── index.html, style.css, ...   (static), or
            └── build/                        (dynamic: the project
                                                Docker built the image
                                                from, kept for logs/
                                                future rebuilds)
```

Website files use their own namespace (`websites/`), completely
separate from personal file storage (`users/`), and use the same
persistent bind-mounted host directory (`STORAGE_HOST_PATH` →
`STORAGE_ROOT`) already established in Phase 3 -- so uploaded websites
survive `docker compose down`/`up` and container recreation exactly
like personal files and the Postgres database do. Nothing is ever
written inside the backend's Docker image.

## Background deployment (why builds don't block the request)

A Docker image build can take anywhere from a few seconds to a couple
of minutes. Blocking the HTTP request for that long risks browser/
proxy timeouts and a bad user experience. Dynamic deployment instead:

1. Returns the `websites` row immediately, with `status: "building"`.
2. Runs the actual build + container start in a FastAPI
   `BackgroundTask`, scheduled from the same request.
3. The frontend polls `GET /api/websites` every 3 seconds while
   anything is `pending`/`building`.

This is deliberately **not** a full job queue (no Celery/Redis) --
the brief explicitly asks not to add that infrastructure unless
genuinely required, and a background task is sufficient at this scale.

**Known limitation**: a `BackgroundTask` runs in the same process as
the request that scheduled it. If the backend container is restarted
or crashes while a build is in progress, that in-flight deployment is
lost (the website is left at `status: "building"` forever, rather than
resolving to `online`/`failed`). Recovering it currently means
deleting and redeploying that one website. A real job queue with
persistence would remove this limitation -- reasonable future work,
not implemented here to avoid the exact complexity (Celery/Redis) the
brief asked to avoid.

## Backend↔container network reconnection after a restart

Docker Compose only remembers the networks *it* creates and connects
services to. The per-website networks created dynamically via
`docker-py` are not tracked by Compose -- so if the backend container
is ever recreated (a plain `docker compose up` after `down`, or a
rebuild), it would otherwise start disconnected from every dynamic
website's network, breaking the reverse proxy until each site was
redeployed.

To fix this, the backend reconnects itself to every existing dynamic
website's network on every startup
(`app.deploy.service.reconnect_all_dynamic_websites`, called from a
FastAPI startup hook in `app/main.py`). This was discovered and fixed
during Phase 4 testing -- see the Testing section in the final report.

## Server restart behavior

- **Static websites**: just files on disk -- always available as soon
  as the backend container is up, no extra recovery step needed.
- **Dynamic websites**: containers are created with
  `restart_policy: unless-stopped`, so Docker itself restarts them
  after a host reboot (as long as the Docker daemon is set to start on
  boot, which is the normal Ubuntu Server configuration). Combined
  with the network-reconnection step above, a website that was
  `online` before a full server reboot comes back `online` afterward
  without any manual redeployment.
- A website a student explicitly `stop`ped stays stopped after a
  restart, since `unless-stopped` (deliberately, matching its name)
  does not restart a container that was intentionally stopped.

## Supported frameworks (recap)

Static: plain HTML/CSS/JS, built React/Vite output (`dist/`).
Dynamic: Flask, FastAPI, Node.js. Adding another framework later means
adding one detection rule (`app/deploy/detection.py`) and one
Dockerfile template (`app/deploy/builder.py`) -- nothing else in the
system needs to change.

## Known limitations (honest summary)

- No egress (outbound internet) restriction on dynamic containers.
- No job-queue persistence for in-flight background deployments (see
  above) -- a backend crash/restart mid-build loses that one
  deployment.
- No per-website disk quota enforcement beyond the ZIP/extracted-size
  checks at deploy time (a dynamic app could still grow its own
  container's writable layer at runtime, unbounded, since no
  `--storage-opt` size cap is applied -- Docker's default storage
  driver on most setups doesn't support one without extra host
  configuration).
- Multiple containers for the same website (e.g. blue/green
  deployments, zero-downtime redeploys) are not supported --
  redeploying means deleting and creating a new website.
- No custom domains, HTTPS, or public internet exposure -- explicitly
  out of scope for this phase.
- **Dynamic apps aren't path-prefix-aware.** `/apps/<slug>/...` is
  proxied straight to the container's own root path (`/...`), so if
  the deployed app itself emits root-relative links (e.g.
  `<link href="/static/style.css">` rather than a relative
  `style.css`), those will resolve against `/static/...` on DECP
  itself instead of the app's own container, and 404. This is the
  well-known "reverse proxy behind a path prefix" problem; static
  sites don't have it (see the trailing-slash fix above), but a
  dynamic framework's default static-file handling often assumes it's
  mounted at `/`. Workaround for now: configure the app's own static/
  asset URLs to be relative, or to respect a configurable base path,
  before deploying it to DECP.

## Future improvements

- A persistent job queue for deployments (removes the background-task
  limitation above) once/if deployment volume justifies the added
  infrastructure.
- Egress network policy for dynamic containers.
- Per-website disk quota enforcement at the container level.
- Additional frameworks (Django, Next.js, etc.) via the same
  detection + template pattern.
- Custom domains / `portfolio.decp.local`-style virtual hosting --
  the relative-`public_url` + backend-resolves-everything design in
  this phase was chosen specifically so this can be added later
  without restructuring the deployment system.
