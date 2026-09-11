from fastapi import Request, Header
from typing import Optional

async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(default=None)
) -> str:
    """
    Dependency injection for user identity.
    Decoupled from Auth / User Management so that:
    1. During current Phase 1 development, all endpoints use this consistent user_id contract.
    2. Once Auth & User Management (JWT / OAuth / NextAuth) are implemented,
       we only update this single function to validate the auth token/session,
       and all backend routes and agents immediately work without refactoring.
    """
    if x_user_id:
        return x_user_id
    
    # Check query params or session if available
    user_id_param = request.query_params.get("user_id")
    if user_id_param:
        return user_id_param

    return "candidate-default-001"
