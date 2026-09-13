import pytest
import time
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException

from app.main import app
from app.services.auth_service import auth_service
from app.config import settings
from app.db.connection import init_db

@pytest.mark.asyncio
async def test_auth_service_token_verification():
    """Verify Supabase JWT token verification and user extraction."""
    user_id = "supa-user-uuid-9988"
    email = "test.candidate@gmail.com"
    name = "Vikram Aditya"

    token = auth_service.create_mock_jwt(user_id=user_id, email=email, name=name)
    assert token is not None

    # Verify token
    payload = auth_service.verify_token(token)
    assert payload["sub"] == user_id
    assert payload["email"] == email

    # Extract user info
    info = auth_service.extract_user_info(payload)
    assert info["user_id"] == user_id
    assert info["email"] == email
    assert info["name"] == name

@pytest.mark.asyncio
async def test_auth_service_expired_token_rejected():
    """Verify expired token raises HTTP 401."""
    token = auth_service.create_mock_jwt(
        user_id="expired-user",
        expires_in_seconds=-10  # already expired
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()

@pytest.mark.asyncio
async def test_auth_service_malformed_token_rejected():
    """Verify malformed token raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_token("invalid.jwt.token.string")
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_api_auth_me_auto_provisions_user():
    """
    Verify GET /api/auth/me with Bearer token automatically provisions
    the candidate record in UserModel on their very first request.
    """
    await init_db()
    user_id = f"supa-auto-{int(time.time())}"
    token = auth_service.create_mock_jwt(
        user_id=user_id,
        email="auto.provision@test.com",
        name="Auto Provisioned User"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == user_id
        assert data["email"] == "auto.provision@test.com"
        assert data["name"] == "Auto Provisioned User"
        assert data["target_role"] == "Full Stack Software Engineer"
        assert data["stats"]["total_interviews"] == 0

@pytest.mark.asyncio
async def test_api_auth_sync_and_profile_update():
    """
    Verify POST /api/auth/sync and PUT /api/auth/profile for updating candidate career targets.
    """
    await init_db()
    user_id = f"supa-sync-{int(time.time()*1000)}"
    test_email = f"sync.{user_id}@test.com"
    token = auth_service.create_mock_jwt(user_id=user_id, email=test_email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sync user from Supabase session
        sync_payload = {
            "id": user_id,
            "email": test_email,
            "name": "Sync Candidate",
            "github_handle": "synccoder",
            "leetcode_handle": "syncleet",
            "codeforces_handle": "synccf"
        }
        res_sync = await client.post("/api/auth/sync", json=sync_payload)
        assert res_sync.status_code == 200
        sync_data = res_sync.json()
        assert sync_data["id"] == user_id
        assert sync_data["github_handle"] == "synccoder"
        assert sync_data["leetcode_handle"] == "syncleet"

        # 2. Update profile with custom target preferences
        update_payload = {
            "target_company": "Amazon",
            "target_role": "Backend Architect",
            "target_location": "Hyderabad",
            "experience_level": "Senior"
        }
        res_update = await client.put(
            "/api/auth/profile",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_update.status_code == 200
        up_data = res_update.json()
        assert up_data["target_company"] == "Amazon"
        assert up_data["target_role"] == "Backend Architect"
        assert up_data["target_location"] == "Hyderabad"
        assert up_data["experience_level"] == "Senior"

        # 3. GET /api/auth/me should reflect the updated profile
        res_me = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["target_company"] == "Amazon"
        assert me_data["github_handle"] == "synccoder"

@pytest.mark.asyncio
async def test_backward_compatibility_with_x_user_id():
    """
    Verify that existing API endpoints still support X-User-Id header
    for mock and test workflows without breaking.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/auth/me",
            headers={"x-user-id": "legacy-test-user-007"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "legacy-test-user-007"
