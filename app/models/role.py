# app/models/role.py
from sqlalchemy import Column, Integer, String
from app.database import Base
from sqlalchemy.orm import relationship

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)
    
    usuario = relationship("Usuario", back_populates="role")