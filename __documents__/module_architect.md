# Module Architecture Guide

This document describes the standard architecture pattern for implementing modules in the integration-service application. The architecture follows **Clean Architecture** principles with clear separation of concerns across three layers: **Data**, **Domain**, and **Presentation**.

## Module Structure

Each module should follow this directory structure:

```
app/modules/{module_name}/
├── data/
│   ├── models.py          # MongoDB models (Pydantic models)
│   ├── mapper.py          # Data transformation functions
│   └── repo.py            # Repository implementation (MongoDB)
├── domain/
│   ├── repo.py            # Repository interface (ABC)
│   └── usecases/
│       ├── usecase1.py    # Individual use case implementations
│       └── usecase2.py
└── presentation/
    ├── schema.py          # Pydantic schemas for API requests/responses
    ├── deps.py            # FastAPI dependency injection functions
    └── routes.py          # FastAPI route handlers
```

## Layer Responsibilities

### 1. Data Layer (`data/`)

The data layer handles all database interactions and data persistence.

#### `data/models.py`

- Defines MongoDB document models using Pydantic
- Extends `BaseMongoModel` from `app.core.model`
- Contains the `Config` class with `collection_name` for MongoDB collection
- Represents the actual database schema

**Example:**

```python
from app.core.model import BaseMongoModel
from pydantic import Field

class ApiKey(BaseMongoModel):
    tenant_id: str
    name: str
    env: str
    prefix: str = Field(..., description="Public prefix for lookup")

    class Config:
        collection_name = "api_keys"
```

#### `data/mapper.py`

- Contains functions to transform domain models to presentation schemas
- Handles data formatting, masking, and transformation logic
- Maps from `data/models.py` to `presentation/schema.py`
- Functions are named with `to_` prefix followed by the target schema name in snake_case

**Example:**

```python
from app.modules.api_key.data.models import ApiKey
from app.modules.api_key.presentation.schema import ApiKeySchema
from app.utils.utils import mask_key

def to_api_key_schema(api_key: ApiKey) -> ApiKeySchema:
    return ApiKeySchema(
        id=str(api_key.id),
        tenant_id=api_key.tenant_id,
        name=api_key.name,
        env=api_key.env,
        prefix=api_key.prefix,
        masked_key=mask_key(api_key.prefix),
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        expires_at=api_key.expires_at,
    )
```

#### `data/repo.py`

- Implements the repository interface defined in `domain/repo.py`
- Contains all MongoDB operations (CRUD)
- Implements `ensure_indexes()` method for database indexes
- Uses `LoggerMixin` for logging
- Handles database-specific concerns (MongoDB, async operations)

**Key patterns:**

- Extends `LoggerMixin` and the domain repository interface
- Uses `@override` decorator for interface methods
- Implements `_get_collection()` helper for MongoDB access
- Handles `DuplicateKeyError` and other database exceptions

**Example:**

```python
from typing import Optional, List, override
from datetime import datetime
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError
from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.api_key.data.models import ApiKey, ApiKeyEnv
from app.modules.api_key.domain.repo import ApiKeyRepo
from app.utils.utils import ensure_id_uuid, utcnow

class ApiKeyDataRepository(LoggerMixin, ApiKeyRepo):
    def __init__(self):
        self.collection_name = ApiKey.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        """Get MongoDB collection."""
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        """
        Call once on startup.
        Enforces:
          - prefix unique (fast lookup)
          - one ACTIVE key per (tenant_id, env) where revoked_at == None
        """
        collection = await self._get_collection()
        await collection.create_index("prefix", unique=True)
        await collection.create_index(
            [("tenant_id", 1), ("env", 1)],
            unique=True,
            partialFilterExpression={"revoked_at": None},
        )

    @override
    async def get_by_prefix(self, prefix: str) -> Optional[ApiKey]:
        collection = await self._get_collection()
        doc = await collection.find_one({"prefix": prefix})
        return ApiKey.model_validate(doc) if doc else None

    @override
    async def create(self, api_key: ApiKey) -> ApiKey:
        try:
            collection = await self._get_collection()
            payload = api_key.model_dump(by_alias=True)
            await collection.insert_one(ensure_id_uuid(payload))
            return api_key
        except DuplicateKeyError as e:
            raise e
```

**Naming Notes:**

- Repository implementation: `{Module}DataRepository` (e.g., `ApiKeyDataRepository`)
- Private helper methods: prefixed with `_` (e.g., `_get_collection()`)
- Always use `@override` decorator for interface method implementations
- Use `model_validate()` for converting MongoDB documents to Pydantic models
- Use `model_dump(by_alias=True)` when inserting documents

### 2. Domain Layer (`domain/`)

The domain layer contains business logic and defines contracts (interfaces) that the data layer must implement.

#### `domain/repo.py`

- Defines the repository interface using Python's `ABC` (Abstract Base Class)
- Declares all required methods as `@abstractmethod`
- Acts as a contract between domain logic and data persistence
- Domain models (from `data/models.py`) are used in the interface

**Example:**

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from app.modules.api_key.data.models import ApiKey, ApiKeyEnv

class ApiKeyRepo(ABC):
    @abstractmethod
    async def get_by_prefix(self, prefix: str) -> Optional[ApiKey]:
        pass

    @abstractmethod
    async def get_active_by_account(
        self, tenant_id: str, env: ApiKeyEnv
    ) -> Optional[ApiKey]:
        pass

    @abstractmethod
    async def list_by_account(
        self, tenant_id: str, env: Optional[ApiKeyEnv] = None
    ) -> List[ApiKey]:
        pass

    @abstractmethod
    async def create(self, api_key: ApiKey) -> ApiKey:
        pass

    @abstractmethod
    async def update_last_used(self, api_key_id: str, last_used_at: datetime) -> None:
        pass

    @abstractmethod
    async def revoke_active_key(
        self, tenant_id: str, env: ApiKeyEnv, revoked_at: datetime
    ) -> Optional[ApiKey]:
        pass

    @abstractmethod
    async def revoke_by_id(
        self, tenant_id: str, env: ApiKeyEnv, api_key_id: str, revoked_at: datetime
    ) -> None:
        pass

    @abstractmethod
    async def touch_updated_at(self, api_key_id: str) -> None:
        pass
```

**Naming Notes:**

- Repository interface: `{Module}Repo` (e.g., `ApiKeyRepo`)
- Methods: snake_case, descriptive action verbs (e.g., `get_by_prefix()`, `list_by_account()`, `revoke_active_key()`)

#### `domain/usecases/`

- Contains individual use case classes
- Each use case is a dataclass with `@dataclass(frozen=True)`
- Extends `LoggerMixin` for logging
- Contains an `execute()` method that implements the business logic
- Use cases can depend on other use cases or the repository
- Should handle exceptions and provide meaningful error messages

**Example:**

```python
from dataclasses import dataclass
from app.core.logging_mixin import LoggerMixin
from app.modules.api_key.domain.repo import ApiKeyRepo
from app.modules.api_key.domain.usecases.create_key_internal import (
    CreateKeyInternalUseCase,
)

@dataclass(frozen=True)
class CreateApiKeyForAccountUseCase(LoggerMixin):
    api_key_repo: ApiKeyRepo
    uc_create_key_internal: CreateKeyInternalUseCase

    async def execute(
        self,
        tenant_id: str,
        name: str,
        env: ApiKeyEnv,
    ) -> CreateApiKeyResponse:
        try:
            # Business logic here
            result = await self.uc_create_key_internal.execute(...)
            return result
        except Exception as e:
            self.log_exception(e)
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create api key: {str(e)}")
```

**Naming Notes:**

- Use case class names: PascalCase ending with `UseCase`
- Repository dependencies: `{module}_repo` (e.g., `api_key_repo`)
- Other use case dependencies: `uc_{descriptive_name}` (e.g., `uc_create_key_internal`)
- Always include `traceback.format_exc()` in exception handling for detailed logging

**Use Case Guidelines:**

- Keep use cases focused on a single responsibility
- Use dependency injection for repositories and other use cases
- Handle exceptions gracefully and log them
- Always log both the exception and `traceback.format_exc()` for detailed error information
- Return domain models or presentation schemas (via mappers)
- Use `*` for keyword-only arguments in `execute()` method when appropriate (e.g., `async def execute(self, *, tenant_id: str, ...)`)
- Use descriptive names: repository dependencies use `{module}_repo`, other use case dependencies use `uc_{descriptive_name}`

### 3. Presentation Layer (`presentation/`)

The presentation layer handles HTTP requests, responses, and API contracts.

#### `presentation/schema.py`

- Defines Pydantic models for API requests and responses
- Request schemas: Input validation for API endpoints (suffix: `Request`)
- Response schemas: Output format for API responses (suffix: `Response`)
- Entity schemas: Representation of domain entities (suffix: `Schema`)
- Should not contain business logic
- Use type literals from `data/models.py` when applicable (e.g., `ApiKeyEnv`)

**Example:**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.modules.api_key.data.models import ApiKeyEnv

class ApiKeySchema(BaseModel):
    id: str = Field(..., description="API key ID")
    tenant_id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Name of the API key")
    env: ApiKeyEnv = Field(..., description="Environment: live or test")
    prefix: str = Field(..., description="Prefix of the API key")
    masked_key: str = Field(..., description="Masked key")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")
    last_used_at: Optional[datetime] = Field(None, description="Last used at")
    revoked_at: Optional[datetime] = Field(None, description="Revoked at")
    expires_at: Optional[datetime] = Field(None, description="Expires at")

class CreateApiKeyRequest(BaseModel):
    tenant_id: str = Field(..., description="Account ID to create API key for")
    name: str = Field(default="default", description="Name for the API key")
    env: ApiKeyEnv = Field(default="live", description="Environment: live or test")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")
    rotate_if_exists: bool = Field(
        default=True, description="Rotate existing key if present"
    )

class CreateApiKeyResponse(BaseModel):
    api_key: str = Field(..., description="API key")
    api_key_info: ApiKeySchema = Field(..., description="API key information")
```

#### `presentation/deps.py`

- Contains FastAPI dependency injection functions
- Creates and wires up use cases and repositories
- Uses FastAPI's `Depends()` for dependency injection
- Each dependency function returns an instance of a use case or repository

**Example:**

```python
from fastapi import Depends
from app.modules.api_key.domain.repo import ApiKeyRepo
from app.modules.api_key.data.repo import ApiKeyDataRepository
from app.modules.api_key.domain.usecases.create_api_key_for_account import (
    CreateApiKeyForAccountUseCase,
)
from app.modules.api_key.domain.usecases.create_key_internal import (
    CreateKeyInternalUseCase,
)

def get_api_key_repo() -> ApiKeyRepo:
    return ApiKeyDataRepository()

def get_uc_create_key_internal(
    api_key_repo: ApiKeyRepo = Depends(get_api_key_repo),
) -> CreateKeyInternalUseCase:
    return CreateKeyInternalUseCase(api_key_repo=api_key_repo)

def get_uc_create_api_key_for_account(
    api_key_repo: ApiKeyRepo = Depends(get_api_key_repo),
    uc_create_key_internal: CreateKeyInternalUseCase = Depends(
        get_uc_create_key_internal
    ),
) -> CreateApiKeyForAccountUseCase:
    return CreateApiKeyForAccountUseCase(
        api_key_repo=api_key_repo,
        uc_create_key_internal=uc_create_key_internal,
    )
```

**Naming Notes:**

- Repository dependency functions: `get_{module}_repo()` (e.g., `get_api_key_repo()`)
- Use case dependency functions: `get_uc_{descriptive_name}()` (e.g., `get_uc_create_api_key_for_account()`)
- Function parameters match the field names in use case classes

#### `presentation/routes.py`

- Defines FastAPI route handlers
- Creates an `APIRouter` with appropriate prefix and tags
- Router prefix: `/{module-name}` format (e.g., `/api-key`, `/connection`)
- Router tags: `["module_name"]` format (e.g., `["api_key"]`, `["connection"]`)
- Each route handler:
  - Accepts request schemas as parameters
  - Uses dependency injection to get use cases
  - Calls use case `execute()` methods
  - Returns `StandardResponse` using `create_success_response()`
  - Handles exceptions and converts them to HTTP exceptions
  - Includes docstrings describing the endpoint functionality

**Example:**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.model import StandardResponse, create_success_response
from app.modules.api_key.presentation.schema import CreateApiKeyRequest
from app.modules.api_key.presentation.deps import (
    get_uc_create_api_key_for_account,
)
from app.modules.api_key.domain.usecases.create_api_key_for_account import (
    CreateApiKeyForAccountUseCase,
)

router = APIRouter(prefix="/api-key", tags=["api_key"])

@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    api_key_data: CreateApiKeyRequest,
    uc_create_api_key_for_account: CreateApiKeyForAccountUseCase = Depends(
        get_uc_create_api_key_for_account
    ),
):
    """
    Create a new API key for an account.
    """
    try:
        result = await uc_create_api_key_for_account.execute(
            tenant_id=api_key_data.tenant_id,
            name=api_key_data.name,
            env=api_key_data.env,
            expires_at=api_key_data.expires_at,
            rotate_if_exists=api_key_data.rotate_if_exists,
        )
        return create_success_response(result, "API key created successfully")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
```

**Naming Notes:**

- Route handler functions: snake_case (e.g., `create_api_key()`, `list_api_keys()`)
- Route handler parameters for use cases: `uc_{descriptive_name}` (e.g., `uc_create_api_key_for_account`)
- Request schema parameters: `{module}_data` or descriptive name (e.g., `api_key_data`, `rotate_data`)

## Module Registration

To register a module in the application:

1. Import the router in `app/app.py`:

```python
from app.modules.{module_name}.presentation.routes import router as {module_name}_router
```

2. Include the router in the FastAPI app:

```python
app.include_router({module_name}_router, prefix="/api/v1")
```

## Naming Conventions

### Classes and Types

- **Models**: PascalCase (e.g., `ApiKey`, `ApiKeyEnv`)
- **Repository Interfaces**: PascalCase ending with `Repo` (e.g., `ApiKeyRepo`)
- **Repository Implementations**: PascalCase ending with `DataRepository` (e.g., `ApiKeyDataRepository`)
- **Use Cases**: PascalCase ending with `UseCase` (e.g., `CreateApiKeyForAccountUseCase`, `ListApiKeysUseCase`)
- **Schemas**: PascalCase with descriptive suffix (e.g., `ApiKeySchema`, `CreateApiKeyRequest`, `CreateApiKeyResponse`)

### Functions

- **Mapper functions**: snake*case, prefixed with `to*`(e.g.,`to_api_key_schema()`)
- **Dependency functions**: snake*case, prefixed with `get*`for repositories,`get*uc*`for use cases (e.g.,`get_api_key_repo()`, `get_uc_create_api_key_for_account()`)
- **Route handlers**: snake_case (e.g., `create_api_key()`, `list_api_keys()`)
- **Use case methods**: `execute()` (standard method name for all use cases)

### Files

- **Use case files**: snake_case (e.g., `create_api_key_for_account.py`, `rotate_api_key.py`, `list.py`)
- **Other files**: snake_case (e.g., `models.py`, `repo.py`, `schema.py`, `routes.py`, `deps.py`, `mapper.py`)

### Variables and Fields

- **Use case dependencies**: snake*case, prefixed with `uc*`for other use cases, no prefix for repositories (e.g.,`uc_create_key_internal: CreateKeyInternalUseCase`, `api_key_repo: ApiKeyRepo`)
- **Repository field in use cases**: snake_case ending with `_repo` (e.g., `api_key_repo`)
- **General variables**: snake_case

### Constants and Literals

- **Type literals**: PascalCase (e.g., `ApiKeyEnv = Literal["live", "test"]`)

## Key Principles

1. **Separation of Concerns**: Each layer has a distinct responsibility
   - Data: Database operations
   - Domain: Business logic
   - Presentation: HTTP/API concerns

2. **Dependency Inversion**: Domain layer defines interfaces, data layer implements them

3. **Dependency Injection**: Use FastAPI's `Depends()` for all dependencies

4. **Error Handling**:
   - Use cases should catch exceptions and log them
   - Routes should convert exceptions to appropriate HTTP status codes

5. **Logging**: All use cases and repositories should extend `LoggerMixin`

6. **Type Safety**: Use type hints throughout for better IDE support and error detection

7. **Immutability**: Use cases are frozen dataclasses (`@dataclass(frozen=True)`)

8. **Naming Consistency**: Follow the naming conventions above for consistency across modules

## Common Patterns

### Database Indexes

Always implement `ensure_indexes()` in the data repository and call it during application startup:

```python
async def ensure_indexes(self) -> None:
    collection = await self._get_collection()
    await collection.create_index("field_name", unique=True)
    await collection.create_index([("field1", 1), ("field2", 1)])
```

### Model Validation

Use Pydantic's validation features in models and schemas:

```python
from pydantic import Field, field_validator

class MyModel(BaseMongoModel):
    email: str = Field(..., description="Email address")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v
```

### Use Case Composition

Use cases can depend on other use cases:

```python
@dataclass(frozen=True)
class ComplexUseCase(LoggerMixin):
    api_key_repo: ApiKeyRepo
    uc_simple: SimpleUseCase  # Depends on another use case

    async def execute(self, ...):
        # Use uc_simple.execute() here
        pass
```

**Naming Notes:**

- Repository dependencies: `{module}_repo` (e.g., `api_key_repo`)
- Other use case dependencies: `uc_{descriptive_name}` (e.g., `uc_simple`, `uc_create_key_internal`)

## Example Module Flow

1. **Request arrives** → `presentation/routes.py` route handler
2. **Route handler** → Validates input using `presentation/schema.py` request schema
3. **Route handler** → Gets use case via dependency injection from `presentation/deps.py`
4. **Use case** → Executes business logic in `domain/usecases/*.py`
5. **Use case** → Calls repository methods from `domain/repo.py` interface
6. **Repository** → Implements database operations in `data/repo.py`
7. **Repository** → Returns domain models from `data/models.py`
8. **Use case** → Transforms models using `data/mapper.py` to presentation schemas
9. **Route handler** → Returns `StandardResponse` with data from `presentation/schema.py`

## Best Practices

1. **Keep use cases small and focused** - One use case per business operation
2. **Use mappers for transformations** - Don't put transformation logic in use cases
3. **Handle all exceptions** - Never let exceptions bubble up unhandled
4. **Log important operations** - Use `LoggerMixin` methods for logging
5. **Validate at boundaries** - Use Pydantic schemas for input validation
6. **Use type hints** - Helps with IDE support and catches errors early
7. **Document complex logic** - Add docstrings to use cases and complex methods
8. **Test each layer independently** - Unit tests for use cases, integration tests for routes

## Reference Implementation

See `app/modules/api_key/` for a complete reference implementation following this architecture pattern.
