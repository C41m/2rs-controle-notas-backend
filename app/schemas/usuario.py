# schemas/usuario.py
import re
import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator
from pydantic import ConfigDict
from .atividade import Atividade, AtividadeCreate


class ResetPasswordRequest(BaseModel):
    user_id: uuid.UUID


class UserBase(BaseModel):
    email: EmailStr
    razao_social: str
    cnpj_cpf: str
    role_id: int
    aliquota: float | None = None

    # Contato
    telefone: str | None = None

    # Endereço
    pais: str | None = None
    uf: str | None = None
    cidade: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None

    # Novos campos
    emite: bool | None = None
    insc_municipal: str | None = None

    atividades: List[AtividadeCreate] = []

class UserCreate(UserBase):
    password: str

    @field_validator("cnpj_cpf")
    @classmethod
    def clean_cnpj_cpf(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) not in (11, 14):
            raise ValueError("CPF ou CNPJ inválido")
        return cleaned


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    razao_social: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    role_id: Optional[int] = None
    aliquota: Optional[float] = None
    telefone: Optional[str] = None
    pais: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None

    # Novos campos opcionais
    emite: Optional[bool] = None
    insc_municipal: Optional[str] = None

    atividades: Optional[List[AtividadeCreate]] = None

    @field_validator("cnpj_cpf")
    @classmethod
    def clean_cnpj_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) not in (11, 14):
            raise ValueError("CPF ou CNPJ inválido")
        return cleaned


class User(UserBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)