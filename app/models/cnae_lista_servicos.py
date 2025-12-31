# app/models/cnae_lista_servicos.py

from sqlalchemy import Column, Integer, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class CnaeListaAtividades(Base):
    __tablename__ = "cnae_lista_servicos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cnae_numerico = Column(String, nullable=False)
    cnae_descricao = Column(String, nullable=False)
    codigo_lista_servico = Column(String, nullable=False)
    lista_servico_descricao = Column(String, nullable=False)
