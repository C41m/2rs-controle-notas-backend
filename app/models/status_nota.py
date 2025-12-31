# app/models/status_nota.py
from sqlalchemy import Column, Integer, String
from app.database import Base

class StatusNota(Base):
    __tablename__ = "status_nota"
    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)