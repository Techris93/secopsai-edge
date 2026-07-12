from collections.abc import Generator
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secopsai_api.database import get_db
import secopsai_api.main as main_module
from secopsai_api.main import app, bootstrap_dashboard_admin
from secopsai_api.models import Base, User
from secopsai_api.security import hash_password, verify_password


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
