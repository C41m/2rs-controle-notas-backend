# app/models/cliente.py
from sqlalchemy import Column, BigInteger, String, UUID, ForeignKey, DateTime, Numeric, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    
    razao_social = Column(String, nullable=False)
    cpf_cnpj = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)

    # Endereço
    pais = Column(String)
    uf = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    cep = Column(String, nullable=True)
    logradouro = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="clientes")
    notas_fiscais = relationship("NotaFiscal", back_populates="cliente")
