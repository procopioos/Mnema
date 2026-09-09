from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


class SetupStatus(BaseModel):
    required: bool


@router.get("/setup", response_model=SetupStatus)
async def setup_status(db: DbSession) -> SetupStatus:
    """Whether the app still needs its first administrator account (empty DB)."""
    count = await db.scalar(select(func.count()).select_from(User)) or 0
    return SetupStatus(required=count == 0)
