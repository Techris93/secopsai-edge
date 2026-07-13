from collections.abc import Generator
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
import secopsai_api.main as main_module
from secopsai_api.main import app, bootstrap_dashboard_admin
from secopsai_api.models import AuditLog, Base, User, utcnow
from secopsai_api.security import create_dashboard_session, hash_password, verify_password


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def make_client(db: Session) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_password_hash_round_trip_and_rejects_wrong_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_dashboard_user_login_and_me_endpoint() -> None:
    db = make_session()
    user = User(email="admin@example.com", password_hash=hash_password("secret-password"), role="admin")
    db.add(user)
    db.commit()
    client = make_client(db)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "ADMIN@example.com", "password": "secret-password"},
        )
        assert login_response.status_code == 200
        payload = login_response.json()
        assert payload["user"]["email"] == "admin@example.com"
        assert payload["access_token"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["user"]["email"] == "admin@example.com"
    finally:
        app.dependency_overrides.clear()


def test_dashboard_user_login_rejects_invalid_password() -> None:
    db = make_session()
    db.add(User(email="admin@example.com", password_hash=hash_password("secret-password"), role="admin"))
    db.commit()
    client = make_client(db)

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_token_session_still_works_for_automation_compatibility() -> None:
    db = make_session()
    client = make_client(db)

    try:
        response = client.post("/api/v1/auth/session", json={"admin_token": "dev-admin-token"})
        assert response.status_code == 200
        token = response.json()["access_token"]

        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["subject"] == "admin-token"
    finally:
        app.dependency_overrides.clear()


def test_bootstrap_dashboard_admin_creates_user(monkeypatch) -> None:
    db = make_session()
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(
            main_module.settings,
            dashboard_admin_email="pilot@example.com",
            dashboard_admin_password="pilot-password",
        ),
    )

    bootstrap_dashboard_admin(db)

    user = db.query(User).filter(User.email == "pilot@example.com").one()
    assert user.role == "admin"
    assert verify_password("pilot-password", user.password_hash)


def test_dashboard_login_locks_after_repeated_failures_and_recovers(monkeypatch) -> None:
    db = make_session()
    user = User(email="admin@example.com", password_hash=hash_password("secret-password"), role="admin")
    db.add(user)
    db.commit()
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, login_max_attempts=3, login_lockout_seconds=120),
    )
    client = make_client(db)

    try:
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.com", "password": "wrong-password"},
            ).status_code
            for _ in range(3)
        ]
        assert statuses == [403, 403, 429]

        db.refresh(user)
        assert user.failed_login_count == 3
        assert user.locked_until is not None
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "secret-password"},
        )
        assert blocked.status_code == 429

        user.locked_until = utcnow() - timedelta(seconds=1)
        db.commit()
        recovered = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "secret-password"},
        )
        assert recovered.status_code == 200
        db.refresh(user)
        assert user.failed_login_count == 0
        assert user.locked_until is None

        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"auth.login_failed", "auth.login_locked", "auth.login_blocked", "auth.login"}.issubset(actions)
    finally:
        app.dependency_overrides.clear()


def test_viewer_session_can_read_but_cannot_administer() -> None:
    db = make_session()
    client = make_client(db)
    viewer_token = create_dashboard_session(subject="viewer@example.com", role="viewer")

    try:
        response = client.get(
            "/api/v1/sites",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        write_response = client.post(
            "/api/v1/sites",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={"name": "Forbidden"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert write_response.status_code == 403
    assert write_response.json()["detail"] == "Administrator role required"


def test_bootstrap_dashboard_admin_rejects_short_password(monkeypatch) -> None:
    db = make_session()
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(
            main_module.settings,
            dashboard_admin_email="pilot@example.com",
            dashboard_admin_password="too-short",
        ),
    )

    with pytest.raises(RuntimeError, match="at least 12 characters"):
        bootstrap_dashboard_admin(db)


def test_logout_revokes_existing_user_session() -> None:
    db = make_session()
    db.add(User(email="admin@example.com", password_hash=hash_password("secret-password"), role="admin"))
    db.commit()
    client = make_client(db)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "secret-password"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        revoked = client.get("/api/v1/auth/me", headers=headers)
        assert revoked.status_code == 403
        assert revoked.json()["detail"] == "Dashboard session revoked"
    finally:
        app.dependency_overrides.clear()


def test_password_change_revokes_sessions_and_accepts_new_password() -> None:
    db = make_session()
    db.add(User(email="admin@example.com", password_hash=hash_password("old-secret-password"), role="admin"))
    db.commit()
    client = make_client(db)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "old-secret-password"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        changed = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "old-secret-password", "new_password": "new-secret-password"},
        )
        assert changed.status_code == 200
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
        assert client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "new-secret-password"},
        ).status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_user_administration_and_last_admin_guard() -> None:
    db = make_session()
    admin = User(email="admin@example.com", password_hash=hash_password("admin-password"), role="admin")
    db.add(admin)
    db.commit()
    client = make_client(db)
    try:
        created = client.post(
            "/api/v1/users",
            headers={"Authorization": "Bearer dev-admin-token"},
            json={"email": "viewer@example.com", "password": "viewer-password", "role": "viewer"},
        )
        assert created.status_code == 200
        assert created.json()["active"] is True
        viewer_id = created.json()["id"]
        promoted = client.patch(
            f"/api/v1/users/{viewer_id}",
            headers={"Authorization": "Bearer dev-admin-token"},
            json={"role": "admin"},
        )
        assert promoted.status_code == 200
        assert promoted.json()["role"] == "admin"
        disabled = client.patch(
            f"/api/v1/users/{viewer_id}",
            headers={"Authorization": "Bearer dev-admin-token"},
            json={"active": False},
        )
        assert disabled.status_code == 200
        blocked = client.patch(
            f"/api/v1/users/{admin.id}",
            headers={"Authorization": "Bearer dev-admin-token"},
            json={"active": False},
        )
        assert blocked.status_code == 409
    finally:
        app.dependency_overrides.clear()
