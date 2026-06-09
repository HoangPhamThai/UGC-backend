# Roles & Permissions; Remove API Keys Module — Design

Date: 2026-06-09
Status: Proposed (revised)

> **Revision note.** A `qc_product` field is added to `User`. QCs are scoped to exactly one product (see `UGC/__documents__/roles.md` §3.1 and the workspaces spec). The product enum itself lives in the workspaces module (`app.modules.workspaces.data.model.Product`).

## Summary

Two related changes:

1. **Remove the `api_keys` module entirely**, including the `X-API-Key` authentication path in `core/auth.py`. After this change, JWT Bearer is the only authentication mechanism.
2. **Introduce four user roles** — `superuser`, `admin`, `qc`, `creator` — with a permission-scope model. Add a minimal set of admin-only user-management endpoints in a new `admin/` module. Bootstrap the first superuser from environment variables on startup.

## Motivation

- The `api_keys` module is unused and we want it gone, simplifying the auth surface to one path (Bearer JWT).
- The product needs distinct user types: creators produce content, QCs validate it, admins manage QCs and view creators, and a superuser manages everything. The current `User` model has no notion of role.

## Out of scope

- Content/QC workflow modules (this is foundation only).
- Promotion/demotion of users between roles. Role is immutable after creation.
- Hard deletion of users. Only soft-deactivate is supported.
- Automated tests. The project has no test framework today; introducing one is a separate decision.
- Automatic dropping of the `api_keys` Mongo collection. Documented as an ops step.

## Domain model

### `UserRole`

A `str, Enum` defined in `app/modules/users/data/model.py`:

```python
class UserRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    QC = "qc"
    CREATOR = "creator"
```

### `User`

The existing `User` Pydantic model in `app/modules/users/data/model.py` gains two new fields:

```python
from app.modules.workspaces.data.model import Product  # closed enum, see workspaces spec

role: UserRole = Field(default=UserRole.CREATOR, description="User role")
qc_product: Optional[Product] = Field(default=None, description="Product the QC is assigned to; required when role=qc, must be None otherwise")
```

`default=CREATOR` means self-registration does not need to specify a role, and any pre-existing user documents without a `role` field read as `creator` automatically.

### `qc_product` invariant

The model enforces a two-way relationship between `role` and `qc_product` via a Pydantic `model_validator`:

```python
@model_validator(mode="after")
def _check_qc_product(self) -> "User":
    if self.role == UserRole.QC and self.qc_product is None:
        raise ValueError("qc_product is required when role=qc")
    if self.role != UserRole.QC and self.qc_product is not None:
        raise ValueError("qc_product must be None when role is not qc")
    return self
```

This means:

- Creating any non-QC user with `qc_product` set → validation error (422).
- Creating a QC user without `qc_product` → validation error (422).
- A pre-existing user document whose role is `creator`/`admin`/`superuser` reads back as `qc_product=None` (default), so the invariant holds without a migration for non-QC rows. The workspaces module separately guards against a QC reaching its code path with `qc_product=None` via `QcMisconfiguredError` (a data-integrity 500).

### Import direction

`User` imports `Product` from `app.modules.workspaces.data.model`. If the team prefers `users` to be independent of `workspaces`, move `Product` to a shared location (e.g. `app/core/product.py`) and import from there in both modules. The workspaces spec also flags this option.

### `Permission`

A new enum in `app/core/permissions.py`:

```python
class Permission(str, Enum):
    USERS_CREATE_ADMIN   = "users:create:admin"
    USERS_CREATE_QC      = "users:create:qc"
    USERS_READ_ADMIN     = "users:read:admin"
    USERS_READ_QC        = "users:read:qc"
    USERS_READ_CREATOR   = "users:read:creator"
    USERS_UPDATE_ADMIN   = "users:update:admin"
    USERS_UPDATE_QC      = "users:update:qc"
    USERS_UPDATE_CREATOR = "users:update:creator"
```

### Role → permissions mapping

The single source of truth, also in `app/core/permissions.py`:

```python
ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.SUPERUSER: frozenset(Permission),  # all permissions
    UserRole.ADMIN: frozenset({
        Permission.USERS_CREATE_QC,
        Permission.USERS_READ_QC,
        Permission.USERS_READ_CREATOR,
        Permission.USERS_UPDATE_QC,
    }),
    UserRole.QC: frozenset({
        Permission.USERS_READ_CREATOR,
    }),
    UserRole.CREATOR: frozenset(),
}
```

This encodes the permission matrix:

| Action | Superuser | Admin | QC | Creator |
|---|---|---|---|---|
| Create/update/view admins | yes | no | no | no |
| Create/update/view QCs | yes | yes | no | no |
| View creators | yes | yes | yes | no |
| Update/deactivate creators | yes | no | no | no |
| Read/update own profile (`/users/me`) | yes | yes | yes | yes |

## RBAC enforcement

A dependency factory in `app/core/permissions.py`:

```python
def require_permissions(*needed: Permission):
    def dep(user: User = Depends(get_current_user)) -> User:
        granted = ROLE_PERMISSIONS[user.role]
        if not all(p in granted for p in needed):
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dep
```

For endpoints where the required permission depends on the **target** user's role (e.g., `GET /admin/users/{id}`), the handler/usecase resolves the target first, then derives the required permission (`users:read:{target.role}`) and checks it against the caller's granted set explicitly.

## API surface

### Auth (`/api/v1/auth`, unchanged externally)

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/auth/register` | none (public) | Internally always sets `role=creator`. Body and response unchanged. |
| `POST` | `/auth/login` | none | Unchanged. |
| `POST` | `/auth/refresh` | none | Unchanged. |
| `POST` | `/auth/logout` | Bearer | Unchanged. |

### Users (`/api/v1/users`, unchanged)

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/users/me` | Bearer | Response includes the user's `role`. |

### Admin (`/api/v1/admin`, new module)

All endpoints require Bearer auth. Permission checks per row.

| Method | Path | Permission(s) | Body / Query | Behavior |
|---|---|---|---|---|
| `POST` | `/admin/users` | `users:create:admin` for `role=admin`; `users:create:qc` for `role=qc` | `{email, password, role, qc_product?}` | Create an admin or QC. Rejects `role` of `creator` or `superuser` with 400. `qc_product` is required when `role=qc`, must be omitted/null otherwise — enforced by the model validator (returns 422 on violation). Returns the created user (id, email, role, qc_product, is_active, created_at). |
| `GET` | `/admin/users` | `users:read:{role}` for the requested `?role=` value | Query: `?role=admin\|qc\|creator` (required), `?page`, `?page_size` | List users of a given role. 403 if the caller lacks the corresponding read permission. Paginated. The QC list includes each user's `qc_product`. |
| `GET` | `/admin/users/{user_id}` | `users:read:{target.role}` | — | Fetch one user by id. 404 if not found. 403 if caller lacks read permission for the target's role. Response includes `qc_product` when the target is a QC. |
| `PATCH` | `/admin/users/{user_id}` | `users:update:{target.role}` | `{is_active?, password?, qc_product?}` | Partial update. `role` is intentionally not mutable. Setting `is_active=false` is the soft-deactivate path. `qc_product` may only be changed for a target whose `role=qc`; supplying it for any other role returns 400. Changing a QC's `qc_product` is the supported way to reassign them (see `roles.md` §3.1 — past review history is preserved on the article, the QC simply stops seeing the old product going forward). |

### Removed

- All `/api/v1/api-keys/*` endpoints.

## Removal of the `api_keys` module

- Delete `app/modules/api_keys/` (entire directory).
- In `app/app.py`: remove the `api_keys_router` import and the `app.include_router(api_keys_router, ...)` line.
- In `app/core/auth.py`: simplify `get_current_user` to JWT-only. Remove `_resolve_from_api_key`, the `X-API-Key` header read, the dual-header rejection branch, and the imports of `hash_api_key` / `ApiKeyDataRepository`.
- In `app/core/security.py`: delete `generate_api_key()` and `hash_api_key()`. Both have no other callers once `core/auth.py` is updated.
- The `api_keys` Mongo collection is left in place by the application. Ops step (documented, not automated): `db.api_keys.drop()`.

## Superuser bootstrap

### Settings

`app/core/settings.py` gains two optional fields:

```python
superuser_email: EmailStr | None = None
superuser_password: str | None = None
```

### Use case

`app/modules/users/domain/usecases/bootstrap_superuser.py` — idempotent:

1. Check whether **any** user with `role=superuser` already exists. If yes, log info and return.
2. If no superuser exists and both env vars are set:
   - If a user with that email already exists but has a non-superuser role → log error, do **not** modify, do not raise.
   - Otherwise, create a new user with `role=superuser`, `is_active=true`, password bcrypt-hashed.
3. If no superuser exists and env vars are missing or partial → log a warning ("no superuser exists and `SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD` not set") and return. Do **not** raise; the app must still boot in dev without these set.

### Repo addition

`UserRepo` gets one new method:

```python
async def exists_with_role(self, role: UserRole) -> bool: ...
```

implemented in `UserDataRepository` as a single-document existence query (`find_one({"role": role.value}, projection={"_id": 1})`). Avoids loading users into memory.

### Wiring

`app/app.py` `lifespan` calls the bootstrap use case immediately after `mongo_connection.connect()`.

## Module layout

```
app/
  app.py                              # remove api_keys_router; call bootstrap in lifespan
  core/
    auth.py                           # Bearer-only
    permissions.py                    # NEW: Permission enum, ROLE_PERMISSIONS, require_permissions()
    security.py                       # drop generate_api_key, hash_api_key
    settings.py                       # add superuser_email, superuser_password
  modules/
    admin/                            # NEW
      __init__.py
      domain/
        __init__.py
        usecases/
          __init__.py
          create_managed_user.py      # create admin/QC
          list_users_by_role.py
          get_user_by_id.py
          update_managed_user.py
      presentation/
        __init__.py
        deps.py
        routes.py
        schema.py
    api_keys/                         # DELETED
    auth/
      domain/usecases/register.py     # hard-codes role=CREATOR
    users/
      data/model.py                   # add UserRole; add role field
      data/repo.py                    # add exists_with_role
      domain/repo.py                  # add exists_with_role
      domain/usecases/
        create_user.py                # add role parameter
        bootstrap_superuser.py        # NEW
      presentation/schema.py          # UserMeResponse includes role
```

## Migration steps (ops, documented)

After deploy:

```js
// 1. Backfill role for any pre-existing user docs.
db.users.updateMany(
  { role: { $exists: false } },
  { $set: { role: "creator" } }
);

// 2. Backfill qc_product for any pre-existing non-QC user docs (no-op on QC rows,
//    which will be created fresh through the admin endpoint with the field set).
db.users.updateMany(
  { qc_product: { $exists: false } },
  { $set: { qc_product: null } }
);

// 3. Drop the now-unused collection.
db.api_keys.drop();
```

Set `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` in the deployment environment before first boot; otherwise the startup warning will fire and no superuser will exist.

## Manual verification

After implementation, smoke-check via curl against a running app:

1. `POST /auth/register` succeeds, response shows the user is created. (No role echoed at this endpoint.)
2. `POST /auth/login` with the registered creator → tokens returned.
3. `GET /users/me` with the access token → `role: "creator"` in response.
4. `GET /admin/users?role=qc` as the creator → 403.
5. Restart app with `SUPERUSER_EMAIL`/`SUPERUSER_PASSWORD` set; log shows "superuser bootstrapped". Restart again; log shows "superuser already exists" (idempotency).
6. Log in as the superuser; `POST /admin/users` with `{role: "admin", ...}` → 201. `POST /admin/users` with `{role: "creator", ...}` → 400.
7. Log in as the new admin; `POST /admin/users` with `{role: "qc", qc_product: "CL", ...}` → 201. Same call with `{role: "qc", ...}` (no `qc_product`) → 422. Same call with `{role: "qc", qc_product: "NOTAPRODUCT"}` → 422. Same call with `{role: "admin", ...}` → 403.
8. As the admin, `PATCH /admin/users/{qc_id}` with `{qc_product: "FD"}` → 200; subsequent `GET` confirms the change. `PATCH` with `{qc_product: "CL"}` on a non-QC user → 400.
9. As the admin, `GET /admin/users?role=creator` → 200 (read-only). `PATCH /admin/users/{creator_id}` with `is_active=false` → 403. `PATCH .../qc_product` on a creator → 400.
10. As the superuser, `PATCH /admin/users/{creator_id}` with `is_active=false` → 200. The deactivated creator's next `POST /auth/login` → 401.
11. `GET /api/v1/api-keys` → 404 (route removed).

## Risks and rollback

- **Risk:** existing user docs without `role` field. **Mitigation:** Pydantic default, plus documented one-liner backfill. Reads are safe either way.
- **Risk:** consumers depending on the `X-API-Key` header. **Mitigation:** confirmed no such consumers exist for this backend; if discovered post-deploy, rolling back requires reverting this change.
- **Risk:** misconfigured `SUPERUSER_EMAIL` colliding with an existing non-superuser account. **Mitigation:** bootstrap logs an error and refuses to modify the existing user. Ops can resolve manually.
- **Rollback:** git revert. The `api_keys` collection still exists in Mongo (we never dropped it automatically), so a revert restores prior behavior without data loss.
