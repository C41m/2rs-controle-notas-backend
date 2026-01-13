# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Cria a classe base para os modelos
Base = declarative_base()

# Cria engine assíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_cache_size": 0,  # Desativa o cache de statements preparados
        "statement_cache_size": 0,  # Garante que o asyncpg não cacheie nada
    },
)

# Cria sessionmaker assíncrono
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
