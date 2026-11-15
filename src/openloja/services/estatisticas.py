"""Cálculos dos painéis do vendedor (home e estatísticas)."""

from datetime import datetime

from sqlmodel import Session, col, select

from ..models import Avaliacao, Produto, Reserva, ReservaProdutoLink

MESES_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


def _mesmo_mes(data: datetime | None, referencia: datetime) -> bool:
    return data is not None and (data.year, data.month) == (
        referencia.year,
        referencia.month,
    )


def vendas_concluidas(session: Session) -> list[Reserva]:
    return list(
        session.exec(
            select(Reserva)
            .where(Reserva.concluida)
            .where(col(Reserva.data_conclusao).is_not(None))
        ).all()
    )


def resumo_home(session: Session, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now()

    produtos = session.exec(select(Produto)).all()
    vendas = vendas_concluidas(session)
    vendas_mes = [r for r in vendas if _mesmo_mes(r.data_conclusao, agora)]

    # "novos clientes" = clientes cuja primeira compra concluída foi neste
    # mês (vendas presenciais não têm cliente cadastrado e não contam)
    primeira_compra: dict[int, datetime] = {}
    for r in vendas:
        if r.cliente_id is None:
            continue
        atual = primeira_compra.get(r.cliente_id)
        if atual is None or r.data_conclusao < atual:
            primeira_compra[r.cliente_id] = r.data_conclusao

    return {
        "receita_mensal": sum(r.valor_final for r in vendas_mes),
        "vendas_mes": len(vendas_mes),
        "itens_em_estoque": sum(p.quantidade_em_estoque for p in produtos),
        "valor_em_estoque": sum(p.preco * p.quantidade_em_estoque for p in produtos),
        "novos_clientes": sum(
            1 for data in primeira_compra.values() if _mesmo_mes(data, agora)
        ),
    }


def receita_por_mes(session: Session) -> dict:
    agrupado: dict[tuple[int, int], float] = {}
    for r in vendas_concluidas(session):
        chave = (r.data_conclusao.year, r.data_conclusao.month)
        agrupado[chave] = agrupado.get(chave, 0.0) + r.valor_final

    chaves = sorted(agrupado)
    return {
        "labels": [f"{MESES_PT[mes]}/{ano}" for ano, mes in chaves],
        "valores": [round(agrupado[c], 2) for c in chaves],
    }


def painel_estatisticas(session: Session, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now()

    vendas_mes = [
        r for r in vendas_concluidas(session) if _mesmo_mes(r.data_conclusao, agora)
    ]

    estatisticas = {
        "vendas_mes": len(vendas_mes),
        "receita_mensal": sum(r.valor_final for r in vendas_mes),
        "nota_media": 0,
    }

    produtos = session.exec(select(Produto)).all()

    # só vendas efetivadas contam (reservas pendentes podem nunca ser pagas)
    vendas_por_produto: dict[int, int] = {}
    for link in session.exec(
        select(ReservaProdutoLink)
        .join(Reserva, col(Reserva.id) == ReservaProdutoLink.reserva_id)
        .where(Reserva.concluida)
    ).all():
        if link.produto_id is not None:
            vendas_por_produto[link.produto_id] = (
                vendas_por_produto.get(link.produto_id, 0) + link.quantidade
            )

    top_produtos = sorted(
        ({"nome": p.nome, "vendas": vendas_por_produto.get(p.id, 0)} for p in produtos),
        key=lambda item: item["vendas"],
        reverse=True,
    )[:5]

    produto_ids = [p.id for p in produtos]
    avaliacoes = (
        session.exec(
            select(Avaliacao).where(col(Avaliacao.produto_id).in_(produto_ids))
        ).all()
        if produto_ids
        else []
    )

    if avaliacoes:
        estatisticas["nota_media"] = round(
            sum(a.nota for a in avaliacoes) / len(avaliacoes), 1
        )

    avaliacoes_recentes = sorted(
        avaliacoes, key=lambda a: (a.ano, a.mes, a.dia, a.horario), reverse=True
    )[:5]

    return {
        "estatisticas": estatisticas,
        "top_produtos": top_produtos,
        "avaliacoes_recentes": avaliacoes_recentes,
    }
