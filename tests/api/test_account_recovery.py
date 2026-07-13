from collections.abc import Generator
from dataclasses import replace
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import secopsai_api.account_recovery as recovery_module
import secopsai_api.main as main_module
from secopsai_api.database import get_db
from secopsai_api.main import app
from secopsai_api.models import AccountAccessToken, AuditLog, Base, User, utcnow
from secopsai_api.security import hash_password


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_client(db: Session) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def recovery_settings():
    return replace(
        main_module.settings,
        dashboard_reset_url="https://edge.example.test/settings",
        smtp_host="smtp.example.test",
        token_secret="account-recovery-test-secret-that-is-not-global",
        password_reset_cooldown_seconds=60,
        password_reset_ttl_seconds=1800,
        password_reset_max_delivery_attempts=2,
    )


def test_password_reset_is_non_enumerating_durable_and_revokes_sessions(monkeypatch) -> None:
    db = make_session()
    user = User(email="admin@example.com", password_hash=hash_password("old-secret-password"), role="admin")
    db.add(user)
    db.commit()
    monkeypatch.setattr(main_module, "settings", recovery_settings())
    delivered_messages = []
    monkeypatch.setattr(recovery_module, "send_email_message", lambda message, settings: delivered_messages.append(message))
    client = make_client(db)

    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "old-secret-password"},
        )
        old_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        known = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "ADMIN@example.com"},
        )
        unknown = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "missing@example.com"},
        )
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json() == {"status": "accepted"}

        row = db.scalar(select(AccountAccessToken))
        assert row is not None
        assert row.delivery_status == "queued"
        assert row.token_hash and "secopsai_access" not in row.token_hash
        assert db.query(AccountAccessToken).count() == 1

        duplicate = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "admin@example.com"},
        )
        assert duplicate.status_code == 202
        assert db.query(AccountAccessToken).count() == 1

        delivery = client.post(
            "/api/v1/account-access/run-due",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert delivery.status_code == 200
        assert delivery.json() == {"processed": 1, "delivered": 1, "retrying": 0, "failed": 0}
        assert len(delivered_messages) == 1
        history = client.get(
            "/api/v1/account-access/deliveries",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert history.status_code == 200
        assert history.json()[0]["email"] == user.email
        assert history.json()[0]["status"] == "delivered"
        assert "token" not in history.text.lower()
        retried = client.post(
            f"/api/v1/account-access/deliveries/{row.id}/retry",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert retried.status_code == 200
        assert retried.json()["status"] == "delivered"
        assert retried.json()["attempts"] == 1
        assert len(delivered_messages) == 2
        reset_link = next(line for line in delivered_messages[0].get_content().splitlines() if "#reset_token=" in line)
        raw_token = reset_link.split("#reset_token=", 1)[1]
        assert raw_token.startswith("secopsai_access.")

        confirmed = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "new-secret-password"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json() == {"status": "password_reset"}
        assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 403
        assert client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "new-secret-password"},
        ).status_code == 200
        assert client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "another-secret-password"},
        ).status_code == 400

        actions = {item.action for item in db.query(AuditLog).all()}
        assert "auth.password_reset_requested" in actions
        assert "auth.password_reset_throttled" in actions
        assert "auth.password_reset_completed" in actions
        assert "account_access_delivery.run_due" in actions
    finally:
        app.dependency_overrides.clear()


def test_password_reset_delivery_retries_then_fails(monkeypatch) -> None:
    db = make_session()
    user = User(email="admin@example.com", password_hash=hash_password("old-secret-password"), role="admin")
    db.add(user)
    db.commit()
    settings = recovery_settings()
    monkeypatch.setattr(main_module, "settings", settings)

    def fail_delivery(message, current_settings):
        raise RuntimeError("SMTP unavailable")

    monkeypatch.setattr(recovery_module, "send_email_message", fail_delivery)
    client = make_client(db)
    try:
        assert client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": user.email},
        ).status_code == 202
        first = client.post(
            "/api/v1/account-access/run-due",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert first.json() == {"processed": 1, "delivered": 0, "retrying": 1, "failed": 0}
        row = db.scalar(select(AccountAccessToken))
        assert row is not None
        assert row.delivery_detail == "SMTP unavailable"
        row.next_attempt_at = utcnow() - timedelta(seconds=1)
        db.commit()
        second = client.post(
            "/api/v1/account-access/run-due",
            headers={"Authorization": "Bearer dev-admin-token"},
        )
        assert second.json() == {"processed": 1, "delivered": 0, "retrying": 0, "failed": 1}
        db.refresh(row)
        assert row.delivery_status == "failed"
        assert row.delivery_attempts == 2
    finally:
        app.dependency_overrides.clear()


def test_expired_reset_token_is_rejected(monkeypatch) -> None:
    db = make_session()
    user = User(email="admin@example.com", password_hash=hash_password("old-secret-password"), role="admin")
    db.add(user)
    db.commit()
    settings = recovery_settings()
    row = recovery_module.queue_password_reset(db, user, settings)
    assert row is not None
    token = recovery_module.materialize_access_token(row, settings)
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    monkeypatch.setattr(main_module, "settings", settings)
    client = make_client(db)
    try:
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": "new-secret-password"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Password reset link is invalid or expired"
    finally:
        app.dependency_overrides.clear()
