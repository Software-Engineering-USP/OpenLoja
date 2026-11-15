"""Dependências do FastAPI para autenticação/autorização."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import select

from .database import SessionDep
from .models import Cliente, Vendedor
from .security import ler_sessao

Usuario = Cliente | Vendedor


def _buscar_usuario(session: SessionDep, dados: dict) -> Usuario | None:
    if dados["tipo"] == "vendedor":
        modelo = Vendedor
    elif dados["tipo"] == "cliente":
        modelo = Cliente
    else:
        return None

    return session.exec(select(modelo).where(modelo.nome == dados["nome"])).first()


def get_active_type(session: Annotated[str | None, Cookie()] = None) -> str | None:
    """Tipo do usuário logado ("vendedor"/"cliente") ou None."""
    dados = ler_sessao(session)
    return dados["tipo"] if dados else None


def get_optional_user(
    db: SessionDep, session: Annotated[str | None, Cookie()] = None
) -> Usuario | None:
    """Usuário logado, se houver, sem exigir autenticação."""
    dados = ler_sessao(session)
    return _buscar_usuario(db, dados) if dados else None


def get_active_user(
    db: SessionDep, session: Annotated[str | None, Cookie()] = None
) -> Usuario:
    dados = ler_sessao(session)

    if not dados:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: você não está logado.",
        )

    if dados["tipo"] not in ("vendedor", "cliente"):
        raise HTTPException(401, "Tipo de usuário inválido.")

    user = _buscar_usuario(db, dados)
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    return user


def get_admin(user: Annotated[Usuario, Depends(get_active_user)]) -> Vendedor:
    if not isinstance(user, Vendedor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas vendedores podem acessar esta rota.",
        )
    return user


def get_cliente(user: Annotated[Usuario, Depends(get_active_user)]) -> Cliente:
    # Vendedor e Cliente ficam em tabelas diferentes e podem ter o mesmo
    # id: sem esta checagem um vendedor acabaria usando o carrinho (ou
    # assinando avaliações) do cliente de mesmo id.
    if not isinstance(user, Cliente):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes podem acessar esta rota.",
        )
    return user


OptionalUser = Annotated[Usuario | None, Depends(get_optional_user)]
ActiveUser = Annotated[Usuario, Depends(get_active_user)]
Admin = Annotated[Vendedor, Depends(get_admin)]
ClienteLogado = Annotated[Cliente, Depends(get_cliente)]
