# app/models/nota_fiscal.py
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    UUID,
    ForeignKey,
    Date,
    Numeric,
    Integer,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    cliente_id = Column(
        BigInteger, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )

    numero_nota = Column(String, nullable=True)
    data_emissao = Column(Date, nullable=True)
    valor_total = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String, nullable=True)
    status_id = Column(Integer, ForeignKey("status_nota.id"), nullable=False, default=1)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cod_cnae = Column(String, nullable=True)
    aliquota = Column(Numeric(5, 2), nullable=True)
    desc_motivo = Column(String, nullable=True)
    codigo_lista_servico = Column(String, nullable=True)
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="notas_fiscais")
    cliente = relationship("Cliente", back_populates="notas_fiscais", lazy="selectin")
    status = relationship("StatusNota")
