# UGC Backend — HTTP API Reference

This document is the authoritative HTTP contract for frontend integration. It covers every public endpoint of the backend: authentication, the current-user endpoint, admin user management, and the workspaces module (workspaces + articles).

> **Terminology change from the original frontend spec:** the unit of content that was called *tab* in `frontend/__plans__/workspace/apis.md` is now **`article`** (Vietnamese: *bài viết*) everywhere — in URLs, payloads, and identifiers. ID prefixes are `art_…` (was `tab_…`). Wherever the frontend still references "tabs", treat it as the equivalent "article".

---

## 1. Conventions

### 1.1 Base URL & versioning

All endpoints below are mounted under the `/api/v1` prefix.

```
GET /api/v1/workspaces
```

There is no separate version negotiation header; the path is the version.

### 1.2 Response envelope (success)

Every successful response is JSON of the shape:

```json
{
  "success": true,
  "data": { ... },          // present when the endpoint returns a payload
  "message": "..."          // optional human-readable success note
}
```

Endpoints that don't return a payload (e.g. `DELETE`, `logout`, `register`) still produce this envelope, with `data` either omitted or `null`.

### 1.3 Response envelope (error)

**Every error response — 4xx and 5xx — uses this exact shape**:

```json
{
  "success": false,
  "message": "Human-readable reason"
}
```

This applies to:
- Bearer-auth failures (`401`)
- Permission denials (`403`)
- Not-found / hidden resources (`404`)
- Validation failures (`422`)
- State conflicts and duplicates (`409`)
- Server errors (`500`)

The HTTP status code is set on the response; `success: false` is always present. Surface `message` directly to the user where it makes sense — backend messages are kept short and plain.

**Important:** the project previously returned `{"detail": "..."}` for some errors. That is no longer the case; every route now uses the `{success, message}` shape via a global FastAPI exception handler.

### 1.4 Field naming & types

- Wire format is **snake_case** (`workspace_id`, `qc_product`, `name_lower` …).
- IDs are **strings** with a short prefix that hints at the entity: `u_…` for users, `ws_…` for workspaces, `art_…` for articles.
- **Timestamps are integers (epoch milliseconds, UTC)** for the workspaces module (workspace + article responses). The `/users/me`, auth and admin endpoints currently return ISO-8601 `datetime` strings for `created_at` — those are existing contracts and unchanged.
- Enums are sent as their string values (`"creator"`, `"approved"`, `"CL"` …).

### 1.5 Authentication

All endpoints except the four under `/api/v1/auth` require a Bearer JWT access token:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `POST /api/v1/auth/login` and refreshed via `POST /api/v1/auth/refresh`. On a `401` with a valid refresh token, the frontend should attempt one refresh and replay the original request.

### 1.6 Roles & visibility (summary)

There are four roles. Each user has exactly one.

| Role | What they see | What they can do |
|---|---|---|
| `creator` | Only their own workspaces and articles | Create / edit / delete their own workspaces and articles; submit articles for review |
| `qc` | Workspaces that contain at least one article with the QC's `qc_product`; inside those, only matching-product articles | Review-flow transitions (`start-review`, `approve`, `reject`) on matching-product articles |
| `admin` | All workspaces and all articles | Read-only on workspace content; manage QC user accounts; **cannot** approve / reject |
| `superuser` | Everything | Everything (creator-style ownership of their own workspaces + reviewer powers + user management) |

Each `qc` user is tied to **exactly one** `qc_product`. Workspaces and articles that don't carry that product are invisible to the QC (the server returns `404`, never leaks existence via `403`).

See `__documents__/roles.md` and `__documents__/workspace.md` for the business rules behind this matrix.

---

## 2. Authentication endpoints

All four endpoints are public (no `Authorization` header required).

### 2.1 `POST /api/v1/auth/register`

Register a new user. Always creates a `creator` (role is hard-coded server-side). Admins, QCs, and superusers are created via the admin endpoints in §4.

**Request body:**

```json
{
  "email": "alice@example.com",
  "password": "at-least-8-chars"
}
```

- `email`: required, must be a valid email.
- `password`: required, min length 8.

**Success — `201 Created`:**

```json
{ "success": true, "message": "User registered" }
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `409` | `"Email already registered: <email>"` | An account with this email exists |
| `422` | `"email: value is not a valid email address …"` (validation) | Invalid body |

---

### 2.2 `POST /api/v1/auth/login`

Exchange credentials for tokens.

**Request body:**

```json
{ "email": "alice@example.com", "password": "secret" }
```

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>"
  },
  "message": "Login successful"
}
```

- Both tokens are JWTs. The access token's `user_id` claim is what the server reads on subsequent requests.
- Inactive users (`is_active=false`) cannot log in — they get `401`.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `401` | `"Invalid credentials"` | Wrong email/password or inactive user |
| `422` | (validation) | Invalid body |

---

### 2.3 `POST /api/v1/auth/refresh`

Exchange a refresh token for a new access token.

**Request body:**

```json
{ "refresh_token": "<refresh_jwt>" }
```

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": { "access_token": "<new_access_jwt>" },
  "message": "Token refreshed"
}
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `401` | `"Invalid or expired refresh token"` | Token expired, revoked, or wrong type |

---

### 2.4 `POST /api/v1/auth/logout`

Revoke the caller's current refresh token (the refresh-token row is deleted server-side).

**Auth:** Bearer.

**Request body:** none.

**Success — `200 OK`:**

```json
{ "success": true, "message": "Logged out" }
```

---

## 3. Current user

### 3.1 `GET /api/v1/users/me`

Returns the authenticated user.

**Auth:** Bearer.

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "u_8f4f1c…",
    "email": "alice@example.com",
    "is_active": true,
    "role": "creator",
    "qc_product": null,
    "created_at": "2026-06-09T12:34:56.000Z"
  }
}
```

- `role`: one of `"creator" | "qc" | "admin" | "superuser"`.
- `qc_product`: present only when `role == "qc"`; one of the Product codes in §8. `null` for all other roles.
- `created_at`: ISO-8601 datetime (existing contract; the workspaces module uses epoch ms instead).

The frontend should call this once after login to learn the user's role + qc_product, since those drive UI gating (e.g. show "Create Workspace" only to creators/superusers).

---

## 4. Admin — user management

Endpoints under `/api/v1/admin/users` manage **admin and QC accounts only**. Creator accounts come in through `POST /auth/register`. Superuser is bootstrapped from environment variables, never via the API.

All endpoints require Bearer auth plus per-row permissions (see §1.6).

### 4.1 `POST /api/v1/admin/users` — create admin or QC

**Auth:** Bearer.

**Permission:** depends on the requested role:
- `role=admin` → caller needs `users:create:admin` (only superuser has this).
- `role=qc` → caller needs `users:create:qc` (admin or superuser).

**Request body:**

```json
{
  "email": "qc1@example.com",
  "password": "at-least-8-chars",
  "role": "qc",
  "qc_product": "CL"
}
```

- `role`: required, must be `"admin"` or `"qc"`. Sending `"creator"` or `"superuser"` is a `400`.
- `qc_product`: required when `role == "qc"`, must be omitted or `null` otherwise. Invalid combinations are `400`/`422`.

**Success — `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "u_8f4f1c…",
    "email": "qc1@example.com",
    "role": "qc",
    "qc_product": "CL",
    "is_active": true,
    "created_at": "2026-06-09T12:34:56.000Z"
  },
  "message": "User created"
}
```

**Errors:**

| Status | message (examples) | Cause |
|---|---|---|
| `400` | `"qc_product is required when role=qc"` / `"qc_product must be None when role is not qc"` / `"Cannot create user with role 'creator' via this endpoint"` | Role/qc_product mismatch or wrong role |
| `403` | `"Insufficient permissions"` | Caller can't create that role |
| `409` | `"Email already registered: <email>"` | Email already used |
| `422` | validation messages | Body schema invalid (invalid email, password < 8, unknown product code, …) |

---

### 4.2 `GET /api/v1/admin/users` — list users of a role

**Auth:** Bearer.

**Permission:** `users:read:<role>` for the requested `?role=` value.

**Query params:**

| Name | Type | Default | Constraints |
|---|---|---|---|
| `role` | string | — | Required; one of `admin` / `qc` / `creator` |
| `page` | int | `1` | `≥ 1` |
| `page_size` | int | `50` | `1 ≤ x ≤ 200` |

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "u_…",
        "email": "qc1@example.com",
        "role": "qc",
        "qc_product": "CL",
        "is_active": true,
        "created_at": "2026-06-09T12:34:56.000Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  },
  "message": "Found 1 user(s)"
}
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `403` | `"Insufficient permissions"` | Caller can't read that role |
| `422` | validation | Bad `role` value |

---

### 4.3 `GET /api/v1/admin/users/{user_id}` — fetch one user

**Auth:** Bearer.

**Permission:** `users:read:<target.role>` — the server fetches the target first, then checks the permission.

**Path params:** `user_id` (string).

**Success — `200 OK`:** same `ManagedUserResponse` shape as §4.2 items.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `403` | `"Insufficient permissions"` | Caller can't read this user's role |
| `404` | `"User not found"` | No user with this id |

---

### 4.4 `PATCH /api/v1/admin/users/{user_id}` — partial update

**Auth:** Bearer.

**Permission:** `users:update:<target.role>`.

**Path params:** `user_id` (string).

**Request body (partial; send only fields to change):**

```json
{
  "is_active": false,
  "password": "new-password-at-least-8",
  "qc_product": "FD"
}
```

- `is_active`: optional boolean. `false` soft-deactivates the user (they cannot log in).
- `password`: optional string, min length 8. Re-hashes server-side.
- `qc_product`: **only meaningful for QC users**. Sending this field on a non-QC user returns `400`. Sending `null` on a QC user returns `400` (cannot clear). Use this to reassign a QC to a different product.
- `role` is **not** mutable. Once created, a user's role is fixed; create a new account if you need a different role.

**Detection of "omitted vs explicitly null":** the server uses `model_dump(exclude_unset=True)` to tell whether the client sent `qc_product`. Omit the key entirely if you don't want to change it.

**Success — `200 OK`:** updated `ManagedUserResponse`.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `400` | `"qc_product can only be set on QC users"` / `"qc_product cannot be cleared on a QC user"` | Misuse of `qc_product` |
| `403` | `"Insufficient permissions"` | Caller can't update this user |
| `404` | `"User not found"` | No user with this id |

---

## 5. Workspaces — shared shapes

All endpoints in this section live under `/api/v1/workspaces`. They follow the conventions in §1: Bearer auth, snake_case wire fields, epoch-ms timestamps, `{success, message, data}` envelope.

### 5.1 `Article` (response shape)

```ts
type ArticleStatus =
  | "not_submitted"
  | "waiting_for_review"
  | "reviewing"
  | "approved"
  | "rejected"

type Product =
  | "CL" | "MMF" | "FD" | "PL" | "FC" | "IN"
  | "Stock" | "Transfer" | "Telco" | "Global" | "OTA" | "Movie"

type Article = {
  id: string              // "art_…"
  workspace_id: string    // "ws_…"
  name: string
  product: Product
  content: string         // HTML; may be ""
  status: ArticleStatus
  created_at: number      // epoch ms
  updated_at: number      // epoch ms
}
```

> Internal audit fields (`reviewer_user_id`, `reviewed_at`) exist on the document but are **not** exposed in the response. They may be added later without breaking the contract.

### 5.2 `Workspace` (response shape)

```ts
type Workspace = {
  id: string                // "ws_…"
  name: string
  owner_user_id: string     // "u_…"
  created_at: number        // epoch ms
  updated_at: number        // epoch ms

  // Present on list cards, ABSENT on detail (`exclude_none`):
  article_count?: number
  products?: Product[]      // distinct products of all articles in the workspace, in declaration order

  // Present on detail, ABSENT on list (`exclude_none`):
  articles?: Article[]
}
```

**Which fields appear where:**

| Endpoint | `articles` | `article_count` | `products` |
|---|---|---|---|
| `GET /workspaces` (list) | absent | present | present |
| `POST /workspaces` (create) | absent | absent | absent |
| `GET /workspaces/{id}` (detail) | **present** (may be `[]`) | absent | present |
| Other writes that return a workspace | n/a | n/a | n/a |

`exclude_none=True` is used on list, create, and detail responses, so the keys above are physically absent (not `null`) from the JSON.

### 5.3 Scope-filtering for QC

For a QC, `products` and `article_count` on the list page reflect **only the QC's product**, not the whole workspace. Likewise the detail endpoint returns only matching-product articles. For an admin/superuser/owner the values cover the full workspace.

Example: a workspace has 1 CL article and 1 FD article. A QC(CL) sees `article_count: 1, products: ["CL"]`. An admin sees `article_count: 2, products: ["CL","FD"]`.

---

## 6. Workspaces — endpoints

11 endpoints. All require Bearer auth.

### 6.1 `GET /api/v1/workspaces` — list

**Permission:** any authenticated user. Visibility is filtered server-side per role (§1.6).

**Query params:**

| Name | Type | Default | Constraints | Frontend convention |
|---|---|---|---|---|
| `page` | int | `1` | `≥ 1` | 1-indexed |
| `limit` | int | `12` | `1 ≤ x ≤ 100` | Grid sends `12` |

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "ws_a8b…",
        "name": "Smoke Test",
        "owner_user_id": "u_8f4…",
        "created_at": 1717900000000,
        "updated_at": 1717900500000,
        "article_count": 3,
        "products": ["CL", "FD"]
      }
    ],
    "total": 1
  }
}
```

`items` may be `[]` (no workspaces visible). `total` is the unpaginated count under the caller's visibility scope.

**Sort order:** workspaces are returned by `updated_at` descending (most-recently-touched first).

**Errors:**

| Status | message | Cause |
|---|---|---|
| `401` | `"Missing authentication"` / `"Invalid or expired token"` | Not authenticated |
| `500` | `"QC user has no qc_product assigned"` | A QC user reached this code with no qc_product (server-side data-integrity failure) |

---

### 6.2 `POST /api/v1/workspaces` — create

**Permission:** `workspaces:create` (`creator` and `superuser` only). QC and admin get `403`.

**Request body:**

```json
{ "name": "My new workspace" }
```

- `name`: required, 1–100 chars after trim. The server trims; whitespace-only is rejected.

**Success — `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "ws_…",
    "name": "My new workspace",
    "owner_user_id": "u_…",
    "created_at": 1717901000000,
    "updated_at": 1717901000000
  },
  "message": "Workspace created"
}
```

The response intentionally omits `article_count`, `products`, and `articles` (the workspace is empty, so the frontend can show 0 / empty without re-fetching).

**Uniqueness:** workspace names are unique per owner, **case-insensitive**. Two workspaces with names `"A"` and `"a"` cannot coexist under one owner.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `403` | `"Insufficient permissions"` | Caller can't create (admin / qc) |
| `409` | `"Workspace name already in use"` | Same owner already has this name (case-insensitive) |
| `422` | validation | `name` empty or > 100 chars |

---

### 6.3 `GET /api/v1/workspaces/{workspace_id}` — detail

**Permission:** any authenticated user. The use case applies visibility rules:

- Owner sees the workspace + all articles.
- Admin / superuser sees the workspace + all articles.
- QC sees the workspace **only if it contains at least one article matching their `qc_product`**, and only those matching articles in `articles`.
- Anyone else (including another creator) gets a `404`.

**Path params:** `workspace_id` (string).

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "ws_…",
    "name": "Smoke Test",
    "owner_user_id": "u_…",
    "created_at": 1717900000000,
    "updated_at": 1717900500000,
    "products": ["CL", "FD"],
    "articles": [
      {
        "id": "art_…",
        "workspace_id": "ws_…",
        "name": "Draft 1",
        "product": "CL",
        "content": "<p>Hello <strong>world</strong></p>",
        "status": "not_submitted",
        "created_at": 1717900100000,
        "updated_at": 1717900480000
      }
    ]
  }
}
```

`articles` is always present (possibly `[]`). Order is `created_at` ascending — same order an article was added is the order it appears in the rail.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` | Doesn't exist OR caller is out of scope (existence is hidden) |

---

### 6.4 `DELETE /api/v1/workspaces/{workspace_id}` — delete

**Permission:** **owner only.** Even an admin/QC/superuser cannot delete via this endpoint unless they are the owner. (A superuser who owns the workspace can.)

**Cascade:** deleting a workspace deletes all of its articles.

**Path params:** `workspace_id` (string).

**Success — `200 OK`:**

```json
{ "success": true, "message": "Workspace deleted" }
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` | Doesn't exist OR caller isn't the owner (existence hidden) |

---

### 6.5 `POST /api/v1/workspaces/{workspace_id}/articles` — create article

**Permission:** any authenticated user; the use case enforces ownership (only the workspace's owner — typically a creator — can create articles; admins / QCs get a `404`).

**Path params:** `workspace_id`.

**Request body:**

```json
{ "name": "Draft 1", "product": "CL" }
```

- `name`: required, 1–100 chars after trim.
- `product`: required, one of the 12 codes in §8. **Immutable after creation** — there is no API to change an article's product. If a creator needs to change it, they delete and recreate.

**Success — `201 Created`:**

```json
{
  "success": true,
  "data": {
    "id": "art_…",
    "workspace_id": "ws_…",
    "name": "Draft 1",
    "product": "CL",
    "content": "",
    "status": "not_submitted",
    "created_at": 1717902000000,
    "updated_at": 1717902000000
  },
  "message": "Article created"
}
```

`content` is initialised to `""`. `status` is `"not_submitted"`. `created_at == updated_at` on creation.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` | Workspace missing OR caller isn't owner |
| `422` | `"product: input should be …"` etc. | Invalid `product` code or invalid name |

---

### 6.6 `DELETE /api/v1/workspaces/{workspace_id}/articles/{article_id}` — delete article

**Permission:** owner-only (same as workspace delete).

**Path params:** `workspace_id`, `article_id`.

**Success — `200 OK`:**

```json
{ "success": true, "message": "Article deleted" }
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` | Workspace missing OR caller isn't owner |
| `404` | `"Article not found"` | Article missing OR its `workspace_id` ≠ path `workspace_id` |

---

### 6.7 `PATCH /api/v1/workspaces/{workspace_id}/articles/{article_id}` — autosave content

**Purpose:** persist in-progress HTML for an article. Called automatically by the editor's autosave hook (5-second debounce + flush on tab switch / unmount). The frontend can issue this as fast as the user types — every call hits the DB.

**Permission:** owner-only. Allowed only while `status ∈ {"not_submitted", "reviewing"}` (creator may continue editing during `reviewing` per the spec).

**Path params:** `workspace_id`, `article_id`.

**Request body:**

```json
{ "content": "<p>Hello <strong>world</strong></p>" }
```

- `content`: required string. Empty string is allowed. Images are inlined as base64 data URLs in MVP (no separate upload endpoint), so payloads can be large.

**Body-size limit:** configured at the ASGI / reverse-proxy layer. The recommended limit is **25 MB** (`client_max_body_size 26M;` on nginx, equivalent on others). Anything larger is rejected at the proxy before reaching the app.

**Success — `200 OK`:**

```json
{
  "success": true,
  "data": {
    "id": "art_…",
    "workspace_id": "ws_…",
    "name": "Draft 1",
    "product": "CL",
    "content": "<p>Hello <strong>world</strong></p>",
    "status": "not_submitted",
    "created_at": 1717900100000,
    "updated_at": 1717902500000
  }
}
```

The server echoes the persisted `content` exactly as stored and bumps `updated_at` to the server clock. `status` is unchanged.

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` | Workspace missing OR caller isn't owner |
| `404` | `"Article not found"` | Article missing OR wrong workspace |
| `409` | `"Article is not in an editable state"` | `status` is one of `waiting_for_review` / `approved` / `rejected`. The frontend already prevents this — if it fires, the article's status changed server-side mid-edit (e.g. a QC just approved). |

---

### 6.8 `POST /api/v1/workspaces/{workspace_id}/articles/{article_id}/submit` — creator submits for review

**Purpose:** transitions `not_submitted → waiting_for_review`. Triggered by the "Submit for Review" button (visible only in `not_submitted`).

**Permission:** owner-only.

**Pre-state required:** `status == "not_submitted"`.

**Path params:** `workspace_id`, `article_id`.

**Request body:** none.

**Success — `200 OK`:** the updated `Article` (with `status: "waiting_for_review"`, bumped `updated_at`).

```json
{
  "success": true,
  "data": {
    "id": "art_…",
    "workspace_id": "ws_…",
    "name": "Draft 1",
    "product": "CL",
    "content": "<p>…</p>",
    "status": "waiting_for_review",
    "created_at": 1717900100000,
    "updated_at": 1717903000000
  }
}
```

**Errors:**

| Status | message | Cause |
|---|---|---|
| `404` | `"Workspace not found"` / `"Article not found"` | Missing or out-of-scope |
| `409` | `"Article is not in a submittable state"` | `status` is not `not_submitted` (already submitted, in review, approved, or rejected) |

---

### 6.9 `POST /api/v1/workspaces/{workspace_id}/articles/{article_id}/start-review` — QC picks up

**Purpose:** transitions `waiting_for_review → reviewing`. Records `reviewer_user_id = caller.id` internally (not exposed in the response today).

**Permission:** `workspaces:review` (QC or superuser). Admin gets `403`.

**Pre-state required:** `status == "waiting_for_review"` AND (for non-superusers) `article.product == caller.qc_product`. If the article's product doesn't match the QC's, the server returns `404` (not `403`) — existence is hidden.

**Path params:** `workspace_id`, `article_id`.

**Request body:** none.

**Success — `200 OK`:** the updated `Article` (`status: "reviewing"`).

**Errors:**

| Status | message | Cause |
|---|---|---|
| `403` | `"Insufficient permissions"` | Caller lacks `workspaces:review` (e.g. admin or creator) |
| `404` | `"Article not found"` | Missing, wrong workspace, OR out of QC's product scope |
| `409` | `"Article is not waiting for review"` | Status is anything other than `waiting_for_review` |

**Server-side check order (frontend can rely on this for error interpretation):**

1. Article exists and belongs to the path workspace — otherwise `404`.
2. (Non-superuser only) `article.product == caller.qc_product` — otherwise `404`.
3. `status == "waiting_for_review"` — otherwise `409`.

So if a QC sends `start-review` on an article whose status is `not_submitted` AND whose product doesn't match, the response is always `404`. The product check fires first to avoid leaking the article's existence.

---

### 6.10 `POST /api/v1/workspaces/{workspace_id}/articles/{article_id}/approve` — QC approves

**Purpose:** transitions `reviewing → approved`. Sets `reviewed_at` server-side.

**Permission:** `workspaces:review` (QC or superuser). Admin gets `403`.

**Pre-state required:** `status == "reviewing"` AND (for non-superusers) `article.product == caller.qc_product`.

**Request body:** none.

**Success — `200 OK`:** the updated `Article` (`status: "approved"`).

**Errors:** same shape as `start-review` (404 / 403 / 409), with message `"Article is not in a reviewable state"` on a 409.

---

### 6.11 `POST /api/v1/workspaces/{workspace_id}/articles/{article_id}/reject` — QC rejects

**Purpose:** transitions `reviewing → rejected`. Sets `reviewed_at` server-side. No `reason` field yet (planned for a future revision).

**Permission, pre-state, errors:** identical to `approve`.

**Success — `200 OK`:** the updated `Article` (`status: "rejected"`).

---

## 7. Article status workflow

```
                Creator clicks Submit
not_submitted ─────────────────────────▶  waiting_for_review
                                                  │
                                          QC picks up
                                                  ▼
                                              reviewing
                                       ┌──────────┴──────────┐
                                  QC approves            QC rejects
                                       ▼                     ▼
                                   approved              rejected
```

| Status | Creator can edit content? | Show "Submit" button? | Frontend editor mode |
|---|---|---|---|
| `not_submitted` | yes | yes | editable |
| `waiting_for_review` | **no** | no | read-only |
| `reviewing` | yes (creator may make changes while QC reviews) | no | editable |
| `approved` | no | no | read-only |
| `rejected` | no | no | read-only |

**There is no "retract" or "back to draft" transition.** Once a creator submits, the only way out is the QC's decision (or rejecting and creating a new article).

---

## 8. Product enum reference

A closed, ordered set. Adding values requires a backend deploy.

```
CL · MMF · FD · PL · FC · IN · Stock · Transfer · Telco · Global · OTA · Movie
```

Wire format is exactly these strings (case-sensitive). The order above is also the recommended display order in dropdowns — `products` arrays returned by the backend are sorted by this declaration order, so the frontend can render them as received.

---

## 9. Common error patterns

A short cheat sheet for shapes the frontend may see often:

| Status | When | message (typical) |
|---|---|---|
| `401` | Missing / expired / malformed token | `"Missing authentication"` / `"Invalid or expired token"` / `"Invalid Authorization header format"` |
| `401` | Inactive or deleted user | `"User not found or inactive"` |
| `401` | Token's payload claims wrong type or no user_id | `"Invalid token type"` / `"Invalid token payload"` |
| `403` | Missing capability (set via `require_permissions`) | `"Insufficient permissions"` |
| `404` | Workspace not visible or doesn't exist | `"Workspace not found"` |
| `404` | Article not visible or doesn't exist | `"Article not found"` |
| `404` | Admin endpoint, target user gone | `"User not found"` |
| `409` | Duplicate workspace name per owner | `"Workspace name already in use"` |
| `409` | State-transition not allowed | `"Article is not in a submittable state"` / `"Article is not waiting for review"` / `"Article is not in a reviewable state"` / `"Article is not in an editable state"` |
| `409` | Email already used | `"Email already registered: <email>"` |
| `422` | Pydantic validation failure | `"<field>: <reason>"` (e.g. `"name: String should have at most 100 characters"`) |
| `500` | QC user with no `qc_product` reached a workspace code path | `"QC user has no qc_product assigned"` |

The exact wording of `message` may evolve. The frontend should switch on **status code** first, then optionally on the message text for finer-grained UX (e.g. "name already in use" prompting an inline form error).

---

## 10. Quick reference table

| # | Method | Path | Body | Auth | Permission | Success |
|---|---|---|---|---|---|---|
| 1 | `POST` | `/api/v1/auth/register` | `{email, password}` | — | — | `201` |
| 2 | `POST` | `/api/v1/auth/login` | `{email, password}` | — | — | `200` (tokens) |
| 3 | `POST` | `/api/v1/auth/refresh` | `{refresh_token}` | — | — | `200` (access_token) |
| 4 | `POST` | `/api/v1/auth/logout` | — | Bearer | — | `200` |
| 5 | `GET` | `/api/v1/users/me` | — | Bearer | — | `200` (User) |
| 6 | `POST` | `/api/v1/admin/users` | `{email,password,role,qc_product?}` | Bearer | `users:create:{role}` | `201` |
| 7 | `GET` | `/api/v1/admin/users?role&page&page_size` | — | Bearer | `users:read:{role}` | `200` (list) |
| 8 | `GET` | `/api/v1/admin/users/{id}` | — | Bearer | `users:read:{target.role}` | `200` |
| 9 | `PATCH` | `/api/v1/admin/users/{id}` | `{is_active?,password?,qc_product?}` | Bearer | `users:update:{target.role}` | `200` |
| 10 | `GET` | `/api/v1/workspaces?page&limit` | — | Bearer | (visibility scoped) | `200` (list) |
| 11 | `POST` | `/api/v1/workspaces` | `{name}` | Bearer | `workspaces:create` | `201` (Workspace) |
| 12 | `GET` | `/api/v1/workspaces/{id}` | — | Bearer | (visibility scoped) | `200` (Workspace+articles) |
| 13 | `DELETE` | `/api/v1/workspaces/{id}` | — | Bearer | owner | `200` |
| 14 | `POST` | `/api/v1/workspaces/{id}/articles` | `{name, product}` | Bearer | owner | `201` (Article) |
| 15 | `DELETE` | `/api/v1/workspaces/{id}/articles/{aid}` | — | Bearer | owner | `200` |
| 16 | `PATCH` | `/api/v1/workspaces/{id}/articles/{aid}` | `{content}` | Bearer | owner, editable status | `200` (Article) |
| 17 | `POST` | `/api/v1/workspaces/{id}/articles/{aid}/submit` | — | Bearer | owner, `not_submitted` | `200` (Article) |
| 18 | `POST` | `/api/v1/workspaces/{id}/articles/{aid}/start-review` | — | Bearer | `workspaces:review`, scope, `waiting_for_review` | `200` (Article) |
| 19 | `POST` | `/api/v1/workspaces/{id}/articles/{aid}/approve` | — | Bearer | `workspaces:review`, scope, `reviewing` | `200` (Article) |
| 20 | `POST` | `/api/v1/workspaces/{id}/articles/{aid}/reject` | — | Bearer | `workspaces:review`, scope, `reviewing` | `200` (Article) |

---

## 11. Integration checklist for the frontend

1. **Token storage and refresh.** Store both `access_token` and `refresh_token` from `/auth/login`. On any `401`, attempt a single refresh via `/auth/refresh`; if the refresh also fails, log the user out.
2. **Bootstrap call after login.** Call `GET /users/me` once to learn `role` and `qc_product`; cache those in client state and use them to gate UI affordances (create button, review buttons, etc.).
3. **Workspace list endpoint** drives the grid; use `article_count` and `products` directly on each card. For a QC, `products` is always a one-element array of their assigned product — render accordingly.
4. **Workspace detail** is the source of truth for the tab rail and editor. The `articles` array is already filtered for the caller's scope; don't apply additional client-side filtering.
5. **Autosave** the `PATCH /articles/{id}` call on a 5-second debounce; flush pending content immediately on tab-switch / route-leave. On `409` (status changed mid-edit), refetch the detail endpoint and re-render — the article is no longer editable.
6. **Submit / approve / reject** all return the updated `Article`. Write that into the cache directly — no separate refetch needed.
7. **Error handling.** Read `message` from `{success: false, message}` for human display. Switch on the HTTP status code for behaviour (refresh on 401, redirect to list on workspace 404, inline form error on 409 dup name, etc.).
8. **Date formatting.** Workspaces / articles use epoch ms — pass straight to `new Date(ms)` in JS. `/users/me` and `/admin/users` use ISO-8601 strings.
9. **Confirm `tabs` → `articles`** in the frontend codebase. The original `frontend/__plans__/workspace/apis.md` document still uses "tab"; the new wire contract is "article".
