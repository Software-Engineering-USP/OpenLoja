"""Regras de negócio de reservas/vendas, compartilhadas pelas rotas."""

import json
from collections.abc import Iterable, Sequence
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from ..models import Cliente, Produto, Reserva, ReservaProdutoLink
from ..schemas import ReservaItemInput

RESERVE_NOT_FOUND = "Reserva não encontrada"
CLIENT_NOT_FOUND = "Cliente não encontrado"


def agrupar_itens(itens: Iterable[ReservaItemInput]) -> dict[int, int]:
    """{produto_id: quantidade}, somando produtos repetidos na lista."""
    quantidades: dict[int, int] = {}
    for item in itens:
        quantidades[item.produto_id] = (
            quantidades.get(item.produto_id, 0) + item.quantidade
        )
    return quantidades


def carregar_produtos(
    session: Session, produto_ids: Iterable[int]
) -> dict[int, Produto]:
    """Busca os produtos pedidos; 404 se algum não existir."""
    ids = set(produto_ids)
    produtos = session.exec(select(Produto).where(col(Produto.id).in_(ids))).all()
    por_id = {p.id: p for p in produtos}

    faltando = ids - por_id.keys()
    if faltando:
        raise HTTPException(404, f"Produto(s) não encontrado(s): {sorted(faltando)}")

    return por_id


def definir_itens(
    session: Session, reserva: Reserva, itens: Sequence[ReservaItemInput]
) -> None:
    """Substitui os itens da reserva, recalcula o valor e reserva o estoque.

    Os itens antigos (se já tinham saído do estoque) são devolvidos antes
    de conferir os novos, então editar uma reserva não "concorre" com ela
    mesma. Falta de estoque gera 400 e nada deve ser salvo.
    """
    if not itens:
        raise HTTPException(400, "A reserva precisa ter ao menos um produto.")

    quantidades = agrupar_itens(itens)
    produtos = carregar_produtos(session, quantidades)

    if reserva.id is None:
        session.add(reserva)
        session.flush()
    else:
        devolver_estoque(session, reserva)
        for link in links_da_reserva(session, reserva.id):
            session.delete(link)
        session.flush()

    # só baixa o estoque depois de conferir todos os itens
    for produto_id, quantidade in quantidades.items():
        _conferir_estoque(produtos[produto_id], quantidade)

    for produto_id, quantidade in quantidades.items():
        produtos[produto_id].quantidade_em_estoque -= quantidade
        session.add(produtos[produto_id])
        session.add(
            ReservaProdutoLink(
                reserva_id=reserva.id, produto_id=produto_id, quantidade=quantidade
            )
        )

    reserva.estoque_baixado = True
    reserva.valor = float(
        sum(produtos[pid].preco * qtd for pid, qtd in quantidades.items())
    )


def devolver_estoque(session: Session, reserva: Reserva) -> None:
    """Devolve ao estoque os itens da reserva, se já tinham saído dele."""
    if not reserva.estoque_baixado:
        return

    for link in links_da_reserva(session, reserva.id):
        produto = session.get(Produto, link.produto_id)
        if produto:
            produto.quantidade_em_estoque += link.quantidade
            session.add(produto)

    reserva.estoque_baixado = False
    session.add(reserva)


def recalcular_valor(session: Session, reserva: Reserva) -> None:
    """Recalcula o valor a partir dos itens que ainda existem."""
    reserva.valor = float(
        sum(
            produto.preco * link.quantidade
            for link, produto in session.exec(
                select(ReservaProdutoLink, Produto)
                .join(Produto, col(Produto.id) == ReservaProdutoLink.produto_id)
                .where(ReservaProdutoLink.reserva_id == reserva.id)
            ).all()
        )
    )
    session.add(reserva)


def links_da_reserva(session: Session, reserva_id: int) -> Sequence[ReservaProdutoLink]:
    return session.exec(
        select(ReservaProdutoLink).where(ReservaProdutoLink.reserva_id == reserva_id)
    ).all()


def buscar_reserva(session: Session, reserva_id: int) -> Reserva:
    reserva = session.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(404, RESERVE_NOT_FOUND)
    return reserva


def buscar_cliente(session: Session, cliente_id: int) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(404, CLIENT_NOT_FOUND)
    return cliente


def definir_comprador(
    session: Session,
    reserva: Reserva,
    cliente_id: int | None,
    nome_comprador: str | None,
    obrigatorio: bool = False,
) -> None:
    """Associa a reserva a um cliente cadastrado ou a um comprador presencial.

    Um nome em branco é tratado como ausente, para que formulários que
    sempre enviam os dois campos funcionem ao escolher um cliente.
    """
    nome = (nome_comprador or "").strip() or None

    if cliente_id is not None and nome is not None:
        raise HTTPException(
            400, "Informe um cliente cadastrado ou o nome do comprador, não ambos."
        )

    if cliente_id is not None:
        reserva.cliente_id = buscar_cliente(session, cliente_id).id
        reserva.nome_comprador = None
    elif nome is not None:
        reserva.cliente_id = None
        reserva.nome_comprador = nome
    elif nome_comprador is not None:
        raise HTTPException(400, "Informe o nome do comprador.")
    elif obrigatorio:
        raise HTTPException(
            400,
            "Informe o cliente para quem a reserva será criada "
            "ou o nome do comprador (venda presencial).",
        )


def _conferir_estoque(produto: Produto, quantidade: int) -> None:
    if produto.quantidade_em_estoque < quantidade:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para '{produto.nome}'. "
                f"Disponível: {produto.quantidade_em_estoque}, "
                f"Solicitado: {quantidade}"
            ),
        )


def verificar_estoque(
    session: Session, quantidades: Iterable[tuple[int, int]]
) -> list[tuple[Produto, int]]:
    """Garante que há estoque para cada (produto_id, quantidade)."""
    resultado = []
    for produto_id, quantidade in quantidades:
        produto = session.get(Produto, produto_id)
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto com ID {produto_id} não encontrado.",
            )
        _conferir_estoque(produto, quantidade)
        resultado.append((produto, quantidade))
    return resultado


def validar_valor_efetivo(valor: float | None) -> None:
    if valor is not None and valor < 0:
        raise HTTPException(400, "Valor efetivo não pode ser negativo")


def efetivar(session: Session, reserva: Reserva, valor_efetivo: float | None) -> None:
    """Conclui a venda e registra valor e data.

    O estoque normalmente já foi baixado quando a reserva foi criada; só
    reservas pendentes de versões anteriores descontam aqui.
    """
    if reserva.concluida:
        raise HTTPException(400, "Reserva já está concluída")

    validar_valor_efetivo(valor_efetivo)

    if not reserva.estoque_baixado:
        links = links_da_reserva(session, reserva.id)
        itens = verificar_estoque(
            session, ((link.produto_id, link.quantidade) for link in links)
        )

        # só reduz o estoque depois de validar todos os itens
        for produto, quantidade in itens:
            produto.quantidade_em_estoque -= quantidade
            session.add(produto)
        reserva.estoque_baixado = True

    reserva.concluida = True
    reserva.valor_efetivo = (
        valor_efetivo if valor_efetivo is not None else reserva.valor
    )
    reserva.data_conclusao = datetime.now()
    session.add(reserva)


def remover(session: Session, reserva: Reserva) -> None:
    """Remove a reserva (pendente ou efetivada), devolvendo os itens ao estoque."""
    devolver_estoque(session, reserva)

    for link in links_da_reserva(session, reserva.id):
        session.delete(link)
    session.flush()

    session.delete(reserva)


# ---------------------------------------------------------------------
# Visões para os templates
# ---------------------------------------------------------------------


def itens_por_reserva(
    session: Session, reserva_ids: Iterable[int]
) -> dict[int, list[dict]]:
    """Itens de cada reserva (ignora produtos que já foram removidos)."""
    ids = list(reserva_ids)
    if not ids:
        return {}

    linhas = session.exec(
        select(ReservaProdutoLink, Produto)
        .join(Produto, col(Produto.id) == ReservaProdutoLink.produto_id)
        .where(col(ReservaProdutoLink.reserva_id).in_(ids))
    ).all()

    resultado: dict[int, list[dict]] = {}
    for link, produto in linhas:
        resultado.setdefault(link.reserva_id, []).append(
            {
                "produto_id": produto.id,
                "nome": produto.nome,
                "quantidade": link.quantidade,
                "preco": produto.preco,
            }
        )
    return resultado


def nome_do_comprador(reserva: Reserva) -> str:
    if reserva.cliente is not None:
        return reserva.cliente.nome
    if reserva.nome_comprador:
        return reserva.nome_comprador
    return "—"  # cliente removido


def visao_reserva(reserva: Reserva, itens: list[dict]) -> dict:
    return {
        "id": reserva.id,
        "cliente_id": reserva.cliente_id,
        "cliente_nome": nome_do_comprador(reserva),
        "nome_comprador": reserva.nome_comprador,
        "presencial": reserva.presencial,
        "valor": reserva.valor,
        "concluida": reserva.concluida,
        "valor_efetivo": reserva.valor_efetivo,
        "valor_final": reserva.valor_final,
        "data_conclusao": reserva.data_conclusao,
        "itens": itens,
        "itens_json": json.dumps(itens),
    }


def listar_visoes(session: Session, cliente_id: int | None = None) -> list[dict]:
    """Reservas (mais recentes primeiro) prontas para os templates."""
    consulta = select(Reserva).options(selectinload(Reserva.cliente))
    if cliente_id is not None:
        consulta = consulta.where(Reserva.cliente_id == cliente_id)

    reservas = session.exec(consulta.order_by(col(Reserva.id).desc())).all()
    itens = itens_por_reserva(session, (r.id for r in reservas))

    return [visao_reserva(r, itens.get(r.id, [])) for r in reservas]


def historico_cliente(session: Session, cliente_id: int) -> dict:
    """Pedidos e resumo de um cliente (página "Minha Conta" e perfil)."""
    reservas = listar_visoes(session, cliente_id)

    return {
        "reservas": reservas,
        "total_pedidos": len(reservas),
        "total_pendentes": sum(1 for r in reservas if not r["concluida"]),
        "total_gasto": sum(r["valor_final"] for r in reservas if r["concluida"]),
    }
