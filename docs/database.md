# DECP Database & Authentication (Phase 2)

This document explains the `users` table and the authentication system
built on top of it, in beginner-friendly terms.

## The `users` table

| Column          | Type                          | Notes                                         |
|-----------------|-------------------------------|------------------------------------------------|
| `id`            | integer, primary key          | Auto-incrementing; uniquely identifies a user |
| `name`          | string                        | Required                                      |
| `roll_number`   | string, nullable              | **Unique** where set; optional (e.g. faculty/admin may not have one) |
| `email`         | string                        | **Unique**; used to log in                    |
| `password_hash` | string                        | Never the plaintext password -- see below     |
| `role`          | enum: `student`/`faculty`/`admin` | Defaults to `student`                     |
| `storage_limit` | integer (MB)                  | Not enforced yet -- reserved for the file storage phase |
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

The initial migration (`create users table`) was generated with
`alembic revision --autogenerate` and applied with `alembic upgrade
head` -- see the README for exact commands.

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

## What's intentionally not built yet

- Refresh tokens / token revocation (a logout only clears the token on
  the client -- the JWT itself remains technically valid until it
  expires, which is acceptable for this phase's short expiry window).
- Email verification, password reset, OAuth/social login.
- A full admin API for managing users, and the admin dashboard itself.
- Enforcement of `storage_limit` (no file storage exists yet).

These are all reasonable, separate future phases.
