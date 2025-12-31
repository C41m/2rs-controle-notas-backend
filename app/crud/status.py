# app/crud/status.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import *
from app.schemas.cliente import ClienteCreate
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Atividade
import uuid


async def get_status_by_id(db: AsyncSession, status_id: int) -> Optional[StatusNota]:
    result = await db.execute(select(StatusNota).where(StatusNota.id == status_id))
    return result.scalar_one_or_none()


async def get_all_status(db: AsyncSession) -> List[StatusNota]:
    result = await db.execute(select(StatusNota))
    return result.scalars().all()
