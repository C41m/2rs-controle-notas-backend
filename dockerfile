# Usa Python 3.13 (compatível com seu ambiente)
FROM python:3.13-slim

# Evita cache de arquivos .pyc e bufferização
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Instala apenas o necessário (gcc para compilar extensões do asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Diretório da aplicação
WORKDIR /app

# Copia requirements primeiro (otimiza cache do build)
COPY requirements.txt .

# Instala dependências — só o que você precisa
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic-settings \
    sqlalchemy \
    asyncpg \
    python-dotenv \
    passlib[bcrypt] \
    python-jose[cryptography]

# Copia todo o código
COPY . .

# Comando para rodar — o Render sobrescreve a porta automaticamente
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]