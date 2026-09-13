import time
import logging
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger("hireprep.auth")

class SupabaseAuthService:
    """
    Validates Supabase JWT tokens and extracts candidate identity.
    Supports:
    1. Live asymmetric verification using Supabase JWKS (ECC P-256 / ES256 / RS256).
    2. Symmetric HMAC-SHA256 verification using SUPABASE_JWT_SECRET.
    3. Seamless zero-config local development/testing fallback.
    """
    _jwks_client: Optional[jwt.PyJWKClient] = None

    @classmethod
    def get_jwks_client(cls) -> Optional[jwt.PyJWKClient]:
        if cls._jwks_client is None and settings.SUPABASE_URL:
            try:
                jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
                cls._jwks_client = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase JWKS client: {e}")
        return cls._jwks_client

    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """
        Validates a Supabase JWT Bearer token and returns claims payload.
        Raises HTTPException(401) on invalid or expired token.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 1. Asymmetric verification via Supabase JWKS (Active ECC P-256 / ES256)
        jwks = cls.get_jwks_client()
        if jwks:
            try:
                signing_key = jwks.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256", "RS256"],
                    options={"verify_aud": False}
                )
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("Supabase token expired.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception:
                # If not an asymmetric token, continue to secret / dev fallback
                pass

        # 2. Symmetric HS256 verification with SUPABASE_JWT_SECRET
        if settings.SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"verify_aud": False}
                )
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("Supabase token signature expired.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.PyJWTError as e:
                logger.warning(f"Invalid Supabase JWT signature: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid authentication token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # 2. Development / Testing mode: Decode without signature if secret not configured
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": True}
            )
            exp = payload.get("exp")
            if exp and time.time() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to decode token in dev mode: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def extract_user_info(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts structured user info from decoded Supabase claims."""
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        email = payload.get("email")
        metadata = payload.get("user_metadata", {}) or {}
        phone = payload.get("phone") or metadata.get("phone")

        # Extracted names & handles from OAuth (GitHub / Google)
        name = (
            metadata.get("full_name")
            or metadata.get("name")
            or (email.split("@")[0] if email else (f"User {phone[-4:]}" if phone else "Candidate"))
        )
        avatar_url = metadata.get("avatar_url") or metadata.get("picture")
        github_handle = metadata.get("user_name") if "github" in metadata.get("iss", "") else metadata.get("github_username")

        return {
            "user_id": user_id,
            "email": email,
            "phone": phone,
            "name": name,
            "avatar_url": avatar_url,
            "github_handle": github_handle,
            "metadata": metadata
        }

    @classmethod
    def create_mock_jwt(
        cls,
        user_id: str = "mock-user-123",
        email: str = "candidate@example.com",
        name: str = "Priya Sharma",
        phone: Optional[str] = None,
        role: str = "authenticated",
        expires_in_seconds: int = 3600
    ) -> str:
        """Helper to generate valid mock JWTs for tests and local dev."""
        secret = settings.SUPABASE_JWT_SECRET or "dev-secret-key-hireprep-ai-enterprise-9988-jwt-32bytes"
        payload = {
            "sub": user_id,
            "email": email,
            "phone": phone or "",
            "aud": "authenticated",
            "role": role,
            "user_metadata": {
                "full_name": name,
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
                "github_username": "priyacodes"
            },
            "exp": int(time.time()) + expires_in_seconds,
            "iat": int(time.time())
        }
        return jwt.encode(payload, secret, algorithm="HS256")

auth_service = SupabaseAuthService()
