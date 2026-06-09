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
