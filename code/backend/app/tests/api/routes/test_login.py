from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.auth_rate_limit import auth_attempt_limiter
from app.core.security import get_password_hash, verify_password
from app.crud import create_user
from app.models import User, UserCreate
from app.tests.utils.user import user_authentication_headers
from app.tests.utils.utils import random_email, random_lower_string
from app.utils import generate_password_reset_token


@pytest.fixture(autouse=True)
def reset_auth_attempt_limiter():
    auth_attempt_limiter.reset()
    yield
    auth_attempt_limiter.reset()


def test_get_access_token(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_get_access_token_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 400


def test_malformed_plaintext_password_row_fails_closed(
    client: TestClient,
    db: Session,
) -> None:
    user = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()
    original_hash = user.hashed_password
    try:
        user.hashed_password = settings.FIRST_SUPERUSER_PASSWORD
        db.add(user)
        db.commit()

        assert not verify_password(
            settings.FIRST_SUPERUSER_PASSWORD,
            settings.FIRST_SUPERUSER_PASSWORD,
        )
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "AUTH_CREDENTIALS_INVALID"
    finally:
        user.hashed_password = original_hash
        db.add(user)
        db.commit()


def test_standard_password_hash_still_verifies() -> None:
    plain_password = "valid-standard-password"
    hashed_password = get_password_hash(plain_password)

    assert hashed_password != plain_password
    assert verify_password(plain_password, hashed_password)
    assert not verify_password("wrong-password", hashed_password)


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_recovery_password(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    with patch("app.api.routes.login.send_email") as send_email_mock:
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 202
        assert r.json() == {
            "message": "如果该邮箱已注册，我们会发送密码重置说明。"
        }
        assert r.headers["x-request-id"]
        send_email_mock.assert_called_once()


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 202
    assert r.json() == {
        "message": "如果该邮箱已注册，我们会发送密码重置说明。"
    }


def test_login_rate_limit_uses_stable_error_contract(client: TestClient) -> None:
    payload = {"username": "rate-limit-user@example.com", "password": "wrong-password"}
    for _ in range(settings.AUTH_RATE_LIMIT_ATTEMPTS):
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data=payload,
        )
        assert response.status_code == 400

    blocked = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=payload,
        headers={"X-Request-ID": "login-rate-test"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]
    assert blocked.headers["x-request-id"] == "login-rate-test"
    assert blocked.json()["detail"] == {
        "code": "AUTH_RATE_LIMITED",
        "message": "尝试次数过多，请稍后再试。",
        "request_id": "login-rate-test",
    }


def test_password_recovery_rate_limit_does_not_reveal_account(client: TestClient) -> None:
    endpoint = f"{settings.API_V1_STR}/password-recovery/missing-rate-user@example.com"
    for _ in range(settings.AUTH_RATE_LIMIT_ATTEMPTS):
        response = client.post(endpoint)
        assert response.status_code == 202

    blocked = client.post(endpoint)
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "AUTH_RATE_LIMITED"


def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
        is_superuser=False,
    )
    user = create_user(session=db, user_create=user_create)
    token = generate_password_reset_token(email=email)
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    db.refresh(user)
    assert verify_password(new_password, user.hashed_password)


def test_reset_password_invalid_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == 400
    assert response["detail"] == "Invalid token"
