# app/models/usuario.py
from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Credenciais (atenção ao email!)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Dados da empresa
    cnpj_cpf = Column(String, unique=True, nullable=False)
    razao_social = Column(String, nullable=False)
    aliquota = Column(Numeric(5, 2), nullable=True)
    emite = Column(Boolean, nullable=True, default=False)
    insc_municipal = Column(String, nullable=True)
    
    # Contato
    telefone = Column(String, nullable=True)

    # Endereço (todos nullable)
    pais = Column(String, nullable=True)
    uf = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    cep = Column(String, nullable=True)
    logradouro = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)

    # Relacionamentos
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos ORM
    clientes = relationship(
        "Cliente", back_populates="usuario", cascade="all, delete-orphan"
    )
    notas_fiscais = relationship(
        "NotaFiscal",  # ✅ Corrigido: nome da classe
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    role = relationship("Role", back_populates="usuario")
    atividades = relationship(
        "Atividade", back_populates="usuario", cascade="all, delete-orphan"
    )
