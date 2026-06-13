from app.core.security import hash_interim_key


def test_hash_is_deterministic_and_not_plaintext():
    raw = "abc123"
    h = hash_interim_key(raw)
    assert h == hash_interim_key(raw)
    assert h != raw
    assert len(h) == 64


def test_different_inputs_differ():
    assert hash_interim_key("a") != hash_interim_key("b")
