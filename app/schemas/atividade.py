# schemas/atividade.py
import uuid
from pydantic import BaseModel, ConfigDict
from typing import Optional

# ✅ Base sem ID — para criação e atualização
class AtividadeCreate(BaseModel):
    cod_cnae: str
    desc_cnae: str
    
    model_config = ConfigDict(from_attributes=True)

# ✅ Resposta completa — com ID, para leitura
class Atividade(AtividadeCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)