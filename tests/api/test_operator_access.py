from __future__ import annotations

import time
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
from secopsai_api.mfa import current_totp
from secopsai_api.models import (
    AccountAccessToken,
    AuditLog,
    Base,
    DEFAULT_ORGANIZATION_ID,
    MfaRecoveryCode,
    OrganizationMembership,
    User,
    utcnow,
)
from secopsai_api.security import hash_password
from secopsai_api.tenancy import ensure_default_organization


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


def operator_settings():
    return replace(
        main_module.settings,
        dashboard_reset_url="https://edge.example.test/settings",
        dashboard_invite_url="https://edge.example.test/settings",
        smtp_host="smtp.example.test",
        token_secret="operator-access-token-secret-that-is-not-global",
        mfa_encryption_key="operator-access-mfa-key-that-is-not-global",
        invitation_ttl_seconds=3600,
    )


def create_operator(db: Session, *, email: str = "owner@example.com", role: str = "owner") -> User:
    organization = ensure_default_organization(db)
    user = User(
        email=email,
        password_hash=hash_password("operator-password"),
        password_ready=True,
        role=role,
        active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            role=role,
            active=True,
        )
    )
    db.commit()
    return user


def test_invitation_delivers_to_pending_user_and_creates_membership(monkeypatch) -> None:
    db = make_session()
    settings = operator_settings()
    monkeypatch.setattr(main_module, "settings", settings)
    delivered_messages = []
    monkeypatch.setattr(
        recovery_module,
        "send_email_message",
        lambda message, current_settings: delivered_messages.append(message),
    )
    client = make_client(db)
    admin_headers = {"Authorization": "Bearer dev-admin-token"}

    try:
        invited = client.post(
            "/api/v1/user-invitations",
            headers=admin_headers,
            json={"email": "PILOT@example.com", "role": "viewer"},
        )
        assert invited.status_code == 200
        assert invited.json()["email"] == "pilot@example.com"
        assert invited.json()["state"] == "pending"
        pending_user = db.scalar(select(User).where(User.email == "pilot@example.com"))
        assert pending_user is not None
        assert pending_user.active is False
        assert pending_user.password_ready is False
        assert db.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == pending_user.id)
        ) is None

        delivery = client.post("/api/v1/account-access/run-due", headers=admin_headers)
        assert delivery.json() == {"processed": 1, "delivered": 1, "retrying": 0, "failed": 0}
        assert len(delivered_messages) == 1
        invitation_link = next(
            line
            for line in delivered_messages[0].get_content().splitlines()
            if "#invitation_token=" in line
        )
        invitation_token = invitation_link.split("#invitation_token=", 1)[1]
        row = db.scalar(select(AccountAccessToken))
        assert row is not None
        assert invitation_token not in row.token_hash
        assert row.organization_id == DEFAULT_ORGANIZATION_ID

        accepted = client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "new-pilot-password"},
        )
        assert accepted.status_code == 200
        assert accepted.json() == {"status": "invitation_accepted"}
        db.refresh(pending_user)
        assert pending_user.active is True
        assert pending_user.password_ready is True
        membership = db.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == pending_user.id)
        )
        assert membership is not None
        assert membership.role == "viewer"
        assert client.post(
            "/api/v1/auth/login",
            json={"email": pending_user.email, "password": "new-pilot-password"},
        ).status_code == 200
        assert client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "another-pilot-password"},
        ).status_code == 400
        actions = {item.action for item in db.query(AuditLog).all()}
        assert {"user.invited", "user.invitation_accepted"}.issubset(actions)
    finally:
        app.dependency_overrides.clear()


def test_disabled_user_login_fails_before_session_issuance() -> None:
    db = make_session()
    user = create_operator(db, role="admin")
    membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
    )
    assert membership is not None
    membership.active = False
    user.active = False
    db.commit()
    client = make_client(db)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "operator-password"},
        )
        assert response.status_code == 403
        assert "access_token" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_existing_user_invitation_password_attempts_lock_then_recover(monkeypatch) -> None:
    db = make_session()
    settings = replace(operator_settings(), login_max_attempts=2, login_lockout_seconds=60)
    monkeypatch.setattr(main_module, "settings", settings)
    existing_user = create_operator(db, email="existing@example.com", role="viewer")
    existing_membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == existing_user.id
        )
    )
    assert existing_membership is not None
    existing_membership.active = False
    db.commit()
    client = make_client(db)
    admin_headers = {"Authorization": "Bearer dev-admin-token"}

    try:
        invited = client.post(
            "/api/v1/user-invitations",
            headers=admin_headers,
            json={"email": existing_user.email, "role": "viewer"},
        )
        assert invited.status_code == 200
        invitation = db.scalar(
            select(AccountAccessToken).where(
                AccountAccessToken.user_id == existing_user.id,
                AccountAccessToken.purpose == recovery_module.USER_INVITATION_PURPOSE,
            )
        )
        assert invitation is not None
        invitation_token = recovery_module.materialize_access_token(invitation, settings)

        first = client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "wrong-password"},
        )
        second = client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "wrong-password"},
        )
        blocked = client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "operator-password"},
        )

        assert first.status_code == 403
        assert second.status_code == 429
        assert blocked.status_code == 429
        db.refresh(existing_user)
        assert existing_user.failed_login_count == 2
        assert existing_user.locked_until is not None
        actions = {item.action for item in db.query(AuditLog).all()}
        assert {
            "auth.invitation_password_failed",
            "auth.invitation_password_locked",
            "auth.invitation_password_blocked",
        }.issubset(actions)

        existing_user.locked_until = utcnow() - timedelta(seconds=1)
        db.commit()
        accepted = client.post(
            "/api/v1/user-invitations/accept",
            json={"token": invitation_token, "password": "operator-password"},
        )
        assert accepted.status_code == 200
        db.refresh(existing_user)
        assert existing_user.failed_login_count == 0
        assert existing_user.locked_until is None
    finally:
        app.dependency_overrides.clear()


def test_mfa_setup_login_replay_protection_recovery_and_disable(monkeypatch) -> None:
    db = make_session()
    user = create_operator(db)
    settings = operator_settings()
    monkeypatch.setattr(main_module, "settings", settings)
    client = make_client(db)

    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "operator-password"},
        )
        session_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        setup = client.post(
            "/api/v1/auth/mfa/setup",
            headers=session_headers,
            json={"current_password": "operator-password"},
        )
        assert setup.status_code == 200
        secret = setup.json()["secret"]
        assert setup.json()["provisioning_uri"].startswith("otpauth://totp/")
        db.refresh(user)
        assert secret not in str(user.mfa_pending_secret_ciphertext)

        initial_code = current_totp(secret)
        enabled = client.post(
            "/api/v1/auth/mfa/enable",
            headers=session_headers,
            json={"code": initial_code},
        )
        assert enabled.status_code == 200
        original_recovery_codes = enabled.json()["recovery_codes"]
        assert len(original_recovery_codes) == 10
        assert db.query(MfaRecoveryCode).count() == 10
        assert client.get("/api/v1/auth/me", headers=session_headers).status_code == 403

        challenged = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "operator-password"},
        )
        assert challenged.status_code == 200
        assert challenged.json()["access_token"] is None
        assert challenged.json()["mfa_required"] is True
        challenge = challenged.json()["mfa_challenge"]
        next_code = current_totp(secret, at_time=int(time.time()) + 30)
        verified = client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge": challenge, "code": next_code},
        )
        assert verified.status_code == 200
        assert verified.json()["access_token"]
        verified_headers = {
            "Authorization": f"Bearer {verified.json()['access_token']}"
        }
        assert client.post(
            "/api/v1/auth/mfa/setup",
            headers=verified_headers,
            json={"current_password": "operator-password"},
        ).status_code == 409
        assert client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge": challenge, "code": next_code},
        ).status_code == 403

        recovery_challenge = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "operator-password"},
        ).json()["mfa_challenge"]
        recovery_login = client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge": recovery_challenge, "code": original_recovery_codes[0]},
        )
        recovery_headers = {"Authorization": f"Bearer {recovery_login.json()['access_token']}"}
        assert client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge": recovery_challenge, "code": original_recovery_codes[0]},
        ).status_code == 403

        regenerated = client.post(
            "/api/v1/auth/mfa/recovery-codes",
            headers=recovery_headers,
            json={
                "current_password": "operator-password",
                "code": original_recovery_codes[1],
            },
        )
        assert regenerated.status_code == 200
        replacement_codes = regenerated.json()["recovery_codes"]
        assert replacement_codes != original_recovery_codes
        disabled = client.post(
            "/api/v1/auth/mfa/disable",
            headers=recovery_headers,
            json={
                "current_password": "operator-password",
                "code": replacement_codes[0],
            },
        )
        assert disabled.status_code == 200
        db.refresh(user)
        assert user.mfa_enabled_at is None
        assert db.query(MfaRecoveryCode).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_owner_can_reset_another_operator_mfa_but_not_their_own(monkeypatch) -> None:
    db = make_session()
    settings = operator_settings()
    monkeypatch.setattr(main_module, "settings", settings)
    owner = create_operator(db, email="owner-mfa@example.com", role="owner")
    target = create_operator(db, email="target-mfa@example.com", role="admin")
    target.mfa_secret_ciphertext = "v1.encrypted-placeholder"
    target.mfa_enabled_at = utcnow()
    target.mfa_last_counter = 42
    db.add(
        MfaRecoveryCode(
            user_id=target.id,
            code_hash="a" * 64,
        )
    )
    db.commit()
    client = make_client(db)

    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": owner.email, "password": "operator-password"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.post(
            f"/api/v1/users/{owner.id}/mfa-reset",
            headers=headers,
        ).status_code == 409

        reset = client.post(
            f"/api/v1/users/{target.id}/mfa-reset",
            headers=headers,
        )
        assert reset.status_code == 200
        db.refresh(target)
        assert target.mfa_enabled_at is None
        assert target.mfa_secret_ciphertext is None
        assert db.scalar(
            select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == target.id)
        ) is None
        actions = {item.action for item in db.query(AuditLog).all()}
        assert "user.mfa_reset" in actions
    finally:
        app.dependency_overrides.clear()
