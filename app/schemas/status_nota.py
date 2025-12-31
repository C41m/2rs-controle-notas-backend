# app/schemas/status_nota.py
from pydantic import BaseModel

class StatusNotaBase(BaseModel):
    id: int
    nome: str

class StatusNota(StatusNotaBase):
    class Config:
        from_attributes = True