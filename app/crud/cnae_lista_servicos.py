# app/crud/cnae_lista_servicos.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.cnae_lista_servicos import CnaeListaAtividades
import uuid
from fastapi import APIRouter, Depends, HTTPException, status


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid

from app.schemas.usuario import User

async def get_cnae_atividade(db: AsyncSession, current_user: User):
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação.",
        )        
    
    result = await db.execute(select(CnaeListaAtividades))
    
    return result.scalars().all()


async def get_codigo_servico_by_cnae(db: AsyncSession, cnae: str):
    result = await db.execute(
        select(CnaeListaAtividades.codigo_lista_servico)
        .where(CnaeListaAtividades.cnae_numerico == cnae)
        .limit(1) 
    )
    return result.scalar()