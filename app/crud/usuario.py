# app/crud/usuario.py

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.schemas.atividade import AtividadeCreate
from app.schemas.usuario import User, UserUpdate
from sqlalchemy import delete
import uuid
from app.models import NotaFiscal
from sqlalchemy import update
from sqlalchemy.future import select
from app.models.usuario import Usuario
from app.models.atividade import Atividade


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.role))
        .where(Usuario.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_documento(db: AsyncSession, documento: str):
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.role), selectinload(Usuario.atividades))
        .where(Usuario.cnpj_cpf == documento)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    cnpj_cpf: str,
    razao_social: str,
    role_id: int,
    aliquota: float | None = None,
    telefone: str | None = None,
    pais: str | None = None,
    uf: str | None = None,
    cidade: str | None = None,
    cep: str | None = None,
    logradouro: str | None = None,
    numero: str | None = None,
    complemento: str | None = None,
    bairro: str | None = None,
    insc_municipal: str | None = None,
    emite: bool | None = None,
    atividades: list[AtividadeCreate] | None = None,
):
    db_user = Usuario(
        email=email,
        hashed_password=hashed_password,
        cnpj_cpf=cnpj_cpf,
        razao_social=razao_social,
        role_id=role_id,
        aliquota=aliquota,
        telefone=telefone,
        pais=pais,
        uf=uf,
        cidade=cidade,
        cep=cep,
        logradouro=logradouro,
        numero=numero,
        complemento=complemento,
        bairro=bairro,
        insc_municipal=insc_municipal,
        emite=emite
    )
    db.add(db_user)
    await db.flush()  # necessário para obter o ID antes de criar atividades

    if atividades:
        for atv_data in atividades:
            atividade = Atividade( 
                cod_cnae=str(atv_data["cod_cnae"]),
                desc_cnae=atv_data["desc_cnae"],
                usuario_id=db_user.id
            )
            db.add(atividade)

    await db.commit()

    # ✅ Agora, recarregue o usuário com as atividades eager-loaded
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.atividades))
        .where(Usuario.id == db_user.id)
    )
    return result.scalar_one()


async def get_users(
    db: AsyncSession, current_user: User, skip: int = 0, limit: int = 100
):

    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão.",
        )

    usuarios = await db.scalars(
        select(Usuario).where(Usuario.role_id != 1)
        .options(selectinload(Usuario.atividades))
        .offset(skip)
        .limit(limit)
    )

    if not usuarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuários nao encontrados."
        )

    return usuarios


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_update: UserUpdate,
    current_user_id: uuid.UUID,
    is_admin: bool = False,
):
    # 1. Buscar o usuário a ser atualizado
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.atividades))
        .where(Usuario.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # 2. Verificar permissão: só admin pode editar outros
    if not is_admin and db_user.id != current_user_id:
        raise HTTPException(status_code=403, detail="Não autorizado")

    # 3. Atualizar campos simples
    update_data = user_update.model_dump(exclude_unset=True)

    # Se não for admin, bloqueie alterações sensíveis
    if not is_admin:
        update_data.pop("role_id", None)
        update_data.pop("email", None)  # opcional: permitir mudança de email?
        update_data.pop("cnpj_cpf", None)  # geralmente não se muda

    for field, value in update_data.items():
        if field != "atividades":
            setattr(db_user, field, value)

    # 4. Atualizar atividades (substituir todas)
    if "atividades" in update_data and update_data["atividades"] is not None:
        # Apagar atividades antigas
        await db.execute(delete(Atividade).where(Atividade.usuario_id == user_id))

        # Adicionar as novas
        for atv in update_data["atividades"]:
            nova_atividade = Atividade(
                cod_cnae=str(atv["cod_cnae"]),
                desc_cnae=atv["desc_cnae"],
                usuario_id=user_id,
            )
            db.add(nova_atividade)

    # 5. Salvar
    await db.commit()
    await db.refresh(db_user)

    # 6. Recarregar com atividades
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.atividades))
        .where(Usuario.id == user_id)
    )
    return result.scalar_one()


async def delete_user(db: AsyncSession, user_id: uuid.UUID, admin_user_id: uuid.UUID):
    # 1. Verificar se o próprio admin não está tentando se excluir
    if user_id == admin_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode excluir sua própria conta.",
        )

    # 2. Verificar se o usuário existe
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # 3. Excluir (as atividades são excluídas em cascata pelo SQLAlchemy)
    await db.execute(delete(Usuario).where(Usuario.id == user_id))
    await db.commit()

    return {"message": "Usuário excluído com sucesso"}


async def atualizar_aliquotas_notas_em_lote(db: AsyncSession):
    result = await db.execute(
        select(Usuario.id, Usuario.aliquota).where(Usuario.aliquota.isnot(None))
    )
    usuarios = result.fetchall()

    total_notas_atualizadas = 0

    for user_id, aliquota_usuario in usuarios:
        stmt = (
            update(NotaFiscal)
            .where(
                NotaFiscal.usuario_id == user_id,
                NotaFiscal.status_id == 1,
                (NotaFiscal.aliquota != aliquota_usuario)
                | (NotaFiscal.aliquota.is_(None)),
            )
            .values(aliquota=aliquota_usuario)
        )
        res = await db.execute(stmt)
        total_notas_atualizadas += res.rowcount

    await db.commit()

    return {
        "total_usuarios": len(usuarios),
        "total_notas_atualizadas": total_notas_atualizadas,
    }
