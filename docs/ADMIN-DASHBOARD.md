# DECP Admin Dashboard (Phase 5)

This document explains the Admin & System Management Dashboard: how
it's structured, secured, and where every number it shows actually
comes from.

## What it is

A separate console, visible only to `role = admin` accounts, giving a
department administrator one place to see and manage what's running
across DECP: users, storage, hosted websites, server health, and an
audit trail of who did what. It uses the exact same backend
(FastAPI + PostgreSQL + Docker) and the same visual language as the
student dashboard -- there is no separate admin service or database.

## Routing: how a user reaches it

There's no separate `/admin` URL path -- `App.tsx` renders `<AdminApp
/>` instead of the student `<Dashboard />` when the authenticated
user's `role` is `admin`, decided purely by what the browser already
knows about the logged-in user. **This is a UI convenience only, never
a security boundary.** Every `/api/admin/*` route independently
re-checks the role on the backend (see "Security" below) -- a student
who somehow rendered the admin UI (they can't, but hypothetically)
would still get `403` from every API call it makes.

## Admin API structure

All under `/api/admin/`, added in `app/api/admin.py`:

```
GET    /api/admin/overview
GET    /api/admin/users
GET    /api/admin/users/{id}
PATCH  /api/admin/users/{id}/role
PATCH  /api/admin/users/{id}/active
GET    /api/admin/storage
GET    /api/admin/websites
GET    /api/admin/websites/{id}
POST   /api/admin/websites/{id}/stop
POST   /api/admin/websites/{id}/restart
DELETE /api/admin/websites/{id}
GET    /api/admin/websites/{id}/logs
GET    /api/admin/system
GET    /api/admin/metrics?range=1h|24h|7d|30d
GET    /api/admin/containers
GET    /api/admin/containers/{id}/logs
GET    /api/admin/audit-logs
GET    /api/admin/audit-logs/{id}
```

Business logic lives in `app/admin/service.py` (the router stays a
thin HTTP adapter, the same layering used everywhere else in the
backend -- see `docs/architecture.md`).

## Security (RBAC)

```
JWT → get_current_user → require_admin (role == admin) → endpoint
```

`app/auth/dependencies.py` adds `require_admin`, a named alias for
`require_role(UserRole.admin)` -- the exact same mechanism that
already protected `/api/users/staff-only` in Phase 2. The entire
`admin.router` in `app/api/admin.py` carries `require_admin` as a
**router-level** dependency, so it's applied to every route on it
automatically -- there's no route in the file that could accidentally
be added without it.

Never trusted from the client:
- **Role.** The dashboard the frontend renders is decided by the
  `role` already embedded in the user object fetched from
  `/api/users/me` -- there is no request in this codebase that lets a
  client claim a role.
- **User id for admin actions.** Every admin endpoint that acts on
  another user (`GET/PATCH /admin/users/{id}`, website actions) takes
  the target id from the URL path and looks it up directly; the
  *acting* user is always the one identified by the JWT
  (`require_admin`'s return value), never anything supplied in the
  request body.

Self-protection:
- An admin **cannot** change their own role
  (`app/admin/service.py:change_user_role`) or disable their own
  account (`change_user_active`) -- both return `400` if
  `actor.id == target_user_id`. This prevents an accidental
  self-lockout with no other admin to undo it.

Account disabling takes effect immediately:
- `get_current_user` (the dependency every authenticated route
  depends on, including every non-admin one) now also checks
  `user.is_active` and returns `403` if false -- so disabling an
  account blocks it on the very next request, not just the next login.
  Login itself also checks this and returns a clear message rather
  than the generic "incorrect password."

## What the admin UI can never see or do

- **No password or password hash** -- every admin schema
  (`app/schemas/admin.py`) is built by hand from specific fields; none
  of them include `password_hash`, and there is no endpoint that
  returns a `User` ORM object directly.
- **No JWT secret / `.env` contents** -- nothing in `app/api/admin.py`
  or `app/admin/service.py` reads environment variables and returns
  them; `settings.jwt_secret` is never referenced from any admin code
  path.
- **No arbitrary filesystem access** -- there is no path parameter
  anywhere in the admin API. Storage numbers come from SQL aggregates
  (`SUM(files.size)`) and `shutil.disk_usage(settings.storage_root)` --
  a single fixed, server-controlled path, never client input.
- **No arbitrary Docker container access** -- `GET
  /admin/containers/{id}/logs` only works for containers DECP itself
  created (name prefix `decp-site-`, enumerated via
  `app/deploy/containers.py:list_managed_containers`); an id for any
  other container returns "(container no longer exists)" rather than
  leaking anything about it. There is no `docker exec`/`docker
  run`/arbitrary-command endpoint anywhere -- container "actions" are
  exactly the three verbs already used for student-owned dynamic
  websites (stop/restart/logs), reusing the same
  `app/deploy/containers.py` functions Phase 4 already hardened.
- **No Docker socket in the browser** -- unchanged from Phase 4:
  `/var/run/docker.sock` is mounted only into the `backend` container;
  the admin UI talks to the backend over the same authenticated REST
  API as everything else, never to Docker directly.

## Server health & metrics

`app/admin/metrics.py`, using [`psutil`](https://pypi.org/project/psutil/)
(a well-established, read-only OS stats library -- no shelling out, no
reading arbitrary `/proc` files by hand):

| Metric | Source |
|---|---|
| CPU % | `psutil.cpu_percent()` |
| Memory % / total / used | `psutil.virtual_memory()` |
| Disk % / total / used | `psutil.disk_usage(settings.storage_root)` |
| Network received/sent | `psutil.net_io_counters()` (cumulative since boot) |
| Uptime | Time since this backend process started (not host uptime) |

**Live snapshot** (`GET /admin/system`) also runs the same service
health checks as the overview (see below).

**History for the graphs** (`GET /admin/metrics?range=...`): a
background asyncio task (`start_sampler`, launched once from a FastAPI
startup hook in `app/main.py`) takes one sample every
`METRICS_SAMPLE_INTERVAL_SECONDS` (default 60s) and writes it to the
`system_metrics` table, then prunes anything older than
`METRICS_RETENTION_DAYS` (default 14 days) in the same pass -- a small,
self-contained mechanism, not a monitoring stack. A failed sample is
logged and skipped; the loop never dies from one bad iteration (the
graph simply has a gap for that interval).

**Time ranges**: only `1h` / `24h` / `7d` / `30d` are accepted -- these
map directly to a `WHERE timestamp >= now() - interval` query against
real stored samples. There is no synthetic/interpolated data; a range
with fewer samples than expected (e.g. right after the backend starts)
just shows fewer points, with the chart saying "Not enough data yet"
if there are none.

**Auto-refresh**: the dashboard overview and system page each poll
their own summary endpoint independently (every 30s and 15s
respectively) -- never the whole page, and never more than the one
endpoint each view actually needs.

## Service health checks (real, not hardcoded)

`app/admin/service.py:check_services` — every check is a real,
independent probe with a timeout:

| Service | Check |
|---|---|
| API | Trivially healthy -- this code is running |
| Database | `SELECT 1` round-trip through the actual SQLAlchemy session |
| NGINX | `GET http://nginx/api/health` over the Docker network, 2s timeout |
| Docker | `docker_client.ping()` |
| Storage | `shutil.disk_usage(STORAGE_ROOT)` succeeds |

Any of these can independently report `unavailable` -- verified during
testing (see the final report's Tests section) by confirming the
response actually reflects a real probe result, not a hardcoded list.

## Storage reporting

`GET /admin/storage`: `used_bytes` is `SUM(files.size)` across every
user (the same real data personal storage already tracks -- see
`docs/database.md`); `capacity_bytes` is the actual total size of the
disk backing `STORAGE_ROOT` (`shutil.disk_usage`). These answer two
different, both-honest questions: "how much of the department's
tracked file storage is used" vs. "how much physical disk is there" --
documented explicitly here since the two are related but not identical
(the disk also holds Postgres data, the OS, Docker images, etc.).

Health thresholds (`STORAGE_WARNING_PERCENT` / `STORAGE_CRITICAL_PERCENT`,
default 70% / 85%) are configurable via `.env`. **Nothing is ever
auto-deleted** when a threshold is crossed -- it's a UI signal only.

"Top storage users" is a real `GROUP BY user_id, SUM(size)` query
against the `files` table, not sample/fake data.

## Audit logging

Answers "who did what," stored in a new `audit_logs` table
(`app/models/audit_log.py`). Every row is written through exactly one
function, `app/admin/audit.py:record` -- the single write path, which
is what makes it possible to guarantee a row can never end up holding
a password, JWT, or file content: those values simply never reach that
function's call sites (listed below).

**Recorded today:**

| Action | Where |
|---|---|
| `auth.register` | `api/auth.py` |
| `auth.login_success` / `auth.login_failure` | `api/auth.py` |
| `file.upload` / `file.delete` | `storage/service.py` |
| `folder.create` / `folder.delete` | `storage/service.py` |
| `website.deploy` / `website.delete` / `website.restart` / `website.stop` | `deploy/service.py` (student actions) and `admin/service.py` (admin-initiated) |
| `admin.role_change` / `admin.account_status_change` | `admin/service.py` |

**Deliberately not logged**: routine reads (listing files, viewing a
dashboard), renames, folder navigation -- useful auditing, not noise,
per the brief.

Every write is best-effort and isolated: `record()` commits in its own
try/except, so a logging hiccup can never fail the real operation it
describes, and a failure in the real operation can't silently corrupt
the audit trail either.

**Filtering & pagination** (`GET /admin/audit-logs`): by actor, action,
and a time range (`24h`/`7d`/`30d`), paginated (`page`/`page_size`, max
200 per page) -- the browser never receives more than one page of rows
at once.

## Containers

`GET /admin/containers` lists only containers DECP itself created for
dynamic websites (name prefix `decp-site-`) -- never arbitrary host
containers, and never the DECP core containers themselves (backend/
nginx/postgres aren't exposed as "manageable" here, only their health
status via `/admin/system`). Each entry's CPU/memory numbers come from
a live, non-streaming `docker stats` snapshot per container
(`app/deploy/containers.py:container_stats`) -- a stopped container
reports zeroed usage rather than an error, since that's simply its
real, healthy state.

## Enable/disable and role change

Added a real `is_active` column to `users` (previously assumed always
true). Both actions go through the same DB session/commit/audit
pattern as everything else, are blocked for self-modification (see
"Security" above), and take effect immediately -- see "Account
disabling" above.

## Auto-refresh, not polling everything

Per the brief's performance guidance: the dashboard never calls more
than the handful of summary endpoints each view actually needs, and
none of them poll faster than 15s. There is no endpoint that returns
every database record at once -- users, websites, and audit logs are
all paginated server-side.

## Known limitations (honest)

- **No total-server metrics history before this phase shipped** -- the
  `system_metrics` table starts empty; historical graphs fill in over
  time from when the backend first runs this code, they don't
  retroactively reconstruct the past.
- **Metrics sampling runs in-process** -- like the Phase 4 background
  deployment task, if the backend process restarts, the *next* sample
  simply happens on the next interval; no sample is lost mid-write,
  but this is not a durable, external monitoring pipeline (Prometheus-
  style), by design (the brief explicitly asks not to add one at this
  scale).
- **Container CPU/memory stats add a small per-container latency** --
  each one is a live Docker API call; fine at current department
  scale, would need batching/caching if the number of concurrent
  dynamic websites grows much larger.
- **No "server logs" viewer beyond container logs and the audit
  trail** -- a general application/NGINX log aggregator was not built;
  admins get container-level logs (for dynamic websites) and the audit
  log (for user actions), which covers the brief's "who did what" /
  "what happened technically" split at this project's current scale.
- **Uptime shown is the backend process's uptime**, not the host
  machine's -- `psutil.boot_time()` would give host uptime but wasn't
  wired in; noted here rather than silently conflating the two.

## Future improvements

- A durable, queryable application log stream (would likely mean
  adding a modest log-shipping step, not a full ELK stack, when the
  need is demonstrated).
- Per-service (not just per-container) resource history.
- Configurable alert thresholds beyond the storage warning/critical
  levels already in place.
