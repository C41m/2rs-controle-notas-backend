# app/api/v1/atividades.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.nota_fiscal import NotaFiscal
from app.schemas.nota_fiscal import NotaFiscalCreate, NotaFiscal
from app.schemas.usuario import User
from app.core.security import get_current_user
from app.crud.atividade import get_atividades_by_id_usuario
from app.schemas.atividade import Atividade

router = APIRouter()


@router.get("/", response_model=list[Atividade])
async def listar_minhas_atividades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    atividades = await get_atividades_by_id_usuario(db, current_user.id)
    return atividades
