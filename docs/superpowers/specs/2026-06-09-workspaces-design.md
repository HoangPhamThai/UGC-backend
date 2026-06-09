# Content Workspaces — Backend Design

Date: 2026-06-09
Status: Proposed (revised)

## Summary

A new `workspaces` module that backs the frontend Content Workspaces feature. It introduces two domain entities (`Workspace`, `Article`), a `Product` enum, role-aware authorization that is **product-scoped for QCs**, and eleven HTTP endpoints under `/api/v1/workspaces`. It also adds a process-global FastAPI exception handler so error responses match the frontend's `{success, message}` envelope across the whole app.

> **Terminology note.** The unit of content was called *tab* in earlier drafts. It is now **`article`** (Vietnamese: *bài viết*) everywhere in code, API, models, and routes. The product business doc (`UGC/__documents__/workspace.md`) uses *bài viết* in Vietnamese prose with the parenthetical *(Article)* on first mention.

## Motivation

- The frontend ships a fully specified HTTP contract for workspaces and articles (paginated grid, autosave-driven editor, review workflow). The backend currently has no module for any of it.
- The product team has added a closed taxonomy of **products** (12 codes such as `CL`, `MMF`, `FD` …) that every article belongs to. QCs are scoped to a single product, and that scoping must be enforced server-side.
- Existing error responses use FastAPI's default `{"detail": "..."}` shape; the frontend reads `message`. New work is the right moment to fix this once for every route.

## Out of scope

- Reviewer assignment / queueing logic. Any user with `WORKSPACES_REVIEW` whose `qc_product` matches an article's `product` can pick up that article.
- Rejection reasons or review comments. The frontend doesn't surface them yet; deferred.
- Article ordering / drag-reorder. The contract doesn't request it; articles are returned in `created_at` ascending order.
- Soft-delete or trash. Both workspace and article deletes are permanent.
- Automated tests. The repo has no test framework today; introducing one is a separate decision.
- Cross-collection transactions. Workspace delete cascades by issuing two writes in sequence (workspace then articles); recovery for partial failure is documented as an ops concern, not coded.
- Body-size enforcement inside handlers. Limits are configured at the ASGI / reverse-proxy layer; see "Body size" below.
- Changing an article's product after creation. Not supported by the contract.

## Domain model

### `Product`

A `str, Enum` defined in `app/modules/workspaces/data/model.py` (also imported by `app/core/permissions.py` and the user module — see "Cross-module impact"):

```python
class Product(str, Enum):
    CL       = "CL"
    MMF      = "MMF"
    FD       = "FD"
    PL       = "PL"
    FC       = "FC"
    IN       = "IN"
    STOCK    = "Stock"
    TRANSFER = "Transfer"
    TELCO    = "Telco"
    GLOBAL   = "Global"
    OTA      = "OTA"
    MOVIE    = "Movie"
```

The set is intentionally closed. Adding a value requires (a) updating this enum, (b) updating `UGC/__documents__/workspace.md` §2.3, and (c) considering whether existing data references a new code that isn't yet allowed.

### `ArticleStatus`

```python
class ArticleStatus(str, Enum):
    NOT_SUBMITTED      = "not_submitted"
    WAITING_FOR_REVIEW = "waiting_for_review"
    REVIEWING          = "reviewing"
    APPROVED           = "approved"
    REJECTED           = "rejected"
```

### `Workspace` (Mongo document)

```python
class Workspace(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ws"), alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    name_lower: str = Field(..., description="Lowercased name for unique index")
    owner_user_id: str = Field(..., description="Owning creator user id")

    class Config:
        collection_name = "workspaces"
```

> Note: `Workspace` does **not** persist the product set. The list of products is derived from its articles (see "Response shapes" → `WorkspaceResponse.products`). Storing it would force every article write to update two collections.

### `Article` (Mongo document)

```python
class Article(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("art"), alias="_id")
    workspace_id: str = Field(..., description="Parent workspace id")
    name: str = Field(..., min_length=1, max_length=100)
    product: Product = Field(..., description="Closed-set product code, immutable")
    content: str = Field(default="", description="TipTap HTML; may be empty")
    status: ArticleStatus = Field(default=ArticleStatus.NOT_SUBMITTED)
    reviewer_user_id: Optional[str] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)

    class Config:
        collection_name = "articles"
```

`product` is required at creation and **never written again** by any code path. The repo's `update_content` and `update_status` only set their respective fields plus `updated_at`. Migration of an article between products is not supported.

### Why `name_lower`

Workspace names are unique per owner, case-insensitive. We denormalize a lowercased copy and put the unique index on it:

- Display: `name` ("Smoke Test") preserves original casing.
- Dedupe key: `name_lower` ("smoke test") via `name.casefold()`.
- Unique compound index: `(owner_user_id, name_lower)`.

The repo sets `name_lower` on every write; callers never pass it. Article names have no uniqueness constraint.

### Indexes

Created on startup via `ensure_indexes()` methods on the data repos, called from `app.py`'s `lifespan` immediately after `mongo_connection.connect()`:

- `workspaces`: `{owner_user_id: 1}`, **unique** `{owner_user_id: 1, name_lower: 1}`
- `articles`: `{workspace_id: 1, created_at: 1}`, `{workspace_id: 1, product: 1}`, `{product: 1, status: 1}`

The `(product, status)` compound supports the QC inbox query "all `waiting_for_review` articles for my product, across all creators". The `(workspace_id, product)` compound supports the QC-scoped article filter inside a single workspace.

## Cross-module impact

This module assumes the **users** module already carries the QC's product assignment. The roles spec (`2026-06-09-roles-and-remove-api-keys-design.md`) is updated to add a `qc_product: Optional[Product]` field on `User`:

- Required when `role == UserRole.QC`.
- Must be `None` for every other role.
- Settable / changeable by admins (`USERS_UPDATE_QC`) and superuser; never by the QC themselves.

This module imports `Product` from `app.modules.workspaces.data.model` into `app.modules.users.data.model`. If that import direction is undesirable, move `Product` into a shared location (e.g. `app/core/product.py`) and import from there in both modules.

## Repositories

Abstract repos in `app/modules/workspaces/domain/repo.py`; Mongo implementations in `app/modules/workspaces/data/repo.py`.

```python
class WorkspaceRepo(ABC):
    async def create(self, workspace: Workspace) -> Workspace: ...
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]: ...
    async def list_by_owner(self, owner_user_id: str, *, skip: int, limit: int) -> list[Workspace]: ...
    async def count_by_owner(self, owner_user_id: str) -> int: ...
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]: ...
    async def count_all(self) -> int: ...
    async def list_with_product(self, product: Product, *, skip: int, limit: int) -> list[Workspace]: ...
    async def count_with_product(self, product: Product) -> int: ...
    async def delete(self, workspace_id: str) -> None: ...
    async def article_counts(self, workspace_ids: list[str], *, product: Optional[Product] = None) -> dict[str, int]: ...
    async def products_for(self, workspace_ids: list[str]) -> dict[str, list[Product]]: ...


class ArticleRepo(ABC):
    async def create(self, article: Article) -> Article: ...
    async def get_by_id(self, article_id: str) -> Optional[Article]: ...
    async def list_by_workspace(
        self, workspace_id: str, *, product: Optional[Product] = None,
    ) -> list[Article]: ...   # asc by created_at; filtered by product when given
    async def workspace_has_product(self, workspace_id: str, product: Product) -> bool: ...
    async def update_content(self, article_id: str, content: str) -> Optional[Article]: ...
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
    ) -> Optional[Article]: ...
    async def delete(self, article_id: str) -> None: ...
    async def delete_by_workspace(self, workspace_id: str) -> int: ...
```

### Implementation notes

- **`list_with_product` / `count_with_product`** drive the QC's paginated workspace list. They use a `$lookup`-free approach: first collect distinct `workspace_id` values from `articles.find({product})` skip/limit, then fetch those workspaces by `_id`. For pagination stability the order is by `articles.created_at.max()` per workspace; the implementation can simplify to "workspaces having any article with that product, sorted by `workspaces.updated_at` desc". Either is acceptable as long as `count_with_product` matches.
- **`article_counts(..., product=...)`** runs a single `$match` + `$group` aggregate. When `product` is supplied, only articles of that product are counted (this is what the QC grid card needs).
- **`products_for(workspace_ids)`** runs `$match: {workspace_id: {$in}}` then `$group: {_id: workspace_id, products: $addToSet: $product}`. Returns `{ws_id: [Product, ...]}` for batch responses.
- **`workspace_has_product`** is a cheap existence check used by `get_workspace` to decide whether a QC may see a workspace at all.
- **`update_content` / `update_status`** are atomic `find_one_and_update` with `return_document=AFTER`. They return `None` if the article disappeared mid-call; the use case translates that to `ArticleNotFoundError`.
- **`delete_by_workspace`** runs after the workspace document is removed; this ordering means a partial failure (workspace deleted, articles not) leaves orphaned articles to clean up but never the inverse.
- `name_lower` is set inside `WorkspaceDataRepository.create`; never set by callers.

## Authorization model

The module distinguishes three orthogonal axes:

1. **Capability** (permission bit on the role): can the caller in principle create / read-any / review?
2. **Ownership** (per-row check inside the use case): is the caller the workspace's owner?
3. **Product scope** (per-row check for QCs): does the article's `product` match the caller's `qc_product`?

Permissions in `app/core/permissions.py`:

```python
class Permission(str, Enum):
    # ... existing users:* ...
    WORKSPACES_CREATE          = "workspaces:create"             # creator, superuser
    WORKSPACES_READ_ANY        = "workspaces:read:any"           # admin, superuser
    WORKSPACES_READ_BY_PRODUCT = "workspaces:read:by_product"    # qc
    WORKSPACES_REVIEW          = "workspaces:review"             # qc, superuser  (NOT admin)
```

`ROLE_PERMISSIONS` additions (union with existing values):

| Role | Adds |
|---|---|
| `CREATOR` | `WORKSPACES_CREATE` |
| `QC` | `WORKSPACES_READ_BY_PRODUCT`, `WORKSPACES_REVIEW` |
| `ADMIN` | `WORKSPACES_READ_ANY` |
| `SUPERUSER` | unchanged — `frozenset(Permission)` already grants everything |

> **Difference from the original draft:** `WORKSPACES_REVIEW` is **removed from admin**, per the business doc (`UGC/__documents__/roles.md` §4.3): "Admin không trực tiếp duyệt / từ chối tab". Admin sees everything but does not act on review state. Superuser still has all permissions implicitly.

The "read" capability comes in two flavours so the use case can branch cheaply on permission, not on role. A QC has `READ_BY_PRODUCT` but **not** `READ_ANY`; admin and superuser have `READ_ANY`. Creators have neither and are limited to their own workspaces.

## Use cases

One use case per business operation, in `app/modules/workspaces/domain/usecases/`. Routes are thin; use cases own authorization, product scoping, and state-transition rules. Domain errors are raised as exceptions and translated to HTTP statuses by the global handler.

| Use case | Authorization | Scoping rule | Pre-state | Effect |
|---|---|---|---|---|
| `create_workspace` | `WORKSPACES_CREATE` | — | — | insert; on duplicate-key → `WorkspaceNameTakenError` |
| `list_workspaces` | any authenticated | branches on permission (see below) | — | returns paginated workspaces visible to caller, each with `article_count` and `products` |
| `get_workspace` | any authenticated | see below | exists | returns workspace + articles filtered by scope; out-of-scope → `WorkspaceNotFoundError` (hides existence) |
| `delete_workspace` | owner only | — | exists | `delete(workspace_id)` then `delete_by_workspace(workspace_id)` |
| `create_article` | owner of parent | — | parent exists | insert article with `workspace_id`, `product=<body>`, `content=""`, `status=not_submitted` |
| `delete_article` | owner of parent | — | article exists AND `article.workspace_id == path id` | hard delete |
| `update_article_content` | owner of parent | — | `status ∈ {not_submitted, reviewing}` | `update_content`; otherwise → `ArticleStateConflictError` |
| `submit_article` | owner of parent | — | `status == not_submitted` | `update_status(waiting_for_review)`; else → `ArticleStateConflictError` |
| `start_review_article` | `WORKSPACES_REVIEW` AND product match | `article.product == caller.qc_product` (skip for superuser) | `status == waiting_for_review` | `update_status(reviewing, reviewer_user_id=caller.id)`; else → state conflict |
| `approve_article` | `WORKSPACES_REVIEW` AND product match | same as above | `status == reviewing` | `update_status(approved, set_reviewed_at=True)` |
| `reject_article` | `WORKSPACES_REVIEW` AND product match | same as above | `status == reviewing` | `update_status(rejected, set_reviewed_at=True)` |

### `list_workspaces` branching

```python
if caller.has(WORKSPACES_READ_ANY):              # admin, superuser
    workspaces = repo.list_all(skip, limit)
    products_by_ws = workspace_repo.products_for([w.id for w in workspaces])
    counts = workspace_repo.article_counts([w.id for w in workspaces])
elif caller.has(WORKSPACES_READ_BY_PRODUCT):     # qc — requires qc_product
    p = caller.qc_product
    if p is None:                                # data integrity: a qc must have a product
        raise QcMisconfiguredError()
    workspaces = repo.list_with_product(p, skip, limit)
    products_by_ws = {w.id: [p] for w in workspaces}        # QC only sees their product
    counts = workspace_repo.article_counts([w.id for w in workspaces], product=p)
else:                                            # creator (or anyone else)
    workspaces = repo.list_by_owner(caller.id, skip, limit)
    products_by_ws = workspace_repo.products_for([w.id for w in workspaces])
    counts = workspace_repo.article_counts([w.id for w in workspaces])

total = corresponding_count_method(...)
```

### `get_workspace` branching

```python
ws = repo.get_by_id(workspace_id)
if ws is None:
    raise WorkspaceNotFoundError()

if caller.id == ws.owner_user_id:
    articles = article_repo.list_by_workspace(workspace_id)
    products = sorted({a.product for a in articles})
elif caller.has(WORKSPACES_READ_ANY):
    articles = article_repo.list_by_workspace(workspace_id)
    products = sorted({a.product for a in articles})
elif caller.has(WORKSPACES_READ_BY_PRODUCT):
    if not article_repo.workspace_has_product(workspace_id, caller.qc_product):
        raise WorkspaceNotFoundError()           # hide existence
    articles = article_repo.list_by_workspace(workspace_id, product=caller.qc_product)
    products = [caller.qc_product]
else:
    raise WorkspaceNotFoundError()               # hide existence
```

Article endpoints always validate `article.workspace_id == path workspace_id` and raise `ArticleNotFoundError` (404) on mismatch — *before* checking product, so the not-found path never leaks the article's product to an unauthorized caller.

#### Check ordering for review-flow use cases (`start_review_article`, `approve_article`, `reject_article`)

The order is fixed and must not be reorganized by implementations, because earlier checks suppress information that later checks would otherwise leak:

1. **Load article by id.** Missing → `ArticleNotFoundError` (404).
2. **Workspace-id match.** `article.workspace_id != path workspace_id` → `ArticleNotFoundError` (404).
3. **Product scope (for non-superuser callers).** `article.product != caller.qc_product` → `ArticleNotFoundError` (404). This must fire **before** the status check, so a QC trying to act on an out-of-scope article sees the same 404 whether the article is `not_submitted`, `approved`, or any other state — the article's existence is not revealed.
4. **Status check.** Wrong status → `ArticleStateConflictError` (409).
5. **Apply the transition** via `update_status(...)`.

The same ordering (load → workspace match → ownership → status) applies to `update_article_content`, `submit_article`, `delete_article`, and `create_article` (creation skips status; ownership is on the parent workspace).

### Errors

In `app/modules/workspaces/domain/errors.py`:

```python
class WorkspaceError(Exception): ...
class WorkspaceNotFoundError(WorkspaceError): ...        # → 404
class ArticleNotFoundError(WorkspaceError): ...          # → 404
class WorkspaceNameTakenError(WorkspaceError): ...       # → 409
class ArticleStateConflictError(WorkspaceError): ...     # → 409
class QcMisconfiguredError(WorkspaceError): ...          # → 500 — QC user with no qc_product
```

Owner-fail and QC-product-mismatch on read paths raise `WorkspaceNotFoundError` rather than a forbidden error, to avoid leaking existence to unauthorized callers. Capability-only failures (missing `WORKSPACES_CREATE` etc.) are raised at the route layer via `Depends(require_permissions(...))`, returning `HTTPException(403)`; the global error envelope reshapes them.

`QcMisconfiguredError` is a data-integrity safeguard — admins shouldn't be able to put a user into `role=qc` without a `qc_product`. Surface as 500 because it indicates a server-side invariant violation, not a user mistake.

## Routes

`app/modules/workspaces/presentation/routes.py`, mounted under `/api/v1` from `app.py`:

| Method | Path | Body | Response data |
|---|---|---|---|
| `GET` | `/workspaces?page&limit` | — | `{items: WorkspaceResponse[], total}` — items have `article_count` and `products`; no `articles` |
| `POST` | `/workspaces` | `{name}` | `WorkspaceResponse` (no `articles`, no `article_count`) |
| `GET` | `/workspaces/{id}` | — | `WorkspaceResponse` with `articles` populated (scope-filtered) |
| `DELETE` | `/workspaces/{id}` | — | `{success: true}` |
| `POST` | `/workspaces/{id}/articles` | `{name, product}` | `ArticleResponse` |
| `DELETE` | `/workspaces/{id}/articles/{article_id}` | — | `{success: true}` |
| `PATCH` | `/workspaces/{id}/articles/{article_id}` | `{content}` | `ArticleResponse` |
| `POST` | `/workspaces/{id}/articles/{article_id}/submit` | — | `ArticleResponse` |
| `POST` | `/workspaces/{id}/articles/{article_id}/start-review` | — | `ArticleResponse` |
| `POST` | `/workspaces/{id}/articles/{article_id}/approve` | — | `ArticleResponse` |
| `POST` | `/workspaces/{id}/articles/{article_id}/reject` | — | `ArticleResponse` |

Routes use `Depends(get_current_user)` and `Depends(require_permissions(...))` where the check is purely capability-based (create + review endpoints). Owner-vs-readers and QC product checks live inside the use cases because they need the workspace/article documents.

### Request schemas (`presentation/schema.py`)

```python
class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CreateArticleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    product: Product                                        # required; closed enum

class UpdateArticleContentRequest(BaseModel):
    content: str
```

Trimming follows what the frontend already does; backend defends with `min_length=1` after `str.strip()` in the use case. `product` is validated by Pydantic enum membership — invalid codes return 422 with `{success: false, message: "Invalid product code"}`.

### Response schemas

Internal models store `datetime`; the frontend wants epoch ms. Conversion happens at the response-schema boundary:

```python
def _to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class ArticleResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    product: Product
    content: str
    status: ArticleStatus
    created_at: int
    updated_at: int

    @classmethod
    def from_model(cls, a: Article) -> "ArticleResponse": ...


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_user_id: str
    created_at: int
    updated_at: int
    article_count: Optional[int] = None
    products: Optional[list[Product]] = None
    articles: Optional[list[ArticleResponse]] = None

    @classmethod
    def from_model(
        cls,
        ws: Workspace,
        *,
        articles: Optional[list[Article]] = None,
        article_count: Optional[int] = None,
        products: Optional[list[Product]] = None,
    ) -> "WorkspaceResponse": ...


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int
```

Important notes on the response shape:

- The list endpoint uses `response_model_exclude_none=True` so `articles` is absent (not `null`) on items; the detail endpoint passes `articles=[...]` so the field is present.
- `products` on items reflects the **scope-filtered** product set for the caller. For a QC, it always contains exactly their product (because the workspace wouldn't be visible to them otherwise); for admin/superuser/owner, it's the full set of products of all articles in that workspace.
- `article_count` is also scope-filtered for a QC (counts only articles in their product).
- `reviewer_user_id` and `reviewed_at` are intentionally not surfaced — they're internal audit data; the frontend contract doesn't include them today.

### Body size

The PATCH-content endpoint can receive large base64 payloads. The application does not enforce a body limit inside the handler. Limits are configured at the ASGI / reverse-proxy layer:

- Document the recommended `client_max_body_size 26M;` (nginx) or equivalent for the deployment.
- Uvicorn's defaults are generous enough for the spec's 25 MB target; no change needed for the dev server.

If a deployment ever needs strict in-app enforcement, add a middleware that rejects requests over a configured threshold before the body is buffered.

## Global error envelope (`app/core/errors.py`)

A new module that registers FastAPI exception handlers, called from `app.py` after `setup_middleware(app)`. Fixes the pre-existing inconsistency where errors emit `{"detail": ...}` instead of `{success: false, message}` for every route in the app.

```python
def _envelope(message: str) -> dict:
    return {"success": False, "message": message}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content=_envelope(msg))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {"msg": "Invalid request"}
    return JSONResponse(status_code=422, content=_envelope(first.get("msg", "Invalid request")))


_DOMAIN_STATUS = {
    WorkspaceNotFoundError: 404,
    ArticleNotFoundError: 404,
    WorkspaceNameTakenError: 409,
    ArticleStateConflictError: 409,
    QcMisconfiguredError: 500,
}


async def domain_exception_handler(request: Request, exc: Exception):
    status_code = _DOMAIN_STATUS.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content=_envelope(str(exc) or "Internal error"))


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    for exc_cls in _DOMAIN_STATUS:
        app.add_exception_handler(exc_cls, domain_exception_handler)
```

Route handlers no longer need per-exception `try/except`; domain errors bubble to the handler. Existing routes (auth, users, admin) keep raising `HTTPException` as they do today — the handler reshapes those to the new envelope automatically.

## Module layout

```
app/
  app.py                                # mount workspaces_router; call register_exception_handlers; call ensure_indexes in lifespan
  core/
    permissions.py                      # add WORKSPACES_CREATE / READ_ANY / READ_BY_PRODUCT / REVIEW
    errors.py                           # NEW: global exception handlers + register_exception_handlers
  modules/
    workspaces/                         # NEW
      __init__.py
      data/
        __init__.py
        model.py                        # Product, ArticleStatus, Workspace, Article
        repo.py                         # WorkspaceDataRepository, ArticleDataRepository, ensure_indexes
      domain/
        __init__.py
        errors.py                       # WorkspaceNotFoundError, ArticleNotFoundError, ...
        repo.py                         # WorkspaceRepo, ArticleRepo (abstract)
        usecases/
          __init__.py
          create_workspace.py
          list_workspaces.py
          get_workspace.py
          delete_workspace.py
          create_article.py
          delete_article.py
          update_article_content.py
          submit_article.py
          start_review_article.py
          approve_article.py
          reject_article.py
      presentation/
        __init__.py
        deps.py                         # repo + use case providers
        routes.py
        schema.py                       # request + response models
```

## Manual verification

After implementation, smoke-check via curl against a running app:

1. Boot with `SUPERUSER_EMAIL`/`SUPERUSER_PASSWORD` set. Log in as superuser. `POST /api/v1/admin/users` with `{role: "qc", qc_product: "CL", ...}` → create a QC user. `POST /auth/register` → register a creator. `POST /auth/login` as the creator → tokens.
2. `POST /api/v1/workspaces` as creator with `{name: "A"}` → 201, returns workspace. Repeat same body → 409 with `message: "Workspace name already in use"`.
3. `GET /api/v1/workspaces?page=1&limit=12` as creator → returns own workspaces only; `items` carry `article_count` and `products`, no `articles`.
4. As creator, `POST /api/v1/workspaces/{id}/articles` with `{name: "Draft 1", product: "CL"}` → article returned with `product: "CL"`, `content: ""`, `status: "not_submitted"`.
5. `POST /api/v1/workspaces/{id}/articles` with `{name: "Draft 2", product: "FD"}` → second article with different product.
6. `GET /api/v1/workspaces/{id}` as creator → workspace with `products: ["CL", "FD"]` and both articles.
7. `PATCH /api/v1/workspaces/{id}/articles/{article_id}` with `{content: "<p>hi</p>"}` → 200 with bumped `updated_at`.
8. `POST .../submit` on the CL article → status `waiting_for_review`. Second submit → 409.
9. PATCH the submitted article again → 409 (status no longer in `{not_submitted, reviewing}`).
10. Log in as the QC(CL) user from step 1. `GET /api/v1/workspaces` → sees the creator's workspace. `GET /api/v1/workspaces/{id}` → workspace returned but `articles` only contains the CL article; `products: ["CL"]`; `article_count: 1`.
11. As QC(CL), `POST .../start-review` on the CL article → status `reviewing`, `reviewer_user_id` recorded. Try `POST .../start-review` on the FD article (still `not_submitted`) → 404 (`ArticleNotFoundError`, because FD is out of QC's scope).
12. PATCH the CL article as the original creator → 200 (reviewing is editable per spec). `POST .../approve` as QC → status `approved`, `reviewed_at` set. Further PATCH → 409.
13. Create a QC(FD) user. As QC(FD), `GET /api/v1/workspaces` → sees the same workspace (because it has an FD article). `GET /api/v1/workspaces/{id}` → returns only the FD article, `products: ["FD"]`, `article_count: 1`.
14. As QC(FD), try to access the CL article by id → 404.
15. Log in as admin. `GET /api/v1/workspaces` → sees all workspaces. `GET /api/v1/workspaces/{id}` → returns all articles (both CL and FD). Try `POST .../approve` → 403 (admin lacks `WORKSPACES_REVIEW`).
16. As creator, `DELETE /api/v1/workspaces/{id}` → 200. Verify via `GET /api/v1/workspaces/{id}` → 404 with `{success: false, message: ...}`.
17. Hit any endpoint that errors → response body is `{success: false, message: "..."}` (not `{detail: ...}`).

## Risks and rollback

- **Risk:** large PATCH content bodies exceed proxy limits in production. **Mitigation:** documented `client_max_body_size 26M` and 25 MB Uvicorn defaults. Frontend will surface a clear error message because the global envelope is applied.
- **Risk:** workspace-delete partial failure leaves orphaned articles. **Mitigation:** delete order is workspace-then-articles, so the workspace never reappears with stale articles. Orphan articles are invisible to the API. Background cleanup is a documented ops step.
- **Risk:** admin places a user into `role=qc` without `qc_product`. **Mitigation:** validation lives in the users-module admin endpoint (see roles spec); workspaces code also defends with `QcMisconfiguredError` if the user reaches it.
- **Risk:** the new global exception handler changes error bodies for *existing* routes (auth/users/admin). **Mitigation:** intentional — the frontend already expects `message` and the existing `detail` shape was unused by any consumer. Roll back by removing the `register_exception_handlers` call.
- **Risk:** `Product` enum drift between code and `__documents__/workspace.md`. **Mitigation:** the enum is the single technical source of truth; the business doc lists names and ordering. Adding a code without updating both is caught at code review.
- **Rollback:** `git revert` removes the module and the handler in one commit. No data migration; collections can be left in place or dropped manually.
