# app/crud/invoice.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import *
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func
from app.core.config import settings
import xml.etree.ElementTree as ET
import re
import httpx
import json
from datetime import datetime, date
import pytz
from typing import Optional

from app.schemas.nota_fiscal import NotaFiscalCreate
from app.schemas.usuario import User
from app.models import NotaFiscal, Cliente, Usuario, Atividade  # 👈 adicione Atividade
from app.crud.cnae_lista_servicos import get_codigo_servico_by_cnae


async def create_nota_fiscal(db: AsyncSession, nota_data: dict):
    db_nota = NotaFiscal(**nota_data)
    db.add(db_nota)
    await db.commit()
    await db.refresh(db_nota)
    return db_nota


async def get_notas_by_usuario(db: AsyncSession, usuario_id: str):
    result = await db.execute(
        select(NotaFiscal)
        .where(NotaFiscal.usuario_id == usuario_id)
        .where(NotaFiscal.status_id != 5)
        .options(
            selectinload(NotaFiscal.status),
            selectinload(NotaFiscal.usuario).selectinload(Usuario.atividades),
        )
    )
    notas = result.scalars().all()

    if notas:
        usuario = notas[0].usuario
        if usuario and usuario.atividades:
            cnae_to_desc = {a.cod_cnae: a.desc_cnae for a in usuario.atividades}
            for nota in notas:
                nota.desc_cnae = cnae_to_desc.get(nota.cod_cnae)
        else:
            for nota in notas:
                nota.desc_cnae = None

    await consultar_notas_em_processamento_api_by_usuario(db=db, usuario_id=usuario_id)
    return notas


async def get_nota_usuario_by_id(db: AsyncSession, usuario_id: str, nota_id: int):

    result = await db.execute(
        select(NotaFiscal)
        .where(NotaFiscal.id == nota_id, NotaFiscal.usuario_id == usuario_id)
        .options(
            selectinload(NotaFiscal.status),
            selectinload(NotaFiscal.usuario).selectinload(Usuario.atividades),
        )
    )
    return result.scalar_one_or_none()


async def get_todas_notas(db: AsyncSession, current_user: User):
    # Carrega cliente + usuario + atividades do usuário em todos os casos
    query = select(NotaFiscal).options(
        selectinload(NotaFiscal.cliente),
        selectinload(NotaFiscal.usuario).selectinload(Usuario.atividades),
        selectinload(NotaFiscal.status),
    )

    if current_user.role_id != 1:
        # Se não for admin, filtra pelo usuário (opcional, depende da regra de negócio)
        query = query.where(NotaFiscal.usuario_id == current_user.id)

    result = await db.execute(query)
    notas = result.scalars().all()

    # Agora podemos acessar atividades com segurança
    for nota in notas:
        atividade = next(
            (a for a in nota.usuario.atividades if a.cod_cnae == nota.cod_cnae), None
        )
        nota.desc_cnae = atividade.desc_cnae if atividade else None

    return notas


async def get_notas_fiscal_by_id(db: AsyncSession, nota_id: int):
    result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_id))
    return result.scalar_one_or_none()


async def insert_id_nota_api(db: AsyncSession, nota_id: int, id_api: int):
    result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_id))
    nota = result.scalar_one_or_none()
    if nota:
        nota.id_api = id_api
        await db.commit()
        await db.refresh(nota)
    return nota


async def update_status_nota(db: AsyncSession, nota_id: int, novo_status_id: int):
    result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_id))
    nota = result.scalar_one_or_none()
    if nota:
        nota.status_id = novo_status_id
        await db.commit()
        await db.refresh(nota)
    return nota


async def update_nota_fiscal(
    db: AsyncSession,
    nota_id: int,
    usuario_id: str,  # UUID como string
    nota_atualizada: NotaFiscalCreate,
):
    # Buscar a nota com o cliente
    result = await db.execute(
        select(NotaFiscal)
        .options(selectinload(NotaFiscal.cliente))
        .where(NotaFiscal.id == nota_id, NotaFiscal.usuario_id == usuario_id)
    )
    nota = result.scalar_one_or_none()

    if not nota:
        return None  # ou lançar exceção, mas prefiro tratar no controller

    # Atualizar cliente
    cliente = nota.cliente
    if cliente:
        for field, value in nota_atualizada.model_dump(exclude_unset=True).items():
            if field in Cliente.__table__.columns:
                setattr(cliente, field, value)
        cliente.usuario_id = usuario_id  # garantir consistência
    else:
        # Criar novo cliente (caso raro)
        cliente_data = nota_atualizada.model_dump(
            include={
                "razao_social",
                "cpf_cnpj",
                "email",
                "telefone",
                "pais",
                "uf",
                "cidade",
                "cep",
                "logradouro",
                "numero",
                "complemento",
                "bairro",
            }
        )
        cliente_data["usuario_id"] = usuario_id
        cliente = Cliente(**cliente_data)
        db.add(cliente)
        await db.flush()
        nota.cliente_id = cliente.id

    # Atualizar nota fiscal
    nota_fields = {"cod_cnae", "valor_total", "descricao"}
    for field in nota_fields:
        if hasattr(nota_atualizada, field):
            setattr(nota, field, getattr(nota_atualizada, field))

    nota.status_id = 1
    nota.desc_motivo = ""

    codigo_lista_servico = await get_codigo_servico_by_cnae(db, nota.cod_cnae)

    if codigo_lista_servico is None:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi encontrado código da Lista de Serviços para o CNAE {nota.cod_cnae}.",
        )

    nota.codigo_lista_servicos = codigo_lista_servico

    nota.data_atualizacao = func.now()
    await db.commit()
    await db.refresh(nota)

    # Recarregar com relacionamentos
    result = await db.execute(
        select(NotaFiscal)
        .options(selectinload(NotaFiscal.cliente), selectinload(NotaFiscal.status))
        .where(NotaFiscal.id == nota.id)
    )
    return result.scalar_one_or_none()


async def recusar_nota_fiscal(
    db: AsyncSession, nota_id: int, novo_status_id: int, desc_motivo: str
):
    nota = await db.get(NotaFiscal, nota_id)

    if nota.status_id != 1:
        raise HTTPException(
            status_code=400,
            detail="Apenas notas com status 'Pendente' podem ser recusadas. Atualize a página e tente novamente!",
        )

    result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_id))

    nota = result.scalar_one_or_none()

    if nota:
        nota.status_id = novo_status_id
        nota.desc_motivo = desc_motivo
        await db.commit()
        await db.refresh(nota)

    return nota


async def aprovar_nota_fiscal(db: AsyncSession, nota_id: int):
    nota = await db.get(NotaFiscal, nota_id)
    if not nota:
        return None

    if nota.status_id != 1:
        raise HTTPException(
            status_code=400,
            detail="Apenas notas com status 'Pendente' podem ser aprovadas.",
        )

    nota.status_id = 4  # ← Aprovação ⇒ status 4 (fixo)
    await db.commit()
    await db.refresh(nota)
    return nota


async def emitir_nota_finalizada(db: AsyncSession, nota_id: int, current_user: Usuario):
    # Busca nota com relacionamentos
    nota = await db.get(NotaFiscal, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Nota fiscal não encontrada.")

    if nota.status_id != 1:
        raise HTTPException(
            status_code=400,
            detail="Apenas notas com status 'Aguardando Validação' podem ser emitidas.",
        )

    if current_user.role_id == 2:  # Se for emissor
        if nota.usuario_id != current_user.id or current_user.emite == False:
            raise HTTPException(status_code=403, detail="Não autorizado.")

    if not nota.cliente:
        raise HTTPException(status_code=400, detail="Nota sem cliente associado!")

    prestador = await db.get(Usuario, nota.usuario_id)

    # ✅ Tenta emitir via SOAP ANTES de alterar o status
    try:
        await emitir_nfse_via_soap(
            db=db,
            nota=nota,
            prestador=prestador,
            tomador=nota.cliente,
            descricao=nota.descricao or "Emissão via sistema 2RS Contabilidade",
            email_destino=prestador.email,
        )
    except Exception as e:
        # ❌ Emissão falhou → NÃO atualiza status
        raise HTTPException(
            status_code=502, detail=f"Falha na emissão da NFSe: {str(e)}"
        )

    # ✅ Só agora atualiza o status
    nota.status_id = 6  # Em Processamento
    await db.commit()
    await db.refresh(nota)
    return nota


async def emitir_nfse_via_soap(
    db: AsyncSession,
    nota: NotaFiscal,
    prestador: Usuario,
    tomador: Cliente,
    descricao: str,
    email_destino: str,
) -> dict:
    """
    Envia a nota fiscal via SOAP e retorna o resultado.
    Lança exceção em caso de falha.
    """

    prestador_cpf_cnpj_fmt = formatar_cpf_cnpj(prestador.cnpj_cpf)
    tomador_cpf_cnpj_fmt = formatar_cpf_cnpj(tomador.cpf_cnpj)

    # Monta o corpo SOAP
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                     xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <eNFSe xmlns="http://tempuri.org/">
          <sAccessKey>{settings.NFSE_ACCESS_KEY}</sAccessKey>
          <sCN>{settings.NFSE_CN}</sCN>
          <sNome>{prestador.razao_social}</sNome>
          <sPrestador>{prestador_cpf_cnpj_fmt}</sPrestador>
          <sIM>{prestador.insc_municipal or ''}</sIM>
          <sTomador>{tomador_cpf_cnpj_fmt}</sTomador>
          <sValor>{nota.valor_total:.2f}</sValor>
          <sCodigoServico>{nota.codigo_lista_servico}</sCodigoServico>
          <sAliquota>{nota.aliquota:.2f}</sAliquota>
          <sValorDeducao>0</sValorDeducao>
          <sTributacaoRPS>0</sTributacaoRPS>
          <sDescricaoNFSe>{descricao}</sDescricaoNFSe>
          <sCofins>0</sCofins>
          <sPis>0</sPis>
          <sCsll>0</sCsll>
          <sIR>0</sIR>
          <sEmail>{email_destino}</sEmail>
        </eNFSe>
      </soap12:Body>
    </soap12:Envelope>"""

    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/eNFSe",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                settings.NFSE_URL, content=soap_body, headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise Exception(f"Falha na comunicação SOAP: {str(e)}")

    # Analisa a resposta XML
    try:
        root = ET.fromstring(response.text)
        # Ajuste o namespace conforme a resposta real da API
        namespace = {"ns": "http://tempuri.org/"}
        result = root.find(".//ns:eNFSeResult", namespace)
        if result is None or not result.text or "erro" in result.text.lower():
            raise Exception(
                f"Erro na emissão: {result.text if result is not None else 'Resposta inválida'}"
            )

        ultima_nota_solicitada_api: dict = await consultar_ultima_solicitacao_api_nfse(
            prestador_cpf_cnpj_fmt, nota.data_criacao
        )

        ultima_nota_id = ultima_nota_solicitada_api["nota_api"]["ID"]
        await insert_id_nota_api(db, nota.id, ultima_nota_id)

        return {"success": True, "response": result.text}

    except ET.ParseError:
        raise Exception("Resposta SOAP inválida (XML malformado)")


async def consultar_ultima_solicitacao_api_nfse(prestador_cnpj: str, data) -> dict:
    """
    Consulta as últimas solicitações de NFSe na API externa.
    Retorna a mais recente (ou todas, dependendo da lógica).
    """

    notas = await consultar_notas_por_periodo_api(prestador_cnpj, data, data)

    # ✅ Supõe que a API retorne em ordem cronológica (ou ID crescente)
    # Mas para garantir a mais recente, ordenamos por "Emissao" ou "ID"
    # Como "Emissao" está como string "dd/mm/yyyy", melhor usar "ID" (numérico)
    ultima = max(notas, key=lambda x: int(x["ID"]))

    return {
        "success": True,
        "nota_api": ultima,  # Dicionário com ID, Status, PDF, XML, etc.
        "todas": notas,
    }


async def consultar_notas_em_processamento_api_by_usuario(
    db: AsyncSession, usuario_id: str
):
    # 1. Busca todas as notas com status_id = 6 ("Em Processamento")
    result = await db.execute(
        select(NotaFiscal)
        .where(NotaFiscal.usuario_id == usuario_id)
        .where(NotaFiscal.status_id == 6)
        .options(
            selectinload(NotaFiscal.status),
            selectinload(NotaFiscal.usuario).selectinload(Usuario.atividades),
        )
    )
    notas = result.scalars().all()

    if not notas:
        # Adiciona desc_cnae mesmo se vazio (mantém compatibilidade com o frontend)
        return []

    # 2. Adiciona desc_cnae (mantém sua lógica original)
    usuario = notas[0].usuario
    if usuario and usuario.atividades:
        cnae_to_desc = {a.cod_cnae: a.desc_cnae for a in usuario.atividades}
        for nota in notas:
            nota.desc_cnae = cnae_to_desc.get(nota.cod_cnae)
    else:
        for nota in notas:
            nota.desc_cnae = None

    # 3. Extrai datas mínima e máxima (em formato dd/mm/yyyy para a API)
    datas = set()
    for nota in notas:
        if nota.data_criacao:
            datas.add(nota.data_criacao)

    if not datas:
        return notas  # não tem data, não pode consultar API

    data_inicio = min(datas)
    data_fim = max(datas)

    # 4. Consulta a API com o período
    try:
        resposta_api = await consultar_notas_por_periodo_api(
            formatar_cpf_cnpj(usuario.cnpj_cpf),
            data_inicio,
            data_fim,
        )
        # resposta_api já é a lista de dicts (não tem wrapper "todas")
        notas_api = resposta_api
    except Exception as e:
        print(f"Erro ao consultar API para sincronização: {e}")
        return notas  # retorna como está se falhar

    # 5. Cria mapa: ID da API → status
    mapa_notas_api = {}
    for item in notas_api:
        if "ID" in item:
            mapa_notas_api[str(item["ID"])] = {
                "Status": item.get("Status"),
                "eNFSe_PDF": item.get("eNFSe_PDF", "").strip(),
                "eNFSe_XML": item.get("eNFSe_XML", "").strip(),
                "Emissao": item.get("Emissao", "").strip(),
                "NFSe": item.get("NFSe", "").strip(),
            }

    # Atualiza as notas locais
    for nota in notas:
        if not nota.id_api:
            continue

        dados_api = mapa_notas_api.get(str(nota.id_api))
        if not dados_api:
            continue

        status_na_api = dados_api["Status"]
        if status_na_api == "EMITIDA":
            nota.status_id = 2
            nota.link_api_pdf = dados_api["eNFSe_PDF"]
            nota.link_api_xml = dados_api["eNFSe_XML"]
            nota.data_emissao = parse_ddmmyyyy(dados_api.get("Emissao")) 
            nota.numero_nota = dados_api["NFSe"]         
            await db.commit()
            await db.refresh(nota)

        return notas


async def consultar_notas_por_periodo_api(prestador_cnpj, data_inicio, data_fim):
    # Formato esperado pela API: dd/mm/yyyy
    data_inicio_str = datetime_utc_to_brasilia_date_str(data_inicio)
    data_fim_str = datetime_utc_to_brasilia_date_str(data_fim)

    # Monta o corpo SOAP para eNFSe_GetAll_DMS_E
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                     xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <eNFSe_GetAll_DMS_E xmlns="http://tempuri.org/">
          <sAccessKey>{settings.NFSE_ACCESS_KEY}</sAccessKey>
          <sCNPJ>{prestador_cnpj}</sCNPJ>
          <sDTStart>{data_inicio_str}</sDTStart>
          <sDTEnd>{data_fim_str}</sDTEnd>
        </eNFSe_GetAll_DMS_E>
      </soap12:Body>
    </soap12:Envelope>"""

    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                settings.NFSE_URL, content=soap_body, headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise Exception(f"Falha na consulta SOAP: {str(e)}")

    # Parse da resposta
    try:
        root = ET.fromstring(response.text)
        namespace = {"ns": "http://tempuri.org/"}
        result_elem = root.find(".//ns:eNFSe_GetAll_DMS_EResult", namespace)

        if result_elem is None or not result_elem.text:
            raise Exception("Resposta SOAP sem dados ou inválida.")

        # A API retorna um JSON dentro do XML!
        try:
            notas = json.loads(result_elem.text)
        except json.JSONDecodeError:
            raise Exception("Conteúdo da resposta não é JSON válido.")

        if not notas:
            raise Exception("Nenhuma solicitação encontrada para o período.")

        return notas

    except ET.ParseError:
        raise Exception("Resposta SOAP malformada.")


def formatar_cpf_cnpj(valor: str) -> str:
    """
    Formata um CPF ou CNPJ com máscara adequada.
    Assume que o valor recebido contém apenas dígitos numéricos.
    """
    valor = re.sub(r"\D", "", str(valor))  # Remove tudo que não for dígito

    if len(valor) == 11:
        # Formata como CPF: XXX.XXX.XXX-XX
        return f"{valor[:3]}.{valor[3:6]}.{valor[6:9]}-{valor[9:]}"
    elif len(valor) == 14:
        # Formata como CNPJ: XX.XXX.XXX/XXXX-XX
        return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"
    else:
        # Se não for CPF nem CNPJ válido, retorna como está (ou lança erro, se preferir)
        return valor


def datetime_utc_to_brasilia_date_str(dt_utc: datetime) -> str:
    """
    Converte um datetime UTC (timezone-aware) para a data civil em Brasília (BRT/BRST)
    e retorna no formato dd/mm/yyyy.
    """
    if dt_utc.tzinfo is None:
        # Se não tiver timezone, assume UTC (mas ideal é sempre armazenar com tz)
        dt_utc = dt_utc.replace(tzinfo=pytz.UTC)

    # Define o fuso horário de Brasília (lida com horário de verão automaticamente)
    brasilia_tz = pytz.timezone("America/Fortaleza")  # ou "America/Sao_Paulo"

    # Converte para o fuso local
    dt_brasilia = dt_utc.astimezone(brasilia_tz)

    # Extrai só a data (ignora hora) e formata
    return dt_brasilia.strftime("%d/%m/%Y")


def parse_ddmmyyyy(data_str: Optional[str]) -> Optional[date]:
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None