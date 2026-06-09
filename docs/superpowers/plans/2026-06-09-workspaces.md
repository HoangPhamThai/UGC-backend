# Content Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the workspaces module (Workspaces + Articles + Product enum, with QC product-scoping) and finalize the roles spec by adding `qc_product` to the user/admin surface, matching `docs/superpowers/specs/2026-06-09-workspaces-design.md` and `2026-06-09-roles-and-remove-api-keys-design.md`.

**Architecture:** Two-collection MongoDB layout (`workspaces`, `articles`). Three-axis authorization (capability via `Permission` enum, ownership via per-row checks in use cases, product scope via per-row checks for QCs). Eleven endpoints under `/api/v1/workspaces`. One global FastAPI exception handler reshapes errors to `{success, message}` for the whole app.

**Tech Stack:** Python 3.12, FastAPI 0.110, Pydantic 2.11, async pymongo 4.16, bcrypt, PyJWT.

**Testing approach:** The project intentionally has no automated test framework today (see spec "Out of scope"). Each task's verification step is one of:
- **Import-compile check** — `python -c "from <module> import <symbol>; print('ok')"` to confirm syntax/types/imports are valid. Run from the repo root with `PYTHONPATH=.` in front. If unsure: `cd /Volumes/Extreme\ SSD/ugcx/UGC/backend && PYTHONPATH=. python -c '<expr>'`.
- **Curl smoke test** — at the end (Phase G), exercise the live endpoints against a running app.

If `python` is not on PATH, use `python3`. If the working directory is wrong, `cd` to the backend root first.

**Commit cadence:** one commit per task unless explicitly grouped. Use Conventional Commits (`feat:`, `chore:`, `fix:`, `docs:`).

---

## File map

### New files (created by this plan)

```
app/core/errors.py                                      # global exception handlers
app/modules/workspaces/__init__.py
app/modules/workspaces/data/__init__.py
app/modules/workspaces/data/model.py                    # Product, ArticleStatus, Workspace, Article
app/modules/workspaces/data/repo.py                     # WorkspaceDataRepository, ArticleDataRepository, ensure_indexes
app/modules/workspaces/domain/__init__.py
app/modules/workspaces/domain/errors.py                 # domain error classes
app/modules/workspaces/domain/repo.py                   # abstract WorkspaceRepo, ArticleRepo
app/modules/workspaces/domain/usecases/__init__.py
app/modules/workspaces/domain/usecases/create_workspace.py
app/modules/workspaces/domain/usecases/list_workspaces.py
app/modules/workspaces/domain/usecases/get_workspace.py
app/modules/workspaces/domain/usecases/delete_workspace.py
app/modules/workspaces/domain/usecases/create_article.py
app/modules/workspaces/domain/usecases/delete_article.py
app/modules/workspaces/domain/usecases/update_article_content.py
app/modules/workspaces/domain/usecases/submit_article.py
app/modules/workspaces/domain/usecases/start_review_article.py
app/modules/workspaces/domain/usecases/approve_article.py
app/modules/workspaces/domain/usecases/reject_article.py
app/modules/workspaces/presentation/__init__.py
app/modules/workspaces/presentation/deps.py             # DI providers
app/modules/workspaces/presentation/routes.py
app/modules/workspaces/presentation/schema.py           # request/response models
```

### Modified files

```
app/app.py                                              # mount workspaces router; register error handlers; ensure indexes
app/core/permissions.py                                 # add WORKSPACES_* permissions
app/modules/users/data/model.py                         # add qc_product + model validator
app/modules/users/domain/usecases/create_user.py        # accept qc_product
app/modules/admin/presentation/schema.py                # qc_product in create/update/response
app/modules/admin/domain/usecases/create_managed_user.py     # pass qc_product through
app/modules/admin/domain/usecases/update_managed_user.py     # handle qc_product change
app/modules/admin/presentation/routes.py                # extra validation for qc_product on update
app/modules/users/presentation/schema.py                # UserMeResponse includes qc_product
```

The workspaces module sits alongside `users/`, `auth/`, `admin/`. Each file has one clear responsibility; use cases stay narrow so agents working on later tasks can hold one in context at a time.

---

## Phase A — Foundation (Product enum + roles-spec catch-up for qc_product)

The `Product` enum lives in the workspaces module per the spec, but the users module needs to import it for `qc_product`. So we create the workspaces skeleton first with **only the enums**, then add `qc_product` to `User`, then thread it through the admin endpoints.

---

### Task 1: Create workspaces module skeleton + enums

**Files:**
- Create: `app/modules/workspaces/__init__.py` (empty)
- Create: `app/modules/workspaces/data/__init__.py` (empty)
- Create: `app/modules/workspaces/data/model.py`
- Create: `app/modules/workspaces/domain/__init__.py` (empty)
- Create: `app/modules/workspaces/domain/usecases/__init__.py` (empty)
- Create: `app/modules/workspaces/presentation/__init__.py` (empty)

- [ ] **Step 1: Create the empty `__init__.py` files**

```bash
cd "/Volumes/Extreme SSD/ugcx/UGC/backend"
mkdir -p app/modules/workspaces/{data,domain/usecases,presentation}
touch app/modules/workspaces/__init__.py \
      app/modules/workspaces/data/__init__.py \
      app/modules/workspaces/domain/__init__.py \
      app/modules/workspaces/domain/usecases/__init__.py \
      app/modules/workspaces/presentation/__init__.py
```

- [ ] **Step 2: Create `data/model.py` with the enums only (Workspace/Article come in Task 7)**

```python
# app/modules/workspaces/data/model.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class Product(str, Enum):
    """Closed set of products. See UGC/__documents__/workspace.md §2.3.

    Adding a value requires updating the business doc first.
    """
    CL = "CL"
    MMF = "MMF"
    FD = "FD"
    PL = "PL"
    FC = "FC"
    IN = "IN"
    STOCK = "Stock"
    TRANSFER = "Transfer"
    TELCO = "Telco"
    GLOBAL = "Global"
    OTA = "OTA"
    MOVIE = "Movie"


class ArticleStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    WAITING_FOR_REVIEW = "waiting_for_review"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
```

- [ ] **Step 3: Import-compile check**

```bash
cd "/Volumes/Extreme SSD/ugcx/UGC/backend"
PYTHONPATH=. python -c "from app.modules.workspaces.data.model import Product, ArticleStatus; print(list(Product), list(ArticleStatus))"
```

Expected: prints both lists (12 products, 5 statuses) and no error.

- [ ] **Step 4: Commit**

```bash
git add app/modules/workspaces/
git commit -m "feat(workspaces): scaffold module with Product and ArticleStatus enums"
```

---

### Task 2: Add `qc_product` to User model with invariant validator

**Files:**
- Modify: `app/modules/users/data/model.py`

- [ ] **Step 1: Replace the file contents**

```python
# app/modules/users/data/model.py
from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from app.core.model import BaseMongoModel, make_prefixed_id
from app.modules.workspaces.data.model import Product


class UserRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    QC = "qc"
    CREATOR = "creator"


class User(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("u"), alias="_id")
    email: str = Field(..., description="Unique email")
    password_hashed: str = Field(..., description="Bcrypt hashed password")
    is_active: bool = Field(default=True, description="Whether user can authenticate")
    role: UserRole = Field(default=UserRole.CREATOR, description="User role")
    qc_product: Optional[Product] = Field(
        default=None,
        description="Product the QC is assigned to; required iff role=qc, must be None otherwise",
    )

    @model_validator(mode="after")
    def _check_qc_product(self) -> "User":
        if self.role == UserRole.QC and self.qc_product is None:
            raise ValueError("qc_product is required when role=qc")
        if self.role != UserRole.QC and self.qc_product is not None:
            raise ValueError("qc_product must be None when role is not qc")
        return self

    class Config:
        collection_name = "users"
```

- [ ] **Step 2: Import-compile + invariant check**

```bash
cd "/Volumes/Extreme SSD/ugcx/UGC/backend"
PYTHONPATH=. python -c "
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Product

# valid creator
u = User(email='c@x', password_hashed='h', role=UserRole.CREATOR)
print('creator ok')

# valid qc
u = User(email='q@x', password_hashed='h', role=UserRole.QC, qc_product=Product.CL)
print('qc ok')

# invalid qc with no product
try:
    User(email='q@x', password_hashed='h', role=UserRole.QC)
    raise SystemExit('FAIL: should have raised')
except ValueError as e:
    print('rejected qc without product:', e)

# invalid creator with product
try:
    User(email='c@x', password_hashed='h', role=UserRole.CREATOR, qc_product=Product.CL)
    raise SystemExit('FAIL: should have raised')
except ValueError as e:
    print('rejected creator with product:', e)
"
```

Expected output: four lines confirming each case.

- [ ] **Step 3: Commit**

```bash
git add app/modules/users/data/model.py
git commit -m "feat(users): add qc_product with role-aware invariant"
```

---

### Task 3: Update `CreateUserUseCase` to accept `qc_product`

**Files:**
- Modify: `app/modules/users/domain/usecases/create_user.py`

- [ ] **Step 1: Replace `execute()` and the User construction**

```python
# app/modules/users/domain/usecases/create_user.py
import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_password
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.workspaces.data.model import Product


@dataclass(frozen=True)
class CreateUserUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(
        self,
        *,
        email: str,
        password: str,
        role: UserRole = UserRole.CREATOR,
        qc_product: Optional[Product] = None,
    ) -> User:
        try:
            existing = await self.user_repo.get_by_email(email)
            if existing is not None:
                raise ValueError(f"Email already registered: {email}")

            user = User(
                email=email,
                password_hashed=hash_password(password),
                role=role,
                qc_product=qc_product,
            )
            created = await self.user_repo.create(user)
            self.log_info(
                f"User created: id={created.id} role={created.role.value} "
                f"qc_product={created.qc_product.value if created.qc_product else None}"
            )
            return created
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"CreateUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create user: {str(e)}") from e
```

- [ ] **Step 2: Import-compile check**

```bash
cd "/Volumes/Extreme SSD/ugcx/UGC/backend"
PYTHONPATH=. python -c "from app.modules.users.domain.usecases.create_user import CreateUserUseCase; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add app/modules/users/domain/usecases/create_user.py
git commit -m "feat(users): create_user accepts qc_product"
```

---

### Task 4: Thread `qc_product` through `CreateManagedUserUseCase`

**Files:**
- Modify: `app/modules/admin/domain/usecases/create_managed_user.py`

- [ ] **Step 1: Replace the file**

```python
# app/modules/admin/domain/usecases/create_managed_user.py
import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.workspaces.data.model import Product


@dataclass(frozen=True)
class CreateManagedUserUseCase(LoggerMixin):
    uc_create_user: CreateUserUseCase

    async def execute(
        self,
        *,
        email: str,
        password: str,
        role: UserRole,
        qc_product: Optional[Product] = None,
    ) -> User:
        try:
            if role not in (UserRole.ADMIN, UserRole.QC):
                raise ValueError(
                    f"Cannot create user with role '{role.value}' via this endpoint"
                )
            # The User model_validator already enforces the qc_product invariant,
            # but raising here gives a cleaner error before hashing the password.
            if role == UserRole.QC and qc_product is None:
                raise ValueError("qc_product is required when role=qc")
            if role != UserRole.QC and qc_product is not None:
                raise ValueError("qc_product must be None when role is not qc")

            return await self.uc_create_user.execute(
                email=email, password=password, role=role, qc_product=qc_product
            )
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"CreateManagedUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create user: {str(e)}") from e
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.admin.domain.usecases.create_managed_user import CreateManagedUserUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/admin/domain/usecases/create_managed_user.py
git commit -m "feat(admin): create_managed_user accepts qc_product"
```

---

### Task 5: Allow updating `qc_product` via `UpdateManagedUserUseCase`

**Files:**
- Modify: `app/modules/admin/domain/usecases/update_managed_user.py`

- [ ] **Step 1: Replace the file**

```python
# app/modules/admin/domain/usecases/update_managed_user.py
import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_password
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.workspaces.data.model import Product


@dataclass(frozen=True)
class UpdateManagedUserUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(
        self,
        *,
        user_id: str,
        is_active: Optional[bool],
        password: Optional[str],
        qc_product: Optional[Product] = None,
        qc_product_provided: bool = False,
    ) -> Optional[User]:
        """Update a managed user.

        `qc_product_provided=True` means the caller explicitly sent the field
        (even if its value is None); only then do we touch it. This avoids
        accidentally clearing qc_product when callers omit the field.
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                return None

            if is_active is not None:
                user.is_active = is_active
            if password is not None:
                user.password_hashed = hash_password(password)
            if qc_product_provided:
                if user.role != UserRole.QC:
                    raise ValueError("qc_product can only be set on QC users")
                if qc_product is None:
                    raise ValueError("qc_product cannot be cleared on a QC user")
                user.qc_product = qc_product

            updated = await self.user_repo.update(user)
            self.log_info(
                f"User updated: id={updated.id} role={updated.role.value} "
                f"qc_product={updated.qc_product.value if updated.qc_product else None}"
            )
            return updated
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"UpdateManagedUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to update user: {str(e)}") from e
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.admin.domain.usecases.update_managed_user import UpdateManagedUserUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/admin/domain/usecases/update_managed_user.py
git commit -m "feat(admin): update_managed_user supports qc_product change"
```

---

### Task 6: Update admin schemas to surface `qc_product`

**Files:**
- Modify: `app/modules/admin/presentation/schema.py`

- [ ] **Step 1: Replace the file**

```python
# app/modules/admin/presentation/schema.py
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import Product


# --- Requests ---


class CreateManagedUserRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    role: Literal[UserRole.ADMIN, UserRole.QC] = Field(
        ..., description="Role to assign; only 'admin' or 'qc' are accepted"
    )
    qc_product: Optional[Product] = Field(
        default=None,
        description="Required when role=qc, must be omitted/null otherwise",
    )


class UpdateManagedUserRequest(BaseModel):
    is_active: Optional[bool] = Field(
        default=None, description="Set false to soft-deactivate"
    )
    password: Optional[str] = Field(
        default=None, min_length=8, description="New password"
    )
    qc_product: Optional[Product] = Field(
        default=None,
        description="Reassign the QC to a different product (only valid for QC users)",
    )


# --- Responses ---


class ManagedUserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    qc_product: Optional[Product] = None
    is_active: bool
    created_at: datetime


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "
from app.modules.admin.presentation.schema import (
    CreateManagedUserRequest, UpdateManagedUserRequest, ManagedUserResponse
)
print('ok')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/admin/presentation/schema.py
git commit -m "feat(admin): expose qc_product in admin request/response schemas"
```

---

### Task 7: Wire `qc_product` through admin routes

**Files:**
- Modify: `app/modules/admin/presentation/routes.py`

- [ ] **Step 1: Update `_to_response` and the create/update handlers**

Find the existing `_to_response`:

```python
def _to_response(user: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
```

Replace with:

```python
def _to_response(user: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        qc_product=user.qc_product,
        is_active=user.is_active,
        created_at=user.created_at,
    )
```

In `create_managed_user`, find:

```python
        user = await uc.execute(
            email=body.email, password=body.password, role=body.role
        )
```

Replace with:

```python
        user = await uc.execute(
            email=body.email,
            password=body.password,
            role=body.role,
            qc_product=body.qc_product,
        )
```

In `update_user`, find the body parsing & the `uc_update.execute` call:

```python
        updated = await uc_update.execute(
            user_id=user_id,
            is_active=body.is_active,
            password=body.password,
        )
```

Replace with:

```python
        # Detect whether qc_product was explicitly present in the request body
        # (`exclude_unset=True` returns the dict keys the client actually sent).
        qc_provided = "qc_product" in body.model_dump(exclude_unset=True)
        try:
            updated = await uc_update.execute(
                user_id=user_id,
                is_active=body.is_active,
                password=body.password,
                qc_product=body.qc_product,
                qc_product_provided=qc_provided,
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
            )
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.admin.presentation.routes import router; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/admin/presentation/routes.py
git commit -m "feat(admin): plumb qc_product through admin routes"
```

---

### Task 8: Expose `qc_product` in `UserMeResponse`

**Files:**
- Modify: `app/modules/users/presentation/schema.py`

- [ ] **Step 1: Replace the file**

```python
# app/modules/users/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import Product


class UserMeResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    role: UserRole
    qc_product: Optional[Product] = None
    created_at: datetime
```

- [ ] **Step 2: Find existing `UserMeResponse` usage and update it**

```bash
grep -RIn "UserMeResponse" app/
```

Expect to find construction in `app/modules/users/presentation/routes.py`. Update that constructor call to include `qc_product=current_user.qc_product` alongside the other fields.

Open the file, find the constructor call (the only one), and add `qc_product=current_user.qc_product,` as one more keyword argument.

- [ ] **Step 3: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.users.presentation.routes import router; print('ok')"
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/users/presentation/schema.py app/modules/users/presentation/routes.py
git commit -m "feat(users): include qc_product in /users/me response"
```

---

## Phase B — Workspaces models & domain errors

---

### Task 9: Add `Workspace` and `Article` to `data/model.py`

**Files:**
- Modify: `app/modules/workspaces/data/model.py`

- [ ] **Step 1: Append `Workspace` and `Article` to the existing file**

Open `app/modules/workspaces/data/model.py` (from Task 1) and append after the enums:

```python
class Workspace(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ws"), alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    name_lower: str = Field(..., description="Lowercased name for unique index")
    owner_user_id: str = Field(..., description="Owning creator user id")

    class Config:
        collection_name = "workspaces"


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

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "
from app.modules.workspaces.data.model import Workspace, Article, Product, ArticleStatus
w = Workspace(name='X', name_lower='x', owner_user_id='u_1')
print('ws:', w.id, w.name, w.owner_user_id)
a = Article(workspace_id=w.id, name='Draft', product=Product.CL)
print('article:', a.id, a.product, a.status, a.content == '')
"
```

Expected: prints workspace and article fields successfully.

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/data/model.py
git commit -m "feat(workspaces): add Workspace and Article Mongo models"
```

---

### Task 10: Domain errors

**Files:**
- Create: `app/modules/workspaces/domain/errors.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/errors.py
class WorkspaceError(Exception):
    """Base class for all workspace-domain errors."""


class WorkspaceNotFoundError(WorkspaceError):
    """Workspace does not exist, or caller may not see it. Maps to 404."""

    def __init__(self, message: str = "Workspace not found") -> None:
        super().__init__(message)


class ArticleNotFoundError(WorkspaceError):
    """Article does not exist, is not in the requested workspace, or out of caller's scope. Maps to 404."""

    def __init__(self, message: str = "Article not found") -> None:
        super().__init__(message)


class WorkspaceNameTakenError(WorkspaceError):
    """Owner already has a workspace with this name (case-insensitive). Maps to 409."""

    def __init__(self, message: str = "Workspace name already in use") -> None:
        super().__init__(message)


class ArticleStateConflictError(WorkspaceError):
    """Article is not in a state that allows this operation. Maps to 409."""

    def __init__(self, message: str = "Article is not in a valid state for this operation") -> None:
        super().__init__(message)


class QcMisconfiguredError(WorkspaceError):
    """A QC user reached workspaces code with no qc_product. Data-integrity error. Maps to 500."""

    def __init__(self, message: str = "QC user has no qc_product assigned") -> None:
        super().__init__(message)
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.errors import WorkspaceNotFoundError; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/errors.py
git commit -m "feat(workspaces): domain errors"
```

---

## Phase C — Permissions & global error envelope

---

### Task 11: Add `WORKSPACES_*` permissions and role mappings

**Files:**
- Modify: `app/core/permissions.py`

- [ ] **Step 1: Add the new enum values**

Find the existing `Permission` class. Add the four new entries at the end:

```python
class Permission(str, Enum):
    USERS_CREATE_ADMIN = "users:create:admin"
    USERS_CREATE_QC = "users:create:qc"
    USERS_READ_ADMIN = "users:read:admin"
    USERS_READ_QC = "users:read:qc"
    USERS_READ_CREATOR = "users:read:creator"
    USERS_UPDATE_ADMIN = "users:update:admin"
    USERS_UPDATE_QC = "users:update:qc"
    USERS_UPDATE_CREATOR = "users:update:creator"
    WORKSPACES_CREATE = "workspaces:create"
    WORKSPACES_READ_ANY = "workspaces:read:any"
    WORKSPACES_READ_BY_PRODUCT = "workspaces:read:by_product"
    WORKSPACES_REVIEW = "workspaces:review"
```

- [ ] **Step 2: Extend the `ROLE_PERMISSIONS` map**

Replace the existing `ROLE_PERMISSIONS` dict with:

```python
ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.SUPERUSER: frozenset(Permission),
    UserRole.ADMIN: frozenset(
        {
            Permission.USERS_CREATE_QC,
            Permission.USERS_READ_QC,
            Permission.USERS_READ_CREATOR,
            Permission.USERS_UPDATE_QC,
            Permission.WORKSPACES_READ_ANY,
        }
    ),
    UserRole.QC: frozenset(
        {
            Permission.USERS_READ_CREATOR,
            Permission.WORKSPACES_READ_BY_PRODUCT,
            Permission.WORKSPACES_REVIEW,
        }
    ),
    UserRole.CREATOR: frozenset({Permission.WORKSPACES_CREATE}),
}
```

- [ ] **Step 3: Import-compile + sanity check**

```bash
PYTHONPATH=. python -c "
from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.modules.users.data.model import UserRole
assert Permission.WORKSPACES_REVIEW in ROLE_PERMISSIONS[UserRole.QC]
assert Permission.WORKSPACES_REVIEW not in ROLE_PERMISSIONS[UserRole.ADMIN]
assert Permission.WORKSPACES_REVIEW in ROLE_PERMISSIONS[UserRole.SUPERUSER]
assert Permission.WORKSPACES_CREATE in ROLE_PERMISSIONS[UserRole.CREATOR]
assert Permission.WORKSPACES_READ_ANY in ROLE_PERMISSIONS[UserRole.ADMIN]
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add app/core/permissions.py
git commit -m "feat(permissions): add workspaces permissions and role mappings"
```

---

### Task 12: Create global error envelope handler

**Files:**
- Create: `app/core/errors.py`

- [ ] **Step 1: Create the file**

```python
# app/core/errors.py
"""Global exception handlers that reshape every error response to the
frontend's standard {success: false, message: ...} envelope."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
    WorkspaceError,
    WorkspaceNameTakenError,
    WorkspaceNotFoundError,
)


def _envelope(message: str) -> dict:
    return {"success": False, "message": message}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content=_envelope(message))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = first.get("msg", "Invalid request")
        if loc:
            message = f"{loc}: {message}"
    else:
        message = "Invalid request"
    return JSONResponse(status_code=422, content=_envelope(message))


_DOMAIN_STATUS: dict[type[WorkspaceError], int] = {
    WorkspaceNotFoundError: 404,
    ArticleNotFoundError: 404,
    WorkspaceNameTakenError: 409,
    ArticleStateConflictError: 409,
    QcMisconfiguredError: 500,
}


async def domain_exception_handler(request: Request, exc: Exception):
    status_code = _DOMAIN_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    for exc_cls in _DOMAIN_STATUS:
        app.add_exception_handler(exc_cls, domain_exception_handler)
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.core.errors import register_exception_handlers; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/core/errors.py
git commit -m "feat(core): global exception handlers reshaping errors to {success,message}"
```

---

## Phase D — Workspaces repositories

---

### Task 13: Abstract `WorkspaceRepo` and `ArticleRepo`

**Files:**
- Create: `app/modules/workspaces/domain/repo.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/repo.py
from abc import ABC, abstractmethod
from typing import Optional

from app.modules.workspaces.data.model import Article, ArticleStatus, Product, Workspace


class WorkspaceRepo(ABC):

    @abstractmethod
    async def create(self, workspace: Workspace) -> Workspace: ...

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]: ...

    @abstractmethod
    async def list_by_owner(
        self, owner_user_id: str, *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_by_owner(self, owner_user_id: str) -> int: ...

    @abstractmethod
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def list_with_product(
        self, product: Product, *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_with_product(self, product: Product) -> int: ...

    @abstractmethod
    async def delete(self, workspace_id: str) -> None: ...

    @abstractmethod
    async def article_counts(
        self, workspace_ids: list[str], *, product: Optional[Product] = None
    ) -> dict[str, int]: ...

    @abstractmethod
    async def products_for(self, workspace_ids: list[str]) -> dict[str, list[Product]]: ...


class ArticleRepo(ABC):

    @abstractmethod
    async def create(self, article: Article) -> Article: ...

    @abstractmethod
    async def get_by_id(self, article_id: str) -> Optional[Article]: ...

    @abstractmethod
    async def list_by_workspace(
        self, workspace_id: str, *, product: Optional[Product] = None
    ) -> list[Article]: ...

    @abstractmethod
    async def workspace_has_product(self, workspace_id: str, product: Product) -> bool: ...

    @abstractmethod
    async def update_content(self, article_id: str, content: str) -> Optional[Article]: ...

    @abstractmethod
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
    ) -> Optional[Article]: ...

    @abstractmethod
    async def delete(self, article_id: str) -> None: ...

    @abstractmethod
    async def delete_by_workspace(self, workspace_id: str) -> int: ...
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.repo import WorkspaceRepo, ArticleRepo; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/repo.py
git commit -m "feat(workspaces): abstract WorkspaceRepo and ArticleRepo"
```

---

### Task 14: Mongo implementations (`WorkspaceDataRepository`, `ArticleDataRepository`)

**Files:**
- Create: `app/modules/workspaces/data/repo.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import Article, ArticleStatus, Product, Workspace
from app.modules.workspaces.domain.errors import WorkspaceNameTakenError
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


# --- Workspaces ---


class WorkspaceDataRepository(LoggerMixin, WorkspaceRepo):
    def __init__(self) -> None:
        self.collection_name: str = Workspace.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("owner_user_id", ASCENDING)])
        await coll.create_index(
            [("owner_user_id", ASCENDING), ("name_lower", ASCENDING)],
            unique=True,
            name="uniq_owner_name_lower",
        )

    @override
    async def create(self, workspace: Workspace) -> Workspace:
        coll = await self._get_collection()
        # Repo owns name_lower normalization; callers never set it.
        workspace.name_lower = workspace.name.casefold()
        payload = workspace.model_dump(by_alias=True)
        try:
            await coll.insert_one(payload)
        except DuplicateKeyError:
            raise WorkspaceNameTakenError()
        return workspace

    @override
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": workspace_id})
        return Workspace.model_validate(doc) if doc else None

    @override
    async def list_by_owner(
        self, owner_user_id: str, *, skip: int, limit: int
    ) -> list[Workspace]:
        coll = await self._get_collection()
        cursor = (
            coll.find({"owner_user_id": owner_user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_by_owner(self, owner_user_id: str) -> int:
        coll = await self._get_collection()
        return await coll.count_documents({"owner_user_id": owner_user_id})

    @override
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]:
        coll = await self._get_collection()
        cursor = coll.find({}).sort("updated_at", -1).skip(skip).limit(limit)
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_all(self) -> int:
        coll = await self._get_collection()
        return await coll.count_documents({})

    @override
    async def list_with_product(
        self, product: Product, *, skip: int, limit: int
    ) -> list[Workspace]:
        # Find workspace ids that have at least one article of `product`.
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": product.value}
        )
        if not ids:
            return []
        coll = await self._get_collection()
        cursor = (
            coll.find({"_id": {"$in": ids}})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_with_product(self, product: Product) -> int:
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": product.value}
        )
        return len(ids)

    @override
    async def delete(self, workspace_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": workspace_id})

    @override
    async def article_counts(
        self, workspace_ids: list[str], *, product: Optional[Product] = None
    ) -> dict[str, int]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        match: dict = {"workspace_id": {"$in": workspace_ids}}
        if product is not None:
            match["product"] = product.value
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$workspace_id", "c": {"$sum": 1}}},
        ]
        result: dict[str, int] = {wid: 0 for wid in workspace_ids}
        async for row in article_coll.aggregate(pipeline):
            result[row["_id"]] = row["c"]
        return result

    @override
    async def products_for(self, workspace_ids: list[str]) -> dict[str, list[Product]]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        pipeline = [
            {"$match": {"workspace_id": {"$in": workspace_ids}}},
            {"$group": {"_id": "$workspace_id", "products": {"$addToSet": "$product"}}},
        ]
        result: dict[str, list[Product]] = {wid: [] for wid in workspace_ids}
        async for row in article_coll.aggregate(pipeline):
            result[row["_id"]] = sorted(
                (Product(p) for p in row["products"]),
                key=lambda p: list(Product).index(p),
            )
        return result


# --- Articles ---


class ArticleDataRepository(LoggerMixin, ArticleRepo):
    def __init__(self) -> None:
        self.collection_name: str = Article.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("workspace_id", ASCENDING), ("created_at", ASCENDING)])
        await coll.create_index([("workspace_id", ASCENDING), ("product", ASCENDING)])
        await coll.create_index([("product", ASCENDING), ("status", ASCENDING)])

    @override
    async def create(self, article: Article) -> Article:
        coll = await self._get_collection()
        payload = article.model_dump(by_alias=True)
        await coll.insert_one(payload)
        return article

    @override
    async def get_by_id(self, article_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": article_id})
        return Article.model_validate(doc) if doc else None

    @override
    async def list_by_workspace(
        self, workspace_id: str, *, product: Optional[Product] = None
    ) -> list[Article]:
        coll = await self._get_collection()
        filt: dict = {"workspace_id": workspace_id}
        if product is not None:
            filt["product"] = product.value
        cursor = coll.find(filt).sort("created_at", ASCENDING)
        docs = [doc async for doc in cursor]
        return [Article.model_validate(d) for d in docs]

    @override
    async def workspace_has_product(self, workspace_id: str, product: Product) -> bool:
        coll = await self._get_collection()
        doc = await coll.find_one(
            {"workspace_id": workspace_id, "product": product.value},
            projection={"_id": 1},
        )
        return doc is not None

    @override
    async def update_content(self, article_id: str, content: str) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": {"content": content, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        update: dict = {"status": status.value, "updated_at": now}
        if reviewer_user_id is not None:
            update["reviewer_user_id"] = reviewer_user_id
        if set_reviewed_at:
            update["reviewed_at"] = now
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def delete(self, article_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": article_id})

    @override
    async def delete_by_workspace(self, workspace_id: str) -> int:
        coll = await self._get_collection()
        result = await coll.delete_many({"workspace_id": workspace_id})
        return result.deleted_count
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "
from app.modules.workspaces.data.repo import WorkspaceDataRepository, ArticleDataRepository
print('ok')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/data/repo.py
git commit -m "feat(workspaces): Mongo data repositories with indexes"
```

---

## Phase E — Use cases

Each use case lives in its own file. Routes will be thin; all authorization and state-transition logic lives here. The check ordering for review-flow use cases follows the spec's "Check ordering for review-flow use cases" section: load → workspace-id match → product scope (skip for superuser) → status → apply.

---

### Task 15: `create_workspace` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/create_workspace.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/create_workspace.py
import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import Workspace
from app.modules.workspaces.domain.repo import WorkspaceRepo


@dataclass(frozen=True)
class CreateWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo

    async def execute(self, *, name: str, owner_user_id: str) -> Workspace:
        try:
            trimmed = name.strip()
            if not trimmed:
                raise ValueError("name must not be empty")
            workspace = Workspace(
                name=trimmed,
                name_lower=trimmed.casefold(),
                owner_user_id=owner_user_id,
            )
            created = await self.workspace_repo.create(workspace)
            self.log_info(f"Workspace created: id={created.id} owner={owner_user_id}")
            return created
        except Exception as e:
            # Let WorkspaceNameTakenError, ValueError, etc. bubble unchanged.
            if isinstance(e, (ValueError,)):
                raise
            from app.modules.workspaces.domain.errors import WorkspaceError
            if isinstance(e, WorkspaceError):
                raise
            self.log_exception(f"CreateWorkspaceUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.create_workspace import CreateWorkspaceUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/create_workspace.py
git commit -m "feat(workspaces): create_workspace use case"
```

---

### Task 16: `list_workspaces` use case (branched by permission)

**Files:**
- Create: `app/modules/workspaces/domain/usecases/list_workspaces.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/list_workspaces.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.core.permissions import Permission, has_permission
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Product, Workspace
from app.modules.workspaces.domain.errors import QcMisconfiguredError
from app.modules.workspaces.domain.repo import WorkspaceRepo


@dataclass(frozen=True)
class ListWorkspacesResult:
    items: list[Workspace]
    total: int
    article_counts: dict[str, int]
    products_by_ws: dict[str, list[Product]]


@dataclass(frozen=True)
class ListWorkspacesUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo

    async def execute(
        self, *, caller: User, page: int, limit: int
    ) -> ListWorkspacesResult:
        skip = (page - 1) * limit
        repo = self.workspace_repo

        if has_permission(caller, Permission.WORKSPACES_READ_ANY):
            workspaces = await repo.list_all(skip=skip, limit=limit)
            total = await repo.count_all()
            ids = [w.id for w in workspaces]
            counts = await repo.article_counts(ids)
            products = await repo.products_for(ids)
            return ListWorkspacesResult(workspaces, total, counts, products)

        if has_permission(caller, Permission.WORKSPACES_READ_BY_PRODUCT):
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            p = caller.qc_product
            workspaces = await repo.list_with_product(p, skip=skip, limit=limit)
            total = await repo.count_with_product(p)
            ids = [w.id for w in workspaces]
            counts = await repo.article_counts(ids, product=p)
            products = {wid: [p] for wid in ids}
            return ListWorkspacesResult(workspaces, total, counts, products)

        # Creator (default): own workspaces only.
        workspaces = await repo.list_by_owner(caller.id, skip=skip, limit=limit)
        total = await repo.count_by_owner(caller.id)
        ids = [w.id for w in workspaces]
        counts = await repo.article_counts(ids)
        products = await repo.products_for(ids)
        return ListWorkspacesResult(workspaces, total, counts, products)
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.list_workspaces import ListWorkspacesUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/list_workspaces.py
git commit -m "feat(workspaces): list_workspaces use case with role branching"
```

---

### Task 17: `get_workspace` use case (detail + scope-filtered articles)

**Files:**
- Create: `app/modules/workspaces/domain/usecases/get_workspace.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/get_workspace.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.permissions import Permission, has_permission
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, Product, Workspace
from app.modules.workspaces.domain.errors import (
    QcMisconfiguredError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class GetWorkspaceResult:
    workspace: Workspace
    articles: list[Article]
    products: list[Product]


@dataclass(frozen=True)
class GetWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(self, *, workspace_id: str, caller: User) -> GetWorkspaceResult:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None:
            raise WorkspaceNotFoundError()

        # Owner sees everything in their workspace.
        if caller.id == ws.owner_user_id:
            articles = await self.article_repo.list_by_workspace(workspace_id)
            products = self._distinct_products(articles)
            return GetWorkspaceResult(ws, articles, products)

        # Admin / superuser: see everything.
        if has_permission(caller, Permission.WORKSPACES_READ_ANY):
            articles = await self.article_repo.list_by_workspace(workspace_id)
            products = self._distinct_products(articles)
            return GetWorkspaceResult(ws, articles, products)

        # QC: scoped to their product.
        if has_permission(caller, Permission.WORKSPACES_READ_BY_PRODUCT):
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if not await self.article_repo.workspace_has_product(
                workspace_id, caller.qc_product
            ):
                # Workspace exists but is invisible to this QC.
                raise WorkspaceNotFoundError()
            articles = await self.article_repo.list_by_workspace(
                workspace_id, product=caller.qc_product
            )
            return GetWorkspaceResult(ws, articles, [caller.qc_product])

        # Anyone else (e.g. another creator).
        raise WorkspaceNotFoundError()

    @staticmethod
    def _distinct_products(articles: list[Article]) -> list[Product]:
        unique = {a.product for a in articles}
        return sorted(unique, key=lambda p: list(Product).index(p))
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.get_workspace import GetWorkspaceUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/get_workspace.py
git commit -m "feat(workspaces): get_workspace use case with QC product scoping"
```

---

### Task 18: `delete_workspace` use case (cascade)

**Files:**
- Create: `app/modules/workspaces/domain/usecases/delete_workspace.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/delete_workspace.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.domain.errors import WorkspaceNotFoundError
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class DeleteWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(self, *, workspace_id: str, caller: User) -> None:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            # Hide existence for non-owners (404, not 403).
            raise WorkspaceNotFoundError()

        await self.workspace_repo.delete(workspace_id)
        deleted = await self.article_repo.delete_by_workspace(workspace_id)
        self.log_info(
            f"Workspace deleted: id={workspace_id} cascade_articles={deleted}"
        )
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.delete_workspace import DeleteWorkspaceUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/delete_workspace.py
git commit -m "feat(workspaces): delete_workspace cascades to articles"
```

---

### Task 19: `create_article` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/create_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/create_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus, Product
from app.modules.workspaces.domain.errors import WorkspaceNotFoundError
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class CreateArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self,
        *,
        workspace_id: str,
        name: str,
        product: Product,
        caller: User,
    ) -> Article:
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("name must not be empty")

        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = Article(
            workspace_id=workspace_id,
            name=trimmed,
            product=product,
            content="",
            status=ArticleStatus.NOT_SUBMITTED,
        )
        created = await self.article_repo.create(article)
        self.log_info(
            f"Article created: id={created.id} ws={workspace_id} product={product.value}"
        )
        return created
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.create_article import CreateArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/create_article.py
git commit -m "feat(workspaces): create_article use case"
```

---

### Task 20: `delete_article` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/delete_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/delete_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class DeleteArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> None:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        await self.article_repo.delete(article_id)
        self.log_info(f"Article deleted: id={article_id} ws={workspace_id}")
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.delete_article import DeleteArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/delete_article.py
git commit -m "feat(workspaces): delete_article use case"
```

---

### Task 21: `update_article_content` use case (autosave)

**Files:**
- Create: `app/modules/workspaces/domain/usecases/update_article_content.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/update_article_content.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


_EDITABLE_STATUSES = {ArticleStatus.NOT_SUBMITTED, ArticleStatus.REVIEWING}


@dataclass(frozen=True)
class UpdateArticleContentUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self,
        *,
        workspace_id: str,
        article_id: str,
        content: str,
        caller: User,
    ) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.status not in _EDITABLE_STATUSES:
            raise ArticleStateConflictError(
                "Article is not in an editable state"
            )

        updated = await self.article_repo.update_content(article_id, content)
        if updated is None:
            raise ArticleNotFoundError()
        return updated
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.update_article_content import UpdateArticleContentUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/update_article_content.py
git commit -m "feat(workspaces): update_article_content (autosave) use case"
```

---

### Task 22: `submit_article` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/submit_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/submit_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class SubmitArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.status != ArticleStatus.NOT_SUBMITTED:
            raise ArticleStateConflictError(
                "Article is not in a submittable state"
            )

        updated = await self.article_repo.update_status(
            article_id, status=ArticleStatus.WAITING_FOR_REVIEW
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article submitted: id={article_id}")
        return updated
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.submit_article import SubmitArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/submit_article.py
git commit -m "feat(workspaces): submit_article use case"
```

---

### Task 23: `start_review_article` use case

Check ordering per spec: load → workspace-id match → **product scope (skip for superuser)** → status → apply.

**Files:**
- Create: `app/modules/workspaces/domain/usecases/start_review_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/start_review_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
)
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class StartReviewArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        # 1. Load
        article = await self.article_repo.get_by_id(article_id)
        # 2. Workspace-id match
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        # 3. Product scope — skip for superuser; required for QC
        if caller.role != UserRole.SUPERUSER:
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if article.product != caller.qc_product:
                # Hide existence: same 404 as missing article.
                raise ArticleNotFoundError()
        # 4. Status
        if article.status != ArticleStatus.WAITING_FOR_REVIEW:
            raise ArticleStateConflictError(
                "Article is not waiting for review"
            )
        # 5. Apply
        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.REVIEWING,
            reviewer_user_id=caller.id,
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article moved to reviewing: id={article_id} reviewer={caller.id}")
        return updated
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.start_review_article import StartReviewArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/start_review_article.py
git commit -m "feat(workspaces): start_review_article use case with scoped check ordering"
```

---

### Task 24: `approve_article` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/approve_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/approve_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
)
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class ApproveArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        if caller.role != UserRole.SUPERUSER:
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if article.product != caller.qc_product:
                raise ArticleNotFoundError()
        if article.status != ArticleStatus.REVIEWING:
            raise ArticleStateConflictError("Article is not in a reviewable state")
        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.APPROVED,
            set_reviewed_at=True,
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article approved: id={article_id} reviewer={caller.id}")
        return updated
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.approve_article import ApproveArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/approve_article.py
git commit -m "feat(workspaces): approve_article use case"
```

---

### Task 25: `reject_article` use case

**Files:**
- Create: `app/modules/workspaces/domain/usecases/reject_article.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/domain/usecases/reject_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
)
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class RejectArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        if caller.role != UserRole.SUPERUSER:
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if article.product != caller.qc_product:
                raise ArticleNotFoundError()
        if article.status != ArticleStatus.REVIEWING:
            raise ArticleStateConflictError("Article is not in a reviewable state")
        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.REJECTED,
            set_reviewed_at=True,
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article rejected: id={article_id} reviewer={caller.id}")
        return updated
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.domain.usecases.reject_article import RejectArticleUseCase; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/domain/usecases/reject_article.py
git commit -m "feat(workspaces): reject_article use case"
```

---

## Phase F — Presentation

---

### Task 26: Request and response schemas

**Files:**
- Create: `app/modules/workspaces/presentation/schema.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.modules.workspaces.data.model import (
    Article,
    ArticleStatus,
    Product,
    Workspace,
)


# --- Requests ---


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CreateArticleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    product: Product


class UpdateArticleContentRequest(BaseModel):
    content: str = Field(default="")


# --- Responses ---


def _to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class ArticleResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    workspace_id: str
    name: str
    product: Product
    content: str
    status: ArticleStatus
    created_at: int
    updated_at: int

    @classmethod
    def from_model(cls, article: Article) -> "ArticleResponse":
        return cls(
            id=article.id,
            workspace_id=article.workspace_id,
            name=article.name,
            product=article.product,
            content=article.content,
            status=article.status,
            created_at=_to_epoch_ms(article.created_at),
            updated_at=_to_epoch_ms(article.updated_at),
        )


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
    ) -> "WorkspaceResponse":
        return cls(
            id=ws.id,
            name=ws.name,
            owner_user_id=ws.owner_user_id,
            created_at=_to_epoch_ms(ws.created_at),
            updated_at=_to_epoch_ms(ws.updated_at),
            article_count=article_count,
            products=products,
            articles=[ArticleResponse.from_model(a) for a in articles]
            if articles is not None
            else None,
        )


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "
from app.modules.workspaces.presentation.schema import (
    CreateWorkspaceRequest, CreateArticleRequest, UpdateArticleContentRequest,
    ArticleResponse, WorkspaceResponse, WorkspaceListResponse
)
print('ok')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/presentation/schema.py
git commit -m "feat(workspaces): request and response schemas (epoch-ms timestamps)"
```

---

### Task 27: Dependency providers

**Files:**
- Create: `app/modules/workspaces/presentation/deps.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/presentation/deps.py
from functools import lru_cache

from app.modules.workspaces.data.repo import (
    ArticleDataRepository,
    WorkspaceDataRepository,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo
from app.modules.workspaces.domain.usecases.approve_article import ApproveArticleUseCase
from app.modules.workspaces.domain.usecases.create_article import CreateArticleUseCase
from app.modules.workspaces.domain.usecases.create_workspace import (
    CreateWorkspaceUseCase,
)
from app.modules.workspaces.domain.usecases.delete_article import DeleteArticleUseCase
from app.modules.workspaces.domain.usecases.delete_workspace import (
    DeleteWorkspaceUseCase,
)
from app.modules.workspaces.domain.usecases.get_workspace import GetWorkspaceUseCase
from app.modules.workspaces.domain.usecases.list_workspaces import (
    ListWorkspacesUseCase,
)
from app.modules.workspaces.domain.usecases.reject_article import RejectArticleUseCase
from app.modules.workspaces.domain.usecases.start_review_article import (
    StartReviewArticleUseCase,
)
from app.modules.workspaces.domain.usecases.submit_article import SubmitArticleUseCase
from app.modules.workspaces.domain.usecases.update_article_content import (
    UpdateArticleContentUseCase,
)


@lru_cache(maxsize=1)
def get_workspace_repo() -> WorkspaceRepo:
    return WorkspaceDataRepository()


@lru_cache(maxsize=1)
def get_article_repo() -> ArticleRepo:
    return ArticleDataRepository()


def get_uc_create_workspace() -> CreateWorkspaceUseCase:
    return CreateWorkspaceUseCase(workspace_repo=get_workspace_repo())


def get_uc_list_workspaces() -> ListWorkspacesUseCase:
    return ListWorkspacesUseCase(workspace_repo=get_workspace_repo())


def get_uc_get_workspace() -> GetWorkspaceUseCase:
    return GetWorkspaceUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_delete_workspace() -> DeleteWorkspaceUseCase:
    return DeleteWorkspaceUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_create_article() -> CreateArticleUseCase:
    return CreateArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_delete_article() -> DeleteArticleUseCase:
    return DeleteArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_update_article_content() -> UpdateArticleContentUseCase:
    return UpdateArticleContentUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_submit_article() -> SubmitArticleUseCase:
    return SubmitArticleUseCase(
        workspace_repo=get_workspace_repo(),
        article_repo=get_article_repo(),
    )


def get_uc_start_review_article() -> StartReviewArticleUseCase:
    return StartReviewArticleUseCase(article_repo=get_article_repo())


def get_uc_approve_article() -> ApproveArticleUseCase:
    return ApproveArticleUseCase(article_repo=get_article_repo())


def get_uc_reject_article() -> RejectArticleUseCase:
    return RejectArticleUseCase(article_repo=get_article_repo())
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.presentation.deps import get_uc_create_workspace; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/presentation/deps.py
git commit -m "feat(workspaces): DI providers for repos and use cases"
```

---

### Task 28: HTTP routes

**Files:**
- Create: `app/modules/workspaces/presentation/routes.py`

- [ ] **Step 1: Create the file**

```python
# app/modules/workspaces/presentation/routes.py
from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.core.auth import get_current_user
from app.core.model import StandardResponse, create_success_response
from app.core.permissions import Permission, require_permissions
from app.modules.users.data.model import User
from app.modules.workspaces.presentation.deps import (
    get_uc_approve_article,
    get_uc_create_article,
    get_uc_create_workspace,
    get_uc_delete_article,
    get_uc_delete_workspace,
    get_uc_get_workspace,
    get_uc_list_workspaces,
    get_uc_reject_article,
    get_uc_start_review_article,
    get_uc_submit_article,
    get_uc_update_article_content,
)
from app.modules.workspaces.presentation.schema import (
    ArticleResponse,
    CreateArticleRequest,
    CreateWorkspaceRequest,
    UpdateArticleContentRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# --- Workspaces ---


@router.get(
    "",
    response_model=StandardResponse[WorkspaceListResponse],
    response_model_exclude_none=True,
)
async def list_workspaces(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_list_workspaces),
):
    result = await uc.execute(caller=current_user, page=page, limit=limit)
    items = [
        WorkspaceResponse.from_model(
            ws,
            article_count=result.article_counts.get(ws.id, 0),
            products=result.products_by_ws.get(ws.id, []),
        )
        for ws in result.items
    ]
    data = WorkspaceListResponse(items=items, total=result.total)
    return create_success_response(data)


@router.post(
    "",
    response_model=StandardResponse[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    body: CreateWorkspaceRequest = Body(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_CREATE)),
    uc=Depends(get_uc_create_workspace),
):
    ws = await uc.execute(name=body.name, owner_user_id=current_user.id)
    return create_success_response(
        WorkspaceResponse.from_model(ws), "Workspace created"
    )


@router.get(
    "/{workspace_id}",
    response_model=StandardResponse[WorkspaceResponse],
)
async def get_workspace(
    workspace_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_get_workspace),
):
    result = await uc.execute(workspace_id=workspace_id, caller=current_user)
    return create_success_response(
        WorkspaceResponse.from_model(
            result.workspace,
            articles=result.articles,
            products=result.products,
        )
    )


@router.delete(
    "/{workspace_id}",
    response_model=StandardResponse,
)
async def delete_workspace(
    workspace_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_delete_workspace),
):
    await uc.execute(workspace_id=workspace_id, caller=current_user)
    return create_success_response(None, "Workspace deleted")


# --- Articles ---


@router.post(
    "/{workspace_id}/articles",
    response_model=StandardResponse[ArticleResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    workspace_id: str = Path(...),
    body: CreateArticleRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_create_article),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        name=body.name,
        product=body.product,
        caller=current_user,
    )
    return create_success_response(
        ArticleResponse.from_model(article), "Article created"
    )


@router.delete(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse,
)
async def delete_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_delete_article),
):
    await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(None, "Article deleted")


@router.patch(
    "/{workspace_id}/articles/{article_id}",
    response_model=StandardResponse[ArticleResponse],
)
async def update_article_content(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    body: UpdateArticleContentRequest = Body(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_update_article_content),
):
    article = await uc.execute(
        workspace_id=workspace_id,
        article_id=article_id,
        content=body.content,
        caller=current_user,
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/submit",
    response_model=StandardResponse[ArticleResponse],
)
async def submit_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    uc=Depends(get_uc_submit_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/start-review",
    response_model=StandardResponse[ArticleResponse],
)
async def start_review_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
    uc=Depends(get_uc_start_review_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/approve",
    response_model=StandardResponse[ArticleResponse],
)
async def approve_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
    uc=Depends(get_uc_approve_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))


@router.post(
    "/{workspace_id}/articles/{article_id}/reject",
    response_model=StandardResponse[ArticleResponse],
)
async def reject_article(
    workspace_id: str = Path(...),
    article_id: str = Path(...),
    current_user: User = Depends(require_permissions(Permission.WORKSPACES_REVIEW)),
    uc=Depends(get_uc_reject_article),
):
    article = await uc.execute(
        workspace_id=workspace_id, article_id=article_id, caller=current_user
    )
    return create_success_response(ArticleResponse.from_model(article))
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.modules.workspaces.presentation.routes import router; print(router.prefix, len(router.routes))"
```

Expected: prints `/workspaces 11` (11 routes registered).

- [ ] **Step 3: Commit**

```bash
git add app/modules/workspaces/presentation/routes.py
git commit -m "feat(workspaces): HTTP routes (11 endpoints)"
```

---

### Task 29: Wire everything into `app.py` (router, error handlers, ensure_indexes)

**Files:**
- Modify: `app/app.py`

- [ ] **Step 1: Replace `app/app.py`**

```python
# app/app.py
"""Main FastAPI application setup."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import mongo_connection
from app.core.errors import register_exception_handlers
from app.core.settings import settings
from app.middlewares import setup_middleware
from app.modules.admin.presentation.routes import router as admin_router
from app.modules.auth.presentation.routes import router as auth_router
from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.usecases.bootstrap_superuser import (
    BootstrapSuperuserUseCase,
)
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.users.presentation.routes import router as users_router
from app.modules.workspaces.data.repo import (
    ArticleDataRepository,
    WorkspaceDataRepository,
)
from app.modules.workspaces.presentation.routes import router as workspaces_router


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_connection.connect()

    # Ensure workspaces indexes
    await WorkspaceDataRepository().ensure_indexes()
    await ArticleDataRepository().ensure_indexes()

    # Bootstrap superuser
    user_repo = UserDataRepository()
    bootstrap = BootstrapSuperuserUseCase(
        user_repo=user_repo,
        uc_create_user=CreateUserUseCase(user_repo=user_repo),
    )
    await bootstrap.execute(
        email=settings.superuser_email,
        password=settings.superuser_password,
    )

    yield


app = FastAPI(
    title="GreenRAG Backend",
    description="GreenRAG Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

setup_middleware(app)
register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 2: Import-compile check**

```bash
PYTHONPATH=. python -c "from app.app import app; print(len(app.routes))"
```

Expected: a positive integer (auth + users + admin + workspaces + health + docs).

- [ ] **Step 3: Commit**

```bash
git add app/app.py
git commit -m "feat(app): mount workspaces router, register error handlers, ensure indexes"
```

---

## Phase G — Manual verification (smoke tests)

Live smoke tests against the running app. These mirror the spec's "Manual verification" section. If any step fails, fix the offending task and re-run from that step.

### Task 30: Smoke-test the live app

**Pre-requisites:**
- `.env` has `MONGO_URI`, `MONGO_DB_NAME`, `JWT_SECRET_KEY`, `SUPERUSER_EMAIL=root@example.com`, `SUPERUSER_PASSWORD=rootroot1` (or similar 8+ char value).
- Mongo is reachable.

- [ ] **Step 1: Start the app**

```bash
cd "/Volumes/Extreme SSD/ugcx/UGC/backend"
PYTHONPATH=. uvicorn app.app:app --host 0.0.0.0 --port 8080 --reload
```

Confirm in the logs: "superuser bootstrapped" or "superuser already exists" (no error), and no Mongo connection failure.

- [ ] **Step 2: Log in as superuser; create a QC user**

In a separate terminal:

```bash
# Login superuser
SU_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"root@example.com","password":"rootroot1"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")
echo "SU_TOKEN=$SU_TOKEN"

# Create QC(CL)
curl -s -X POST http://localhost:8080/api/v1/admin/users \
  -H "Authorization: Bearer $SU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"qc_cl@example.com","password":"qcqc1234","role":"qc","qc_product":"CL"}'
echo
```

Expected: JSON with `success: true` and a user with `role: "qc"`, `qc_product: "CL"`.

- [ ] **Step 3: Register a creator; login**

```bash
curl -s -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"creator@example.com","password":"crcr1234"}'
echo

CR_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"creator@example.com","password":"crcr1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")
echo "CR_TOKEN=$CR_TOKEN"
```

- [ ] **Step 4: Create a workspace (and verify dup-name → 409)**

```bash
curl -s -X POST http://localhost:8080/api/v1/workspaces \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Smoke Test"}'
echo

# duplicate name (case-insensitive)
curl -s -X POST http://localhost:8080/api/v1/workspaces \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke test"}'
echo
```

Expected: first call returns the workspace; second returns `{success: false, message: "Workspace name already in use"}` with status 409.

- [ ] **Step 5: List workspaces; confirm tab_count and products**

Capture the workspace id:

```bash
WS_ID=$(curl -s -X GET 'http://localhost:8080/api/v1/workspaces?page=1&limit=12' \
  -H "Authorization: Bearer $CR_TOKEN" \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['items'][0]['id'])")
echo "WS_ID=$WS_ID"
```

The list response items should have `article_count: 0` and either no `products` key or an empty list.

- [ ] **Step 6: Create articles in two products**

```bash
ART_CL=$(curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Draft 1","product":"CL"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['id'])")

ART_FD=$(curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Draft 2","product":"FD"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['id'])")

echo "ART_CL=$ART_CL ART_FD=$ART_FD"
```

- [ ] **Step 7: Get workspace detail as creator; PATCH content; submit CL**

```bash
curl -s -X GET "http://localhost:8080/api/v1/workspaces/$WS_ID" \
  -H "Authorization: Bearer $CR_TOKEN"
echo

curl -s -X PATCH "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"<p>hi</p>"}'
echo

curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL/submit" \
  -H "Authorization: Bearer $CR_TOKEN"
echo

# second submit → 409
curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL/submit" \
  -H "Authorization: Bearer $CR_TOKEN"
echo
```

Expected: detail returns workspace with both articles and `products: ["CL","FD"]`; PATCH returns updated article; first submit transitions to `waiting_for_review`; second submit returns 409 `{success: false, message: "Article is not in a submittable state"}`.

- [ ] **Step 8: PATCH submitted article → 409**

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"<p>nope</p>"}'
echo
```

Expected: 409.

- [ ] **Step 9: Log in as QC(CL); see scope-filtered workspace; start-review CL**

```bash
QC_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"qc_cl@example.com","password":"qcqc1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

curl -s -X GET 'http://localhost:8080/api/v1/workspaces?page=1&limit=12' \
  -H "Authorization: Bearer $QC_TOKEN"
echo

curl -s -X GET "http://localhost:8080/api/v1/workspaces/$WS_ID" \
  -H "Authorization: Bearer $QC_TOKEN"
echo

curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL/start-review" \
  -H "Authorization: Bearer $QC_TOKEN"
echo

# QC starts-review on the FD article (not in scope) → 404 even though status is wrong
curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_FD/start-review" \
  -H "Authorization: Bearer $QC_TOKEN"
echo
```

Expected: list contains the workspace with `article_count: 1`, `products: ["CL"]`; detail returns only the CL article; start-review on CL → 200, status `reviewing`; start-review on FD → 404.

- [ ] **Step 10: Approve CL as QC, PATCH as creator (allowed in reviewing)**

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"<p>edited during review</p>"}'
echo

curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL/approve" \
  -H "Authorization: Bearer $QC_TOKEN"
echo

# After approval, PATCH → 409
curl -s -X PATCH "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_CL" \
  -H "Authorization: Bearer $CR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"<p>too late</p>"}'
echo
```

Expected: PATCH during reviewing → 200; approve → 200, status `approved`; PATCH after approval → 409.

- [ ] **Step 11: Verify admin can read but not approve**

Create an admin user as superuser first:

```bash
curl -s -X POST http://localhost:8080/api/v1/admin/users \
  -H "Authorization: Bearer $SU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin1@example.com","password":"admin123","role":"admin"}'
echo

ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin1@example.com","password":"admin123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

# Admin can list everything
curl -s -X GET 'http://localhost:8080/api/v1/workspaces?page=1&limit=12' \
  -H "Authorization: Bearer $ADMIN_TOKEN"
echo

# Admin tries approve → 403
curl -s -X POST "http://localhost:8080/api/v1/workspaces/$WS_ID/articles/$ART_FD/approve" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
echo
```

Expected: list shows the workspace; approve attempt returns 403 with `{success: false, message: "Insufficient permissions"}`.

- [ ] **Step 12: Delete workspace → cascade**

```bash
curl -s -X DELETE "http://localhost:8080/api/v1/workspaces/$WS_ID" \
  -H "Authorization: Bearer $CR_TOKEN"
echo

curl -s -X GET "http://localhost:8080/api/v1/workspaces/$WS_ID" \
  -H "Authorization: Bearer $CR_TOKEN"
echo
```

Expected: delete returns `{success: true, message: "Workspace deleted"}`; get returns 404 `{success: false, message: "Workspace not found"}`.

- [ ] **Step 13: Confirm error envelope shape on every error**

Check a few error responses captured above — all should be `{success: false, message: "..."}`. **Not** the FastAPI default `{detail: "..."}`. If any errors still emit `detail`, the global handler is not registered correctly (revisit Task 29).

- [ ] **Step 14: Commit a smoke-test note (optional)**

If you want a record of the verification:

```bash
git commit --allow-empty -m "chore: workspaces module smoke-tested end-to-end"
```

---

## Self-Review

**Spec coverage:**
- Workspace + Article + Product enum + ArticleStatus enum — Tasks 1, 9.
- name_lower uniqueness — Task 14 (`uniq_owner_name_lower` index + `casefold()` in `create`).
- Indexes per spec — Task 14 (`ensure_indexes` on both repos).
- Authorization on three axes (capability/ownership/product) — Task 11 + use cases 15-25.
- WORKSPACES_REVIEW not granted to admin — Task 11.
- Check ordering for review-flow — Tasks 23, 24, 25 follow load → ws-match → product → status → apply.
- Error envelope — Task 12 + 29.
- qc_product cross-module — Tasks 2-8.
- Eleven endpoints — Task 28 (verified by `len(router.routes) == 11`).
- Tab count + products on list — list_workspaces use case + WorkspaceResponse.
- Epoch-ms timestamps — `_to_epoch_ms` helper in Task 26.
- Cascade delete — Task 18 (calls `delete_by_workspace` after workspace delete).
- WorkspaceNotFoundError used to hide existence — used in get_workspace, delete_workspace, create_article, delete_article, update_article_content, submit_article when caller is not owner.
- ArticleNotFoundError used to hide existence — used in start_review/approve/reject when product scope fails.
- Smoke tests cover all status transitions and all four roles — Task 30.

**Placeholder scan:** no TBD / TODO / "add appropriate" / "similar to Task N" / vague directions. Every step contains the actual code or command.

**Type consistency:**
- `WorkspaceRepo` / `ArticleRepo` abstract methods (Task 13) match `WorkspaceDataRepository` / `ArticleDataRepository` overrides (Task 14).
- `ListWorkspacesResult` and `GetWorkspaceResult` are referenced consistently by routes (Task 28).
- `from_model` signatures on `WorkspaceResponse` / `ArticleResponse` match all call sites in `routes.py`.
- DI providers (Task 27) return types match what routes expect (Task 28).
- `qc_product_provided` boolean parameter (Task 5) matches its caller in routes (Task 7).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-09-workspaces.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
