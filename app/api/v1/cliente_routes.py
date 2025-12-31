from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.cliente import Cliente, ClienteCreate
from app.crud.cliente import (
    get_cliente_by_id,
    get_cliente_by_id_usuario,
    get_cliente_by_cpf_cnpj,
    create_cliente,
    get_clientes_by_usuario_id,
    delete_cliente,
    get_todos_os_clientes,
)
from app.core.security import get_current_user
from app.schemas.usuario import User

router = APIRouter()


@router.get("/{id}", response_model=Cliente)
async def obter_cliente_by_id(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role_id == 1:
        cliente = await get_cliente_by_id(db, id)

    else:
        cliente = await get_cliente_by_id_usuario(db, id, current_user.id)

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )

    return cliente or None

@router.get("/por-documento/{documento}", response_model=Cliente)
async def obter_cliente_by_documento(
    documento: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    cliente = await get_cliente_by_cpf_cnpj(db, documento, current_user.id)

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )

    return cliente or None




@router.post("/", response_model=Cliente, status_code=status.HTTP_201_CREATED)
async def criar_cliente(
    cliente_novo: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return await create_cliente(db, cliente_novo.model_dump(), current_user.id)


@router.get("/", response_model=list[Cliente])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role_id == 1:
        clientes = await get_todos_os_clientes(db)

    else:
        clientes = await get_clientes_by_usuario_id(db, current_user.id)

    return clientes or []


@router.delete("/{id}", status_code=status.HTTP_200_OK, response_model=dict)
async def deletar_cliente(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    cliente: Cliente = await get_cliente_by_id_usuario(db, id, current_user.id)

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )

    if cliente.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para excluir este cliente.",
        )

    nome = cliente.razao_social
    documento = cliente.cpf_cnpj

    # Formata documento como CPF ou CNPJ
    if len(documento) == 14:  # CNPJ limpo tem 14 dígitos
        documento_formatado = f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}"
    elif len(documento) == 11:  # CPF limpo tem 11 dígitos
        documento_formatado = (
            f"{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}"
        )
    else:
        documento_formatado = documento

    await delete_cliente(db, id, current_user.id)

    return {"detail": f"Cliente {nome} ({documento_formatado}) excluído com sucesso."}
