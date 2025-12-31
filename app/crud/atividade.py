from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import *
from app.schemas.cliente import ClienteCreate
import uuid
from fastapi import APIRouter, Depends, HTTPException, status


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Atividade
import uuid


async def get_atividades_by_id_usuario(db: AsyncSession, usuario_id: uuid.UUID):
    result = await db.execute(
        select(Atividade).where(Atividade.usuario_id == usuario_id)
    )
    return result.scalars().all()
