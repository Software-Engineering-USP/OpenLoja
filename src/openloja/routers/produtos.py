"""Catálogo (vitrine), estoque, CRUD de produtos e avaliações."""

from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from ..database import SessionDep
from ..dependencies import Admin, ClienteLogado, OptionalUser
from ..models import (
    Avaliacao,
    CarrinhoProdutoLink,
    Cliente,
    Loja,
    Produto,
    Reserva,
    ReservaProdutoLink,
)
from ..schemas import AvaliacaoCreate
from ..services.reservas import recalcular_valor
from ..services.uploads import salvar_imagem
from ..templating import templates

router = APIRouter()

PRODUCT_NOT_FOUND = "Produto não encontrado"
NOT_FOUND = {404: {"description": PRODUCT_NOT_FOUND}}


def _produto_ou_404(session: Session, produto_id: int) -> Produto:
    produto = session.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(404, PRODUCT_NOT_FOUND)
    return produto


# ---------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------


# vitrine da loja (acessível sem login)
@router.get("/homeCliente")
def home_cliente(request: Request, user: OptionalUser, session: SessionDep):
    produtos = session.exec(select(Produto)).all()
    loja = session.exec(select(Loja)).first()

    tags = {
        tag.strip()
        for produto in produtos
        if produto.tag
        for tag in produto.tag.split(",")
        if tag.strip()
    }

    return templates.TemplateResponse(
        request=request,
        name="frontpage.html",
        context={
            "usuario": user,
            # só clientes têm carrinho no servidor; vendedores usam o local
            "usuario_cliente": isinstance(user, Cliente),
            "produtos": produtos,
            "tags": sorted(tags),
            "loja": loja,
        },
    )


@router.get("/stock")
def stock(request: Request, admin: Admin, session: SessionDep):
    produtos = session.exec(select(Produto)).all()
    return templates.TemplateResponse(
        request=request, name="stock.html", context={"produtos": produtos}
    )


@router.get("/product/{produto_id}", responses=NOT_FOUND)
def product(request: Request, produto_id: int, user: OptionalUser, session: SessionDep):
    produto = _produto_ou_404(session, produto_id)
    avaliacoes = session.exec(
        select(Avaliacao).where(Avaliacao.produto_id == produto_id)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="product.html",
        context={"produto": produto, "avaliacoes": avaliacoes},
    )


# ---------------------------------------------------------------------
# API de produtos
# ---------------------------------------------------------------------


@router.post("/produtos")
def criar_produto(produto: Produto, admin: Admin, session: SessionDep):
    produto.id = None
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


@router.get("/produtos")
def listar_produtos(session: SessionDep):
    return session.exec(select(Produto)).all()


@router.get("/produtos/{produto_id}", responses=NOT_FOUND)
def buscar_produto(produto_id: int, session: SessionDep):
    return _produto_ou_404(session, produto_id)


@router.put("/produtos/{produto_id}", responses=NOT_FOUND)
def atualizar_produto(
    produto_id: int, dados: Produto, admin: Admin, session: SessionDep
):
    produto = _produto_ou_404(session, produto_id)
    produto.sqlmodel_update(dados.model_dump(exclude_unset=True, exclude={"id"}))

    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


@router.post("/produtos/{produto_id}/imagem", responses=NOT_FOUND)
def enviar_imagem(
    produto_id: int,
    admin: Admin,
    session: SessionDep,
    imagem: UploadFile = File(...),
):
    produto = _produto_ou_404(session, produto_id)
    produto.imagem = salvar_imagem(imagem, str(produto_id))

    session.add(produto)
    session.commit()
    return {"ok": True}


@router.delete("/produtos/{produto_id}", responses=NOT_FOUND)
def deletar_produto(produto_id: int, admin: Admin, session: SessionDep):
    produto = _produto_ou_404(session, produto_id)

    # reservas pendentes com o produto perdem o item e precisam ter o
    # valor recalculado (as já concluídas mantêm o valor da venda)
    pendentes = session.exec(
        select(Reserva)
        .join(ReservaProdutoLink, ReservaProdutoLink.reserva_id == Reserva.id)
        .where(ReservaProdutoLink.produto_id == produto_id)
        .where(col(Reserva.concluida).is_(False))
    ).all()

    # o produto também sai dos carrinhos, senão o checkout falharia
    for link in session.exec(
        select(CarrinhoProdutoLink).where(CarrinhoProdutoLink.produto_id == produto_id)
    ).all():
        session.delete(link)

    session.delete(produto)
    session.flush()

    for reserva in pendentes:
        recalcular_valor(session, reserva)

    session.commit()
    return {"message": "Produto removido"}


# ---------------------------------------------------------------------
# Avaliações
# ---------------------------------------------------------------------


@router.get("/produtos/{produto_id}/avaliacoes")
def listar_avaliacoes(produto_id: int, session: SessionDep):
    avaliacoes = session.exec(
        select(Avaliacao)
        .where(Avaliacao.produto_id == produto_id)
        .options(selectinload(Avaliacao.cliente))
        .order_by(col(Avaliacao.id).desc())
    ).all()

    return [
        {
            "id": a.id,
            "nota": a.nota,
            "texto": a.texto,
            "dia": a.dia,
            "mes": a.mes,
            "ano": a.ano,
            "horario": a.horario,
            "cliente": a.cliente.nome if a.cliente else "Cliente",
        }
        for a in avaliacoes
    ]


@router.post(
    "/produtos/{produto_id}/avaliacoes",
    responses={**NOT_FOUND, 400: {"description": "A nota deve estar entre 0 e 5."}},
)
def criar_avaliacao(
    produto_id: int, dados: AvaliacaoCreate, user: ClienteLogado, session: SessionDep
):
    _produto_ou_404(session, produto_id)

    if not 0 <= dados.nota <= 5:
        raise HTTPException(status_code=400, detail="A nota deve estar entre 0 e 5.")

    agora = datetime.now()
    avaliacao = Avaliacao(
        cliente_id=user.id,
        produto_id=produto_id,
        nota=dados.nota,
        texto=dados.texto,
        dia=agora.day,
        mes=agora.month,
        ano=agora.year,
        horario=agora.hour * 100 + agora.minute,
    )

    session.add(avaliacao)
    session.commit()
    session.refresh(avaliacao)
    return avaliacao
