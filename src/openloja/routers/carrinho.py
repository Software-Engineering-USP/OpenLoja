"""Carrinho do cliente e checkout (transforma o carrinho em reserva)."""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from ..database import SessionDep
from ..dependencies import ClienteLogado
from ..models import Carrinho, CarrinhoProdutoLink, Produto, Reserva
from ..schemas import CarrinhoItem, ReservaItemInput
from ..services.reservas import definir_itens, verificar_estoque

router = APIRouter()

ITEM_NOT_FOUND = {404: {"description": "Carrinho ou item não encontrado"}}


def _get_or_create_carrinho(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(
        select(Carrinho).where(Carrinho.cliente_id == cliente_id)
    ).first()
    if not carrinho:
        carrinho = Carrinho(cliente_id=cliente_id)
        session.add(carrinho)
        session.commit()
        session.refresh(carrinho)
    return carrinho


def _get_carrinho_or_404(session: Session, cliente_id: int) -> Carrinho:
    carrinho = session.exec(
        select(Carrinho).where(Carrinho.cliente_id == cliente_id)
    ).first()
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    return carrinho


def _link(
    session: Session, carrinho_id: int, produto_id: int
) -> CarrinhoProdutoLink | None:
    return session.exec(
        select(CarrinhoProdutoLink).where(
            CarrinhoProdutoLink.carrinho_id == carrinho_id,
            CarrinhoProdutoLink.produto_id == produto_id,
        )
    ).first()


def _adicionar(session: Session, carrinho: Carrinho, produto_id: int, quantidade: int):
    link = _link(session, carrinho.id, produto_id)
    if link:
        link.quantidade += quantidade
    else:
        link = CarrinhoProdutoLink(
            carrinho_id=carrinho.id, produto_id=produto_id, quantidade=quantidade
        )
    session.add(link)


def _links(session: Session, carrinho_id: int):
    return session.exec(
        select(CarrinhoProdutoLink).where(
            CarrinhoProdutoLink.carrinho_id == carrinho_id
        )
    ).all()


@router.get("/carrinho")
def get_carrinho(user: ClienteLogado, session: SessionDep):
    carrinho = _get_or_create_carrinho(session, user.id)

    itens = session.exec(
        select(Produto, CarrinhoProdutoLink.quantidade)
        .join(CarrinhoProdutoLink, CarrinhoProdutoLink.produto_id == Produto.id)
        .where(CarrinhoProdutoLink.carrinho_id == carrinho.id)
    ).all()

    return {
        "id": carrinho.id,
        "cliente_id": user.id,
        "itens": [
            {
                "id": produto.id,
                "nome": produto.nome,
                "preco": produto.preco,
                "imagem": produto.imagem,
                "quantidade": quantidade,
            }
            for produto, quantidade in itens
        ],
        "total": sum(produto.preco * quantidade for produto, quantidade in itens),
    }


@router.post(
    "/carrinho/add", responses={404: {"description": "Produto não encontrado"}}
)
def add_produto(
    user: ClienteLogado, session: SessionDep, produto_id: int, quantidade: int = 1
):
    if quantidade < 1:
        raise HTTPException(400, "Quantidade inválida.")
    if session.get(Produto, produto_id) is None:
        raise HTTPException(404, "Produto não encontrado")

    carrinho = _get_or_create_carrinho(session, user.id)
    _adicionar(session, carrinho, produto_id, quantidade)
    session.commit()
    return {"msg": "produto adicionado", "carrinho_id": carrinho.id}


@router.patch("/carrinho/item", responses=ITEM_NOT_FOUND)
def update_item(
    produto_id: int, nova_quantidade: int, user: ClienteLogado, session: SessionDep
):
    carrinho = _get_carrinho_or_404(session, user.id)

    link = _link(session, carrinho.id, produto_id)
    if not link:
        raise HTTPException(status_code=404, detail="Item não está no carrinho")

    if nova_quantidade <= 0:
        session.delete(link)
    else:
        link.quantidade = nova_quantidade
        session.add(link)

    session.commit()
    return {"msg": "quantidade atualizada"}


@router.delete("/carrinho/item/{produto_id}", responses=ITEM_NOT_FOUND)
def remove_item(produto_id: int, user: ClienteLogado, session: SessionDep):
    carrinho = _get_carrinho_or_404(session, user.id)

    link = _link(session, carrinho.id, produto_id)
    if link:
        session.delete(link)
        session.commit()
    return {"msg": "item removido"}


# junta o carrinho guardado no navegador (antes do login) ao do banco
@router.post("/carrinho/sincronizar")
def sincronizar_carrinho(
    itens: list[CarrinhoItem], user: ClienteLogado, session: SessionDep
):
    carrinho = _get_or_create_carrinho(session, user.id)

    for item in itens:
        # ignora produtos que deixaram de existir enquanto estavam no navegador
        if session.get(Produto, item.produto_id) is not None:
            _adicionar(session, carrinho, item.produto_id, item.quantidade)

    session.commit()
    return {"ok": True}


@router.post(
    "/checkout",
    responses={400: {"description": "Carrinho vazio ou estoque insuficiente"}},
)
def checkout(user: ClienteLogado, session: SessionDep):
    carrinho = _get_or_create_carrinho(session, user.id)
    links = _links(session, carrinho.id)

    # itens de produtos que foram removidos da loja somem do carrinho
    validos = [link for link in links if session.get(Produto, link.produto_id)]

    if not validos:
        raise HTTPException(status_code=400, detail="O carrinho está vazio.")

    itens = verificar_estoque(
        session, ((link.produto_id, link.quantidade) for link in validos)
    )

    reserva = Reserva(cliente_id=user.id)
    definir_itens(
        session,
        reserva,
        [ReservaItemInput(produto_id=p.id, quantidade=q) for p, q in itens],
    )

    for link in links:
        session.delete(link)

    session.commit()
    return {
        "msg": "Compra finalizada com sucesso!",
        "reserva_id": reserva.id,
        "itens": [
            {"nome": produto.nome, "preco": produto.preco, "quantidade": quantidade}
            for produto, quantidade in itens
        ],
        "total": reserva.valor,
    }
