import pytest
from pydantic import ValidationError

from app.modules.workspaces.data.model import AnchorTargetType
from app.modules.workspaces.presentation.schema import AnchorRequest, CreateFeedbackRequest


def test_none_anchor_accepts_empty_fields():
    a = AnchorRequest(target_type=AnchorTargetType.NONE)
    assert a.target_type == AnchorTargetType.NONE
    assert a.quote == ""


def test_none_anchor_rejects_nonempty_quote():
    with pytest.raises(ValidationError):
        AnchorRequest(target_type=AnchorTargetType.NONE, quote="hello")


def test_create_feedback_with_none_anchor():
    req = CreateFeedbackRequest(
        body="Fix tone overall",
        anchor=AnchorRequest(target_type=AnchorTargetType.NONE),
    )
    assert req.anchor.target_type == AnchorTargetType.NONE
