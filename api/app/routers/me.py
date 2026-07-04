"""Identity endpoint: echoes the authenticated user derived from the JWT."""

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=CurrentUser)
async def read_me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Return the current user. Requires a valid Supabase bearer token."""
    return user
