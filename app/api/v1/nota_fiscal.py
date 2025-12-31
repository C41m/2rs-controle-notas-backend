# app/api/v1/invoices.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.nota_fiscal import (
    NotaFiscal,
    NotaFiscalCreate,
    NotaFiscalComCliente,
    NotaFiscalComClienteEUsuario,
    AtualizarStatusNotaPayload,
    AtualizarStatusMotivoNotaPayload,
    AtualizarStutasNotaAceitePayload,
)
from app.schemas.usuario import User
from app.schemas.cliente import Cliente
from app.core.security import get_current_user
from app.crud.nota_fiscal import (
    create_nota_fiscal,
    get_notas_by_usuario,
    update_status_nota,
    update_nota_fiscal,
    get_todas_notas,
    get_nota_usuario_by_id,
    recusar_nota_fiscal,
    aprovar_nota_fiscal,
    emitir_nota_finalizada,
)
from app.crud.cliente import (
    get_cliente_by_id_usuario,
    create_cliente,
    get_cliente_by_cpf_cnpj,
)

from app.crud.cnae_lista_servicos import get_codigo_servico_by_cnae

from app.core.email import send_admin_notification

router = APIRouter()


@router.post("/", response_model=NotaFiscal, status_code=status.HTTP_201_CREATED)
async def emitir_nota(
    nota_nova: NotaFiscalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Verifica se existe cliente
    cliente: Cliente = await get_cliente_by_cpf_cnpj(
        db, nota_nova.cpf_cnpj, current_user.id
    )

    # Cria cliente se necessário
    if cliente is None:
        cliente_data = {
            "razao_social": nota_nova.razao_social,
            "cpf_cnpj": nota_nova.cpf_cnpj,
            "email": nota_nova.email,
            "telefone": nota_nova.telefone,
            "pais": nota_nova.pais,
            "uf": nota_nova.uf,
            "cidade": nota_nova.cidade,
            "cep": nota_nova.cep,
            "logradouro": nota_nova.logradouro,
            "numero": nota_nova.numero,
            "complemento": nota_nova.complemento,
            "bairro": nota_nova.bairro,
        }

        cliente = await create_cliente(db, cliente_data, current_user.id)

    else:

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado.",
            )
        if cliente.usuario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para emitir nota para este cliente.",
            )

    codigo_lista_servico = await get_codigo_servico_by_cnae(db, nota_nova.cod_cnae)
    
    if codigo_lista_servico is None:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi encontrado código da Lista de Serviços para o CNAE {nota_nova.cod_cnae}."
        )
    
    # Prepara dados da nota fiscal
    nota_data = {
        "usuario_id": current_user.id,
        "cliente_id": cliente.id,
        "cod_cnae": nota_nova.cod_cnae,
        "valor_total": nota_nova.valor_total,
        "descricao": nota_nova.descricao,
        "status_id": 1,
        "aliquota": current_user.aliquota,
        "codigo_lista_servico": codigo_lista_servico,
    }

    # Cria a nota fiscal no banco
    nota_fiscal = await create_nota_fiscal(db, nota_data)

    # # 👇 Envia notificação ao administrador
    # try:
    #     await send_admin_notification(
    #         nota_id=nota_fiscal.id,
    #         cliente_nome=nota_nova.razao_social or nota_nova.cpf_cnpj,
    #         valor_total=nota_nova.valor_total,
    #         descricao=nota_nova.descricao or "Sem descrição",
    #         usuario_emissor=current_user.email,  # ou current_user.nome, se existir
    #     )
    # except Exception as e:
    #     # Loga o erro, mas não quebra o fluxo principal
    #     print(f"[ALERTA] Falha ao enviar notificação por e-mail: {e}")

    return nota_fiscal


@router.post(
    "/emitir-finalizada", response_model=NotaFiscal, status_code=status.HTTP_201_CREATED
)
async def emitir_nota_finalizada_endpoint(
    payload: AtualizarStutasNotaAceitePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await emitir_nota_finalizada(db, payload.nota_id ,current_user)


@router.get("/", response_model=list[NotaFiscalComCliente])
async def listar_minhas_notas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notas = await get_notas_by_usuario(db, current_user.id)

    return notas or []


@router.get("/admin", response_model=list[NotaFiscalComClienteEUsuario])
async def listar_notas(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):

    notas = await get_todas_notas(db, current_user)

    return notas


@router.get("/{nota_id}", response_model=NotaFiscalComCliente)
async def listar_minhas_notas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    nota_id: int = None,
):

    notas = await get_nota_usuario_by_id(db, current_user.id, nota_id)

    return notas or []


@router.put("/recusar", response_model=NotaFiscal)
async def recusar_nota(
    nota_atualizada: AtualizarStatusMotivoNotaPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação.",
        )

    nota = await recusar_nota_fiscal(
        db,
        nota_atualizada.nota_id,
        nota_atualizada.status_id,
        nota_atualizada.desc_motivo,
    )

    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada ou sem permissão.",
        )

    return nota


@router.put("/aprovar", response_model=NotaFiscal)
async def aprovar_nota(
    payload: AtualizarStutasNotaAceitePayload,  # ← só nota_id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem executar esta ação."
        )

    nota = await aprovar_nota_fiscal(db, payload.nota_id)  # ← só ID
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    return nota


@router.put("/{nota_id}/status", response_model=NotaFiscal)
async def atualizar_status(
    nota_id: int,
    payload: AtualizarStatusNotaPayload,
    db: AsyncSession = Depends(get_db),
):
    return await update_status_nota(db, nota_id, payload.status_id)


@router.put("/{nota_id}", response_model=NotaFiscalComCliente)
async def atualizar_nota(
    nota_id: int,
    nota_atualizada: NotaFiscalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nota = await update_nota_fiscal(db, nota_id, current_user.id, nota_atualizada)

    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada ou sem permissão.",
        )

    return nota
