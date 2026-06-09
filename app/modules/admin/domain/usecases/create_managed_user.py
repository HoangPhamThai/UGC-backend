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
