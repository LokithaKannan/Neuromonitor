"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.base import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.session import ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()

    if payload.email is not None:
        # Check uniqueness
        result = await db.execute(
            select(User).where(User.email == payload.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        current_user.email = payload.email

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required")
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password incorrect")
        current_user.hashed_password = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(current_user)
    return current_user
