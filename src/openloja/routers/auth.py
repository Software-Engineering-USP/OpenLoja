"""Criação de conta, login e logout."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select

from ..database import SessionDep
from ..dependencies import get_active_type
from ..models import Cliente, Loja, Vendedor
from ..schemas import Usuario
from ..security import (
    criar_sessao,
    encerrar_sessao,
    hash_senha,
    senha_tem_hash,
    verificar_senha,
)
from ..templating import templates

router = APIRouter()


# rota inicial: criação da conta do vendedor (primeiro acesso) ou redireciona
@router.get("/")
def root(
    request: Request,
    session: SessionDep,
    tipo: str | None = Depends(get_active_type),
):
    if session.exec(select(Vendedor)).first() is None:
        return templates.TemplateResponse(
            request=request,
            name="createAccount.html",
            context={"primeiroVendedor": True},
        )

    if tipo == "vendedor":
        return RedirectResponse(url="/home", status_code=303)

    return RedirectResponse(url="/homeCliente", status_code=303)


@router.get("/paginalogin", response_class=HTMLResponse)
def paginalogin(request: Request, session: SessionDep):
    loja = session.exec(select(Loja)).first()
    return templates.TemplateResponse(
        request=request, name="login.html", context={"loja": loja}
    )


@router.get("/paginacria", response_class=HTMLResponse)
def paginacriar(request: Request, session: SessionDep):
    loja = session.exec(select(Loja)).first()
    return templates.TemplateResponse(
        request=request,
        name="createAccount.html",
        context={"primeiroVendedor": False, "loja": loja},
    )


# a primeira conta criada vira o vendedor; as demais são clientes
@router.post("/criarusuario", responses={404: {"description": "Usuário já existente"}})
def criar_usuario(user: Usuario, session: SessionDep):
    nome = user.nome.strip()
    if not nome or not user.senha:
        raise HTTPException(400, "Informe usuário e senha.")

    existe_vendedor = session.exec(select(Vendedor)).first() is not None

    if existe_vendedor:
        ja_existe = (
            session.exec(select(Vendedor).where(Vendedor.nome == nome)).first()
            or session.exec(select(Cliente).where(Cliente.nome == nome)).first()
        )
        if ja_existe:
            raise HTTPException(status_code=404, detail="Usuário já existente.")
        modelo = Cliente
    else:
        modelo = Vendedor

    usuario = modelo(nome=nome, senha=hash_senha(user.senha))
    session.add(usuario)
    session.commit()

    return {"usuario": usuario.nome}


@router.post(
    "/login",
    responses={404: {"description": "Usuário ou senha incorretos ou inexistente"}},
)
def logar(dados: Usuario, response: Response, session: SessionDep):
    nome = dados.nome.strip()

    for modelo, tipo in ((Vendedor, "vendedor"), (Cliente, "cliente")):
        usuario = session.exec(select(modelo).where(modelo.nome == nome)).first()
        if usuario is None:
            continue

        if not verificar_senha(dados.senha, usuario.senha):
            raise HTTPException(404, "Senha incorreta")

        # contas antigas guardavam a senha em texto puro: converte agora
        if not senha_tem_hash(usuario.senha):
            usuario.senha = hash_senha(dados.senha)
            session.add(usuario)
            session.commit()

        criar_sessao(response, usuario.nome, tipo)
        return {"message": "Logado", "tipo": tipo}

    raise HTTPException(404, "Usuário não encontrado")


@router.post("/logout")
def deslogar(response: Response):
    encerrar_sessao(response)
    return {"message": "Deslogado"}
