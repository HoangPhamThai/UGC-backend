from enum import Enum

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import get_current_principal
from app.modules.users.data.model import User, UserRole


class Permission(str, Enum):
    # --- User management ---
    USERS_CREATE_ADMIN = "users:create:admin"
    USERS_CREATE_QC = "users:create:qc"
    USERS_READ_ADMIN = "users:read:admin"
    USERS_READ_QC = "users:read:qc"
    USERS_READ_CREATOR = "users:read:creator"
    USERS_UPDATE_ADMIN = "users:update:admin"
    USERS_UPDATE_QC = "users:update:qc"
    USERS_UPDATE_CREATOR = "users:update:creator"
    # --- Workspaces (owned by creators) ---
    WORKSPACES_CREATE = "workspaces:create"
    WORKSPACES_DELETE = "workspaces:delete"
    WORKSPACES_READ_ANY = "workspaces:read:any"
    WORKSPACES_READ_BY_PRODUCT = "workspaces:read:by_product"
    # --- Articles ---
    ARTICLES_CREATE = "articles:create"
    ARTICLES_UPDATE = "articles:update"
    ARTICLES_DELETE = "articles:delete"
    ARTICLES_SUBMIT = "articles:submit"
    ARTICLES_REVIEW = "articles:review"
    # --- Statistics (read-only aggregates) ---
    STATS_READ = "stats:read"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.SUPERUSER: frozenset(Permission),
    UserRole.ADMIN: frozenset(
        {
            Permission.USERS_CREATE_QC,
            Permission.USERS_READ_QC,
            Permission.USERS_READ_CREATOR,
            Permission.USERS_UPDATE_QC,
            Permission.WORKSPACES_READ_ANY,
            Permission.STATS_READ,
        }
    ),
    UserRole.QC: frozenset(
        {
            Permission.USERS_READ_CREATOR,
            Permission.WORKSPACES_READ_BY_PRODUCT,
            Permission.ARTICLES_REVIEW,
        }
    ),
    UserRole.CREATOR: frozenset(
        {
            Permission.WORKSPACES_CREATE,
            Permission.WORKSPACES_DELETE,
            Permission.ARTICLES_CREATE,
            Permission.ARTICLES_UPDATE,
            Permission.ARTICLES_DELETE,
            Permission.ARTICLES_SUBMIT,
        }
    ),
}


# Permissions an interim key (agent acting for an admin) may exercise. Read/stat
# only — never mutations. The chat/memory endpoints don't go through
# require_permissions, so they are reachable independently of this set.
INTERIM_ALLOWED_PERMISSIONS: frozenset[Permission] = frozenset({Permission.STATS_READ})


def interim_key_allows(needed) -> bool:
    """True iff every required permission is interim-allowed."""
    return all(p in INTERIM_ALLOWED_PERMISSIONS for p in needed)


_CREATE_PERMISSION_BY_ROLE: dict[UserRole, Permission] = {
    UserRole.ADMIN: Permission.USERS_CREATE_ADMIN,
    UserRole.QC: Permission.USERS_CREATE_QC,
}

_READ_PERMISSION_BY_ROLE: dict[UserRole, Permission] = {
    UserRole.ADMIN: Permission.USERS_READ_ADMIN,
    UserRole.QC: Permission.USERS_READ_QC,
    UserRole.CREATOR: Permission.USERS_READ_CREATOR,
}

_UPDATE_PERMISSION_BY_ROLE: dict[UserRole, Permission] = {
    UserRole.ADMIN: Permission.USERS_UPDATE_ADMIN,
    UserRole.QC: Permission.USERS_UPDATE_QC,
    UserRole.CREATOR: Permission.USERS_UPDATE_CREATOR,
}


def permission_to_create(role: UserRole) -> Permission | None:
    return _CREATE_PERMISSION_BY_ROLE.get(role)


def permission_to_read(role: UserRole) -> Permission | None:
    return _READ_PERMISSION_BY_ROLE.get(role)


def permission_to_update(role: UserRole) -> Permission | None:
    return _UPDATE_PERMISSION_BY_ROLE.get(role)


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[user.role]


def require_permissions(*needed: Permission):
    def dep(
        request: Request,
        user: User = Depends(get_current_principal),
    ) -> User:
        granted = ROLE_PERMISSIONS[user.role]
        if not all(p in granted for p in needed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if getattr(request.state, "is_interim", False) and not interim_key_allows(needed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dep
