# main.py
from fastapi import FastAPI
from app.api.v1 import auth, cliente_routes, nota_fiscal, usuarios, atividades, status
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Comunica - Backend",
    swagger_ui_parameters={"oauth2RedirectUrl": None},
)

origins = [
    "http://localhost:4200",  # Angular local
    "http://127.0.0.1:4200",  # Alternativo, dependendo de como roda o front
    "*",
]


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(nota_fiscal.router, prefix="/nota-fiscal", tags=["nota-fiscal"])
app.include_router(cliente_routes.router, prefix="/clientes", tags=["cliente"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
app.include_router(atividades.router, prefix="/atividades", tags=["atividades"])
app.include_router(status.router, prefix="/status", tags=["status"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Bem-vindo ao Comunica!"}
