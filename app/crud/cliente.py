from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import *
from app.schemas.cliente import ClienteCreate
import uuid
from fastapi import APIRouter, Depends, HTTPException, status


async def get_cliente_by_id(db: AsyncSession, id: int):
    query = select(Cliente).where(Cliente.id == id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_cliente_by_id_usuario(db: AsyncSession, id: int, current_user: str):
    query = (
        select(Cliente)
        .where(Cliente.usuario_id == current_user)
        .where(Cliente.id == id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_cliente_by_cpf_cnpj(db: AsyncSession, cpf_cnpj: str, current_user: str):
    print(f"Buscando cliente com cpf_cnpj={cpf_cnpj}, usuario_id={current_user}")
    query = (
        select(Cliente)
        .where(Cliente.usuario_id == current_user)
        .where(Cliente.cpf_cnpj == cpf_cnpj)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_clientes_by_usuario_id(db: AsyncSession, usuario_id: int):
    query = select(Cliente).where(Cliente.usuario_id == usuario_id)
    result = await db.execute(query)
    return result.scalars().all()


# crud/cliente.py (ou em um arquivo de serviço)
async def create_cliente(
    db: AsyncSession,
    cliente_data: dict,
    usuario_id: uuid.UUID,
) -> Cliente:
    
    # Verifica se já existe
    cliente_existente = await get_cliente_by_cpf_cnpj(
        db, cliente_data["cpf_cnpj"], usuario_id
    )
    if cliente_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe um cliente com esse CPF/CNPJ. ({cliente_existente.razao_social} - {cliente_existente.cpf_cnpj})",
        )

    # Cria novo cliente
    cliente_data["usuario_id"] = usuario_id
    db_cliente = Cliente(**cliente_data)
    db.add(db_cliente)
    await db.commit()
    await db.refresh(db_cliente)
    return db_cliente


async def delete_cliente(db: AsyncSession, id: int, current_user: str):
    query = (
        select(Cliente)
        .where(Cliente.id == id)
        .where(Cliente.usuario_id == current_user)
    )
    result = await db.execute(query)
    cliente = result.scalar_one_or_none()
    if not cliente:
        return None
    await db.delete(cliente)
    await db.commit()
    return


async def edita_cliente(db: AsyncSession, id: int, cliente_data: dict):
    query = select(Cliente).where(Cliente.id == id)
    result = await db.execute(query)
    cliente = result.scalar_one_or_none()
    if not cliente:
        return None
    for key, value in cliente_data.items():
        setattr(cliente, key, value)
    await db.commit()
    await db.refresh(cliente)
    return


async def get_todos_os_clientes(db: AsyncSession):
    result = await db.execute(select(Cliente))
    return result.scalars().all()
