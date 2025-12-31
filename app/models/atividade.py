# app/models/atividade.py
from sqlalchemy import Column, Integer, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class Atividade(Base):
    __tablename__ = "atividades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)  # ✅ FK explícita
    cod_cnae = Column(String, nullable=False)
    desc_cnae = Column(String, nullable=False)

    # Relacionamento opcional (útil para queries reversas)
    usuario = relationship("Usuario", back_populates="atividades")