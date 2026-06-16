from typing import Optional

import pytest

from app.modules.auth.domain.usecases.register import (
    RegisterUseCase,
    RoleNotAllowedError,
)
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.workspaces.data.model import Product


class FakeUserRepo(UserRepo):
    def __init__(self) -> None:
        self.created: list[User] = []

    async def create(self, user: User) -> User:
        self.created.append(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        return None

    async def update(self, user: User) -> User:
        return user

    async def exists_with_role(self, role: UserRole) -> bool:
        return False

    async def list_by_role(self, role, *, skip=0, limit=50):
        return []

    async def count_by_role(self, role) -> int:
        return 0


def _make_uc() -> tuple[RegisterUseCase, FakeUserRepo]:
    repo = FakeUserRepo()
    return RegisterUseCase(uc_create_user=CreateUserUseCase(user_repo=repo)), repo


@pytest.mark.asyncio
async def test_creator_registration_works_when_demo_off(monkeypatch):
    monkeypatch.setattr(
        "app.modules.auth.domain.usecases.register.settings.demo_mode", False
    )
    uc, repo = _make_uc()
    await uc.execute(email="c@example.com", password="password123", role=UserRole.CREATOR)
    assert repo.created[0].role == UserRole.CREATOR
    assert repo.created[0].qc_products == []


@pytest.mark.asyncio
async def test_qc_registration_assigns_all_products(monkeypatch):
    monkeypatch.setattr(
        "app.modules.auth.domain.usecases.register.settings.demo_mode", True
    )
    uc, repo = _make_uc()
    await uc.execute(email="qc@example.com", password="password123", role=UserRole.QC)
    assert repo.created[0].role == UserRole.QC
    assert set(repo.created[0].qc_products) == set(Product)


@pytest.mark.asyncio
async def test_admin_allowed_when_demo_on(monkeypatch):
    monkeypatch.setattr(
        "app.modules.auth.domain.usecases.register.settings.demo_mode", True
    )
    uc, repo = _make_uc()
    await uc.execute(email="a@example.com", password="password123", role=UserRole.ADMIN)
    assert repo.created[0].role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_admin_rejected_when_demo_off(monkeypatch):
    monkeypatch.setattr(
        "app.modules.auth.domain.usecases.register.settings.demo_mode", False
    )
    uc, _ = _make_uc()
    with pytest.raises(RoleNotAllowedError):
        await uc.execute(email="a@example.com", password="password123", role=UserRole.ADMIN)


@pytest.mark.asyncio
async def test_superuser_always_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.modules.auth.domain.usecases.register.settings.demo_mode", True
    )
    uc, _ = _make_uc()
    with pytest.raises(RoleNotAllowedError):
        await uc.execute(
            email="s@example.com", password="password123", role=UserRole.SUPERUSER
        )
