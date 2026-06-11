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
        qc_products: Optional[list[Product]] = None,
        qc_products_provided: bool = False,
    ) -> Optional[User]:
        """Update a managed user.

        `qc_products_provided=True` means the caller explicitly sent the field
        (even if its value is None); only then do we touch it. This avoids
        accidentally clearing qc_products when callers omit the field.
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                return None

            if is_active is not None:
                user.is_active = is_active
            if password is not None:
                user.password_hashed = hash_password(password)
            if qc_products_provided:
                if user.role != UserRole.QC:
                    raise ValueError("qc_products can only be set on QC users")
                if not qc_products:
                    raise ValueError("qc_products cannot be cleared on a QC user")
                user.qc_products = qc_products

            updated = await self.user_repo.update(user)
            self.log_info(
                f"User updated: id={updated.id} role={updated.role.value} "
                f"qc_products={[p.value for p in updated.qc_products]}"
            )
            return updated
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"UpdateManagedUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to update user: {str(e)}") from e
