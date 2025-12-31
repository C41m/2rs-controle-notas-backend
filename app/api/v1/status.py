from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.core.security import get_current_user
from app.schemas.usuario import User  # Schema do usuário autenticado
from app.crud.status import get_status_by_id, get_all_status
from app.schemas.status_nota import StatusNota as StatusNotaSchema

router = APIRouter()


@router.get("/", response_model=List[StatusNotaSchema])
async def get_all_status_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ← Protegido
):
    return await get_all_status(db)


@router.get("/{id}", response_model=StatusNotaSchema)
async def get_status_by_id_endpoint(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ← Protegido
):
    status = await get_status_by_id(db, id)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status não encontrado"
        )
    return status