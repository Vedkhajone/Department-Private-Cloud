# DECP Database, Authentication & Storage

This document explains the database tables, the authentication system,
and personal cloud storage, in beginner-friendly terms.

**A key distinction used throughout this document:** PostgreSQL never
stores file *contents* -- only *metadata* (names, folder structure,
size, ownership). The actual bytes of every uploaded file live on the
filesystem. See "Personal cloud storage" below.

## The `users` table

| Column          | Type                          | Notes                                         |
|-----------------|-------------------------------|------------------------------------------------|
| `id`            | integer, primary key          | Auto-incrementing; uniquely identifies a user |
| `name`          | string                        | Required                                      |
| `roll_number`   | string, nullable              | **Unique** where set; optional (e.g. faculty/admin may not have one) |
| `email`         | string                        | **Unique**; used to log in                    |
| `password_hash` | string                        | Never the plaintext password -- see below     |
| `role`          | enum: `student`/`faculty`/`admin` | Defaults to `student`                     |
| `storage_limit` | integer (MB)                  | The user's personal storage quota, enforced on every upload (see below) |
| `is_active`     | boolean                       | Added in Phase 5; admin-controlled account enable/disable -- see below |
| `created_at`    | timestamp (with timezone)     | Set automatically on insert                   |

**Primary key**: `id`, a plain auto-incrementing integer. It's simple,
efficient for foreign keys future tables will need (e.g. "which user
owns this project"), and doesn't leak information the way, say, an
email-as-primary-key would.

**Why email is unique**: a user logs in with their email, so two
accounts sharing an email would make login ambiguous. The database
enforces this with a `UNIQUE` constraint -- even a race condition (two
registration requests at the same instant) can't create a duplicate,
because Postgres itself rejects the second insert.

**Why roll_number is unique but nullable**: students have a roll
number and it must be unique among students, but the column doesn't
belong to students only at the table level -- faculty/admin accounts
simply leave it empty. A `UNIQUE` constraint on a nullable column
still enforces "no two *non-null* values are the same," which is what
we want.

**Why role defaults to `student`**: the public `/api/auth/register`
endpoint never reads a `role` field from the request at all -- it's
hardcoded to `UserRole.student` in the backend. There is no way to
register as `faculty` or `admin` through the public API; those roles
can only be assigned directly (e.g. by an administrator working
directly with the database), which is intentional until a real admin
API exists.

## The `folders` table

| Column             | Type                    | Notes |
|--------------------|-------------------------|-------|
| `id`               | integer, primary key    | |
| `user_id`          | integer, FK → `users.id` | Owner; every query filters on this |
| `parent_folder_id` | integer, FK → `folders.id`, nullable | `NULL` means "at the user's root" |
| `name`             | string                  | Unique within the same user + parent (enforced by two database indexes -- see below) |
| `created_at`, `updated_at` | timestamp (with timezone) | |

Folders are a **purely logical/database concept** -- creating a folder
does not create a directory on disk. Only `File.folder_id` (and
`Folder.parent_folder_id` for nesting) records which folder something
is "in." See "Personal cloud storage" below for why.

**Preventing duplicate names:** a user can't have two folders with the
same name in the same parent. This is enforced by the database itself
(not just application code), via two indexes:
`ix_folders_user_parent_name` (a normal unique index on `user_id`,
`parent_folder_id`, `name`) plus `ix_folders_user_root_name` (a
*partial* unique index on `user_id`, `name` that only applies `WHERE
parent_folder_id IS NULL`). The second index exists because SQL
treats every `NULL` as distinct from every other `NULL` -- without it,
a plain unique index would silently allow duplicate names at the root
level. `files` has the identical pair of indexes for the same reason.

**Deleting a folder:** the API refuses to delete a folder that still
contains files or subfolders (`409 Conflict`) rather than silently
cascading. This is a deliberate safety choice -- accidentally deleting
a folder should not be able to take an entire tree of files with it.

## The `files` table

| Column          | Type                     | Notes |
|-----------------|--------------------------|-------|
| `id`            | integer, primary key     | |
| `user_id`       | integer, FK → `users.id` | Owner |
| `folder_id`     | integer, FK → `folders.id`, nullable | `NULL` means "at the user's root" |
| `name`          | string                   | The display name shown in the UI |
| `storage_path`  | string, unique           | Server-generated identifier for the file *on disk* -- see below |
| `size`          | bigint                   | Bytes; used to calculate quota usage |
| `mime_type`     | string, nullable         | From the upload's Content-Type |
| `created_at`, `updated_at` | timestamp (with timezone) | |

`name` and `storage_path` are deliberately independent: `name` is
whatever the user sees and can rename freely; `storage_path` is a
random identifier (a UUID) chosen by the server when the file is
uploaded, and never changes. This is what makes renaming instant (only
the database row changes) and is also a core security measure -- see
"Personal cloud storage" below.

## SQLAlchemy

SQLAlchemy is the library that lets the Python backend describe the
`users` table as a normal Python class (`app/models/user.py`) and work
with rows as objects, instead of writing raw SQL everywhere. It also
manages the connection to Postgres (`app/db/database.py`) and,
combined with Alembic, keeps the database schema in sync with that
class definition.

## Alembic (migrations)

A **migration** is a small, version-controlled script that describes
one schema change (e.g. "create the `users` table"). Alembic:

1. Compares the SQLAlchemy models against the current database schema.
2. Generates a migration script describing the difference.
3. Applies migration scripts in order, tracking which ones have already
   run (in a table called `alembic_version`), so re-running is safe.

This matters for two reasons:

- **Reproducibility** — anyone (including the department server) can
  get an identical schema by running `alembic upgrade head`, instead of
  relying on the app creating tables ad hoc on startup.
- **History** — every schema change is a file in
  `backend/alembic/versions/`, so you can see exactly how the database
  evolved, and roll a change back if needed.

Four migrations exist so far: `create users table` (Phase 2), `add
folders and files tables` (Phase 3), `add websites table` (Phase 4),
and `add admin dashboard: audit_logs, system_metrics, users.is_active`
(Phase 5). Each was generated with `alembic revision --autogenerate`
and applied with `alembic upgrade head` -- see the README for exact
commands. Each new migration only adds its own tables/columns; none of
them modify an earlier migration's own changes (the Phase 5 migration
adds a column to the existing `users` table, which is expected --
Alembic captures that as `users.is_active`, cleanly separate from
what the `create users table` migration itself does).

## Password hashing

Passwords are **hashed**, never encrypted or stored as-is. Hashing is
one-way: there's no way to recover the original password from the
hash, only to check whether a given password produces the same hash.

This project uses [`pwdlib`](https://pypi.org/project/pwdlib/) with
**Argon2** (`PasswordHash.recommended()`), a modern, memory-hard
hashing algorithm designed specifically to make large-scale password
cracking (e.g. after a database leak) slow and expensive.

```
Register:  plaintext password → hash_password() → password_hash column
Login:     plaintext password + stored password_hash → verify_password() → bool
```

The plaintext password only ever exists in memory for the duration of
the request that receives it -- it is never written to the database,
logged, or included in any API response. API responses use the
`UserOut` schema, which has no `password_hash` field at all, so it's
structurally impossible for an endpoint built on it to leak a hash.

## JWT (JSON Web Tokens) and the authentication flow

On successful login, the backend issues a **JWT** -- a signed, compact
token the client can present on later requests instead of resending a
password every time.

```
{
  "sub": "1",              <- the user's id
  "role": "student",       <- the user's role (avoids a DB lookup for
                                role checks on every request)
  "iat": 1699999999,       <- issued-at time
  "exp": 1700003599        <- expiry time
}
```

The token is signed with a secret key (`JWT_SECRET`, set only via
environment variables, never hardcoded) using HMAC-SHA256. Signing
means the token's contents can't be modified by the client without
invalidating the signature -- the backend can trust `sub` and `role`
on any token it successfully verifies.

**Request flow:**

1. Client sends `Authorization: Bearer <token>` with a request.
2. The `get_current_user` FastAPI dependency verifies the signature and
   expiry (`decode_access_token`). An invalid or expired token is
   rejected with `401 Unauthorized` before any endpoint code runs.
3. The user id (`sub`) is used to load the user from the database.
4. The endpoint receives the authenticated `User` object as a normal
   function argument.

**Role-based access control:** `require_role(*roles)` wraps
`get_current_user` and additionally checks the user's `role` against an
allowed set, returning `403 Forbidden` otherwise. `GET
/api/users/staff-only` demonstrates this (faculty/admin only) -- it's a
placeholder to prove the mechanism works, not a real feature.

## Personal cloud storage

**Metadata vs. file contents, concretely:** when a user uploads
`essay.docx`, PostgreSQL gets a new row in `files` (`name`,
`folder_id`, `size`, `storage_path`, ...); the actual bytes of
`essay.docx` are written to a file on the filesystem, under the
directory configured by `STORAGE_ROOT`. Nothing about the file's
content ever passes through PostgreSQL.

**Where uploads are stored on disk:**

```
STORAGE_ROOT/users/<user_id>/<random-uuid>
```

Every user gets one flat directory (no per-folder subdirectories --
folder structure is metadata-only, see the `folders` table above).
Every file inside it is named with a random UUID generated by the
server at upload time (`app/storage/paths.py:new_storage_filename`)
-- never the file's original name.

**Why the on-disk filename is never the display name:** if the
physical filename came from user input, a filename like
`../../../etc/passwd` or one containing OS-specific special characters
would need very careful handling to avoid writing outside the
intended directory (a "path traversal" vulnerability). By always using
a server-generated UUID instead, there is no user-controlled string in
the path at all -- traversal isn't blocked by validation, it's
structurally impossible. (The display name is *still* validated --
see `sanitize_name` in `app/storage/service.py` -- mainly to keep it
sane for the UI and reject anything that looks like a path, as
defense in depth.)

**Docker persistence:** `docker-compose.yml` mounts a host directory
(`STORAGE_HOST_PATH`) into the backend container at `STORAGE_ROOT`
(`/cloud-data`), the same pattern used for the Postgres volume. Files
are never written inside the container's own filesystem or the Docker
image, so `docker compose down` / `up` and container restarts don't
lose them. Moving to the department server is a one-line change:
set `STORAGE_HOST_PATH` in `.env` to wherever files should live there
(e.g. `/cloud-data`).

**Upload flow and failure handling:**

```
1. Verify the target folder (if any) belongs to the current user.
2. Validate and check the display name isn't already used here.
3. Check remaining quota (quota_bytes - used_bytes).
4. Stream the upload to disk in 1MB chunks (never fully buffered in
   memory), aborting if it would exceed the remaining quota.
5. Insert the files row.
6. If anything from step 4 onward fails, delete the (possibly
   partial) physical file -- never leave an orphaned file with no
   database row, or vice versa.
```

Deletion works in the safer order for consistency: the database row is
removed first (and committed), then the physical file is removed. If
step two somehow fails, the result is an orphaned file on disk
(harmless, cleanable later) rather than a database row pointing at a
file that no longer exists (which would break downloads with a
confusing error).

**Quota:** `quota_bytes = users.storage_limit * 1024 * 1024`. Usage is
calculated on demand as `SUM(files.size)` for the user -- acceptable
at this phase's scale; a running counter can be introduced later if
recalculating on every request becomes a bottleneck. The default quota
for new registrations is set via the `DEFAULT_STORAGE_QUOTA_BYTES`
environment variable (see `.env.example`).

**Ownership on every operation:** every folder/file endpoint calls a
`get_owned_folder` / `get_owned_file` helper that filters by *both*
the row's id *and* `user_id == current_user.id` in the same database
query -- there's no separate "fetch, then check ownership" step where
a check could be forgotten. A file/folder belonging to another user
looks exactly like one that doesn't exist (`404`), so the API never
confirms or denies another user's file exists.

## The `websites` table

| Column          | Type                                                 | Notes |
|-----------------|-------------------------------------------------------|-------|
| `id`            | UUID, primary key                                      | Unlike other tables, a UUID -- website ids are exposed in the API/URLs, so a non-sequential id is preferable |
| `owner_id`      | integer, FK → `users.id`                                | Always the authenticated user; never client-supplied |
| `name`          | string                                                   | Display name the student chose |
| `slug`          | string, unique                                            | URL-safe identifier, always server-generated from `name` -- see below |
| `type`          | enum: `static` / `dynamic`                                 | |
| `framework`     | enum: `html` / `react` / `flask` / `fastapi` / `node`        | |
| `status`        | enum: `pending`/`building`/`online`/`stopped`/`failed`/`deleting` | |
| `storage_path`  | string, nullable                                            | Relative identifier under `STORAGE_ROOT/websites/<owner_id>/` |
| `container_id`  | string, nullable                                              | Dynamic websites only |
| `internal_port` | integer, nullable                                              | The fixed port the app listens on *inside* its container (never published to the host) |
| `public_url`    | string, nullable                                                | Relative path, e.g. `/sites/my-portfolio` -- never a hardcoded host |
| `error_message` | text, nullable                                                   | Set when `status = failed`, explaining why |
| `created_at`, `updated_at` | timestamp (with timezone)                             | |

**Why `slug` is always server-generated:** a client never supplies a
slug directly -- it's derived from `name` (lowercased, non-alphanumeric
characters replaced with `-`) and checked for uniqueness, appending a
short random suffix on collision (`app/deploy/slug.py`). This is what
guarantees a slug can never be used for path traversal or to collide
with a route the app itself owns (a small reserved list -- `api`,
`sites`, `apps`, etc. -- is rejected and suffixed too).

**Why `owner_id` is trustworthy:** exactly like `folders`/`files`, it's
set from the authenticated JWT user on the server side -- the deploy
endpoint has no `owner_id` field a client could populate, so "a student
deploys a website as someone else" is not expressible through the API.

See [`docs/WEBSITE-HOSTING.md`](./WEBSITE-HOSTING.md) for the full
deployment architecture, Docker isolation model, and NGINX routing
built on top of this table.

## The `audit_logs` table (Phase 5)

| Column          | Type                          | Notes |
|-----------------|-------------------------------|-------|
| `id`            | integer, primary key          | |
| `actor_id`      | integer, FK → `users.id`, nullable | Who did it; `NULL` for a few actor-less events (e.g. a failed login against an unknown email) |
| `action`        | string                        | A short fixed code, e.g. `website.deploy`, `file.delete` |
| `resource_type` | string, nullable              | e.g. `website`, `file`, `folder`, `user` |
| `resource_id`   | string, nullable              | The affected row's id (kept as text since ids vary in type -- integer for users/files, UUID for websites) |
| `description`   | text, nullable                | Human-readable summary shown in the admin UI |
| `ip_address`    | string, nullable              | Captured where cheap to (register/login); `NULL` elsewhere |
| `created_at`    | timestamp (with timezone)     | |

Answers "who did what" -- see
[`docs/ADMIN-DASHBOARD.md`](./ADMIN-DASHBOARD.md) for exactly which
actions are recorded and why, and for the guarantee that a row can
never contain a password, JWT, or file content (there's exactly one
function that writes this table, and none of its call sites ever pass
those values to it).

## The `system_metrics` table (Phase 5)

| Column             | Type                     | Notes |
|--------------------|--------------------------|-------|
| `id`               | integer, primary key     | |
| `timestamp`        | timestamp (with timezone)| When this sample was taken |
| `cpu_percent`      | float                    | |
| `memory_percent`   | float                    | |
| `disk_percent`     | float                    | Of the filesystem backing `STORAGE_ROOT` |
| `network_rx_bytes` | bigint                   | Cumulative bytes received since boot |
| `network_tx_bytes` | bigint                   | Cumulative bytes sent since boot |

Answers "what was the server doing at time T" -- no per-user or
per-action information lives here (that's `audit_logs`). A background
task takes one sample per `METRICS_SAMPLE_INTERVAL_SECONDS` (default
60s) and prunes rows older than `METRICS_RETENTION_DAYS` (default 14
days) -- see `docs/ADMIN-DASHBOARD.md`, "Server health & metrics."

## What's intentionally not built yet

- Refresh tokens / token revocation (a logout only clears the token on
  the client -- the JWT itself remains technically valid until it
  expires, which is acceptable for this phase's short expiry window).
- Email verification, password reset, OAuth/social login.
- Moving/copying a file or folder between folders (rename only, for now).
- Recursive folder deletion (deleting a non-empty folder is refused
  rather than silently deleting everything inside it).
- A materialized/cached storage usage counter (currently recalculated
  from `files.size` on every request).
- Persistent/queued background deployments -- a backend restart mid-
  build loses that one in-flight deployment (see WEBSITE-HOSTING.md).
- Egress network restrictions and per-container disk quotas for
  dynamic websites (see WEBSITE-HOSTING.md's "Known limitations").

These are all reasonable, separate future phases.
