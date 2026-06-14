from datetime import datetime, timezone

from app.modules.users.data.model import UserRole
from app.modules.users.presentation.schema import UserMeResponse


def test_user_me_response_has_profile_complete_field():
    r = UserMeResponse(
        id="u_1",
        email="a@x.com",
        is_active=True,
        role=UserRole.CREATOR,
        qc_products=[],
        permissions=[],
        profile_complete=False,
        created_at=datetime.now(timezone.utc),
    )
    assert r.profile_complete is False
