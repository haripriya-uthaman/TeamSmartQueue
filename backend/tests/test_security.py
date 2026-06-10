from app.core.security import get_password_hash, verify_password


def test_password_hash_and_verify_round_trip():
    hashed = get_password_hash("SmokeTest123")

    assert hashed != "SmokeTest123"
    assert verify_password("SmokeTest123", hashed)
    assert not verify_password("wrong-password", hashed)
