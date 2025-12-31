# Usar a mesma versão do Python que você usa localmente
FROM python:3.13-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar apenas arquivos de dependência primeiro (cache otimizado)
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Expor a porta usada pelo Render
EXPOSE 8000

# Aqui estou supondo que é FastAPI com Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
