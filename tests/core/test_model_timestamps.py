from datetime import datetime, timezone

from app.core.model import BaseMongoModel


def test_model_validate_preserves_updated_at():
    stored = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    m = BaseMongoModel.model_validate(
        {"_id": "x", "created_at": stored, "updated_at": stored}
    )
    # The stored updated_at must survive a read (NOT be bumped to ~now).
    assert m.updated_at == stored
    assert m.created_at == stored


def test_construction_sets_timestamps():
    m = BaseMongoModel(id="y")
    assert m.created_at is not None
    assert m.updated_at is not None
