# app/api/v1/usuarios.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud.usuario import get_users
from app.core.security import get_current_user
from app.schemas.usuario import User, UserBase
from app.models.usuario import Usuario
from app.schemas.nota_fiscal import NotaFiscal
from sqlalchemy import update, select
from app.crud.usuario import atualizar_aliquotas_notas_em_lote, get_user_by_documento

router = APIRouter()


@router.get("/", response_model=list[User])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    usuarios = await get_users(db, current_user, skip=0, limit=100)
    return usuarios


@router.post("/atualizar-aliquotas-lote")
async def atualizar_aliquotas_lote(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação.",
        )

    resultado = await atualizar_aliquotas_notas_em_lote(db)
    return resultado


@router.get("/meusDadosUsuario", response_model=UserBase)
async def read_users_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Busca o usuário completo com relacionamentos (atividades, etc)
    full_user = await get_user_by_documento(db, current_user.cnpj_cpf)
    if not full_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return User.model_validate(full_user)
