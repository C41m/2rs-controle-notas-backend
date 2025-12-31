# app/schemas/nota_fiscal.py
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid
from app.schemas.cliente import ClienteBase
from app.schemas.usuario import UserBase
from app.schemas.atividade import Atividade


class NotaFiscal(BaseModel):
    id: int
    usuario_id: uuid.UUID  # UUID como string
    cliente_id: Optional[int] = None
    cod_cnae: Optional[str] = None
    numero_nota: Optional[str] = None
    data_emissao: Optional[date] = None
    valor_total: float
    descricao: Optional[str] = None
    status_id: int
    data_criacao: datetime
    data_atualizacao: datetime
    aliquota: Optional[float] = None
    desc_cnae: Optional[str] = None
    desc_motivo: Optional[str] = None
    codigo_lista_servico: Optional[str] = None


class NotaFiscalCreate(BaseModel):
    cpf_cnpj: str
    razao_social: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    pais: str
    uf: str
    cidade: str
    cep: str
    logradouro: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cod_cnae: str
    valor_total: float
    descricao: Optional[str] = None
    cliente_id: Optional[int] = None
    desc_motivo: Optional[str] = None
    codigo_lista_servico: Optional[str] = None

class NotaFiscalComCliente(NotaFiscal):
    cliente: ClienteBase


class NotaFiscalComClienteEUsuario(NotaFiscal):
    cliente: Optional[ClienteBase] = None
    usuario: Optional[UserBase] = None  # 👈 inclui dados do usuário


class AtualizarStatusNotaPayload(BaseModel):
    status_id: int

class AtualizarStutasNotaAceitePayload(BaseModel):
    nota_id: int

class AtualizarStatusMotivoNotaPayload(BaseModel):
    nota_id: int
    status_id: int
    desc_motivo: str

    class Config:
        from_attributes = True
