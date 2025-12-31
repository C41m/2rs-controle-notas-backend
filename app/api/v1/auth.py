# app/api/v1/auth.py

import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user_by_documento,
    get_current_user,
)
from app.schemas.usuario import UserCreate, User, UserLogin, UserUpdate
from app.crud.usuario import (
    create_user,
    get_user_by_email,
    update_user,
    delete_user,
    get_user_by_id,
)
import uuid
from pydantic import BaseModel
from app.schemas.usuario import ResetPasswordRequest

router = APIRouter()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=dict)
async def login(login: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, login.username, login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": user.cnpj_cpf,
            "role_id": user.role_id,
            "razao_social": user.razao_social,
            "emite": bool(user.emite)
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role_id": user.role_id,
        "razao_social": user.razao_social,
    }


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Verifica se o e-mail já existe
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado"
        )

    # 2. Verifica se o CNPJ/CPF já existe
    existing_documento = await get_user_by_documento(db, user_in.cnpj_cpf)
    if existing_documento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CNPJ ou CPF já cadastrado"
        )

    # 3. Hasheia a senha
    hashed_password = get_password_hash(user_in.cnpj_cpf)

    # 4. Cria o usuário com todos os dados
    user = await create_user(
        db=db,
        email=user_in.email,
        hashed_password=hashed_password,
        cnpj_cpf=user_in.cnpj_cpf,
        razao_social=user_in.razao_social,
        role_id=user_in.role_id,
        aliquota=user_in.aliquota,
        telefone=user_in.telefone,
        pais=user_in.pais,
        uf=user_in.uf,
        cidade=user_in.cidade,
        cep=user_in.cep,
        logradouro=user_in.logradouro,
        numero=user_in.numero,
        complemento=user_in.complemento,
        bairro=user_in.bairro,
        atividades=[
            atv.model_dump() for atv in user_in.atividades
        ],
        insc_municipal=user_in.insc_municipal,
        emite=user_in.emite,
    )
    return user


@router.put("/{user_id}", response_model=User)
async def update_user_by_id(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permite que um administrador (role_id == 1) atualize qualquer usuário.
    """
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem editar outros usuários.",
        )
    updated_user = await update_user(
        db=db,
        user_id=user_id,
        user_update=user_update,
        current_user_id=current_user.id,
        is_admin=True,
    )
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem excluir usuários.",
        )

    return await delete_user(db, user_id, current_user.id)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Buscar usuário completo com o hash da senha
    db_user = await get_user_by_documento(db, current_user.cnpj_cpf)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    # 2. Verificar senha atual
    from app.core.security import verify_password, get_password_hash

    if not verify_password(request.current_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta."
        )

    # 3. Evitar reutilização da mesma senha
    if verify_password(request.new_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha não pode ser igual à senha atual.",
        )

    # 4. Gerar novo hash (com truncamento de 72 bytes, já feito em get_password_hash)
    new_hashed_password = get_password_hash(request.new_password)

    # 5. Atualizar no banco
    db_user.hashed_password = new_hashed_password
    db.add(db_user)
    await db.commit()

    return {"message": "Senha alterada com sucesso!"}


@router.post("/redefinir-senha", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # 1. Verificar se o usuário atual é admin
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem redefinir senhas de outros usuários.",
        )

    # 2. Buscar o usuário-alvo pelo ID
    target_user = await get_user_by_id(db, request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # 3. Remover máscara do CNPJ/CPF do usuário-alvo
    clean_documento = re.sub(r"\D", "", target_user.cnpj_cpf)

    # 4. Gerar hash da nova senha (CPF/CNPJ sem máscara)
    new_hashed_password = get_password_hash(clean_documento)

    # 5. Atualizar no banco
    target_user.hashed_password = new_hashed_password
    db.add(target_user)
    await db.commit()

    return {
        "message": "Senha redefinida com sucesso! A nova senha é o CPF/CNPJ sem máscara."
    }



@router.get("/perfil", response_model=User)
async def get_current_user_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    
    return current_user