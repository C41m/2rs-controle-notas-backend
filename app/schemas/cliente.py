# schemas/cliente.py
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClienteBase(BaseModel):
    razao_social: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    # Endereço
    pais: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class Cliente(ClienteBase):
    id: int
    usuario_id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
