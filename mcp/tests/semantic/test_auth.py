import time

import jwt as pyjwt

from app.tools.semantic.auth import sign_cube_token


def test_sign_cube_token_is_verifiable_with_the_secret():
    token = sign_cube_token("dev-secret")

    decoded = pyjwt.decode(token, "dev-secret", algorithms=["HS256"])

    assert isinstance(token, str)
    assert decoded  # non-empty payload


def test_sign_cube_token_sets_expiry_in_the_future():
    token = sign_cube_token("dev-secret", expires_in_seconds=120)

    decoded = pyjwt.decode(token, "dev-secret", algorithms=["HS256"])

    assert decoded["exp"] > time.time()


def test_sign_cube_token_wrong_secret_fails_verification():
    token = sign_cube_token("dev-secret")

    try:
        pyjwt.decode(token, "wrong-secret", algorithms=["HS256"])
        assert False, "expected verification to fail"
    except pyjwt.InvalidSignatureError:
        pass