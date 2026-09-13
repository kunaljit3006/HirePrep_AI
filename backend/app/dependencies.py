import logging
from typing import Optional
from fastapi import Request, Header, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.connection import get_db
from app.db.models import UserModel
from app.services.auth_service import auth_service

logger = logging.getLogger("hireprep.dependencies")

async def get_current_user_id(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None)
) -> str:
    """
    Dependency injection for user identity.
    1. Checks 'Authorization: Bearer <token>' and validates Supabase JWT token.
    2. If no Bearer token, checks 'X-User-Id' header for test/dev environments.
    3. Falls back to query parameter or default dev candidate.
    """
    # Direct test call support: extract from request.headers if not injected by FastAPI
    if not isinstance(authorization, str):
        authorization = None
        if hasattr(request, "headers") and request.headers:
            authorization = request.headers.get("authorization")

    if not isinstance(x_user_id, str):
        x_user_id = None
        if hasattr(request, "headers") and request.headers:
            x_user_id = request.headers.get("x-user-id")

    # 1. Bearer Token Verification
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        try:
            payload = auth_service.verify_token(token)
            user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if user_id:
                return str(user_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to verify Bearer token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. X-User-Id header (for testing and dev workflows)
    if x_user_id:
        return x_user_id

    # 3. Query param check (useful in WebSocket handshakes or quick dev calls)
    user_id_param = request.query_params.get("user_id")
    if user_id_param:
        return user_id_param

    # 4. Default candidate fallback for dev mode
    return "candidate-default-001"


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """
    Retrieves the authenticated UserModel from database.
    Automatically provisions/syncs new users if logging in via Supabase for the first time.
    """
    user_id = await get_current_user_id(request, authorization, x_user_id)

    # Look up user in database
    stmt = select(UserModel).where(UserModel.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        return user

    # Auto-provision user record
    email = None
    phone = None
    name = f"Candidate {user_id[-6:]}" if len(user_id) > 6 else "Candidate"
    avatar_url = None
    github_handle = None

    if authorization and authorization.lower().startswith("bearer "):
        try:
            token = authorization[7:].strip()
            payload = auth_service.verify_token(token)
            info = auth_service.extract_user_info(payload)
            raw_email = info.get("email")
            raw_phone = info.get("phone")
            email = raw_email.strip() if raw_email and raw_email.strip() else None
            phone = raw_phone.strip() if raw_phone and raw_phone.strip() else None
            name = info.get("name") or name
            avatar_url = info.get("avatar_url")
            github_handle = info.get("github_handle")
        except Exception:
            pass

    new_user = UserModel(
        id=user_id,
        email=email,
        phone=phone,
        name=name,
        avatar_url=avatar_url,
        github_handle=github_handle,
        target_role="Full Stack Software Engineer",
        target_company="Google",
        target_location="India",
        experience_level="Mid"
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Auto-provisioned new UserModel for {user_id} ({name})")
        return new_user
    except Exception as e:
        await db.rollback()
        logger.warning(f"Error auto-provisioning user {user_id}: {e}")
        # Retry lookup in case of race condition
        stmt = select(UserModel).where(UserModel.id == user_id)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing
        return new_user


class RateLimiter:
    """
    Sliding-window rate limiter powered by Redis with in-memory fallback.
    Prevents abuse of expensive LLM generation, resume parsing, and interview sessions.
    """
    def __init__(self, requests_limit: int = 60, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
        authorization: Optional[str] = Header(default=None),
        x_user_id: Optional[str] = Header(default=None)
    ) -> bool:
        from app.services.cache_service import cache_service

        user_id = await get_current_user_id(request, authorization, x_user_id)
        endpoint = request.url.path

        allowed, remaining = await cache_service.check_rate_limit(
            identifier=user_id,
            endpoint=endpoint,
            limit=self.requests_limit,
            window_seconds=self.window_seconds
        )

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded on {endpoint}. "
                    f"Maximum {self.requests_limit} requests allowed per {self.window_seconds}s."
                )
            )

        return True
