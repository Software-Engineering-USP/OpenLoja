"""Cálculos dos painéis do vendedor (home e estatísticas)."""

import calendar
from datetime import date, datetime, timedelta

from sqlmodel import Session, col, select

from ..models import Avaliacao, Cliente, Produto, Reserva, ReservaProdutoLink

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
    vendas_hoje = [r for r in vendas_mes if r.data_conclusao.date() == agora.date()]

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
        "receita_hoje": sum(r.valor_final for r in vendas_hoje),
        "vendas_hoje": len(vendas_hoje),
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


# ---------------------------------------------------------------------
# Visualizações detalhadas (mês, dia, padrões de venda)
# ---------------------------------------------------------------------

DIAS_SEMANA_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _chave_mes(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def _proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def _itens_por_venda(session: Session, vendas: list[Reserva]) -> dict[int, list[dict]]:
    """Itens (nome e quantidade) de cada venda, numa única consulta."""
    ids = [r.id for r in vendas]
    if not ids:
        return {}

    itens: dict[int, list[dict]] = {}
    for link, nome in session.exec(
        select(ReservaProdutoLink, Produto.nome)
        .join(Produto, col(Produto.id) == ReservaProdutoLink.produto_id)
        .where(col(ReservaProdutoLink.reserva_id).in_(ids))
    ).all():
        itens.setdefault(link.reserva_id, []).append(
            {"nome": nome, "quantidade": link.quantidade}
        )
    return itens


def _resumo(vendas: list[Reserva], itens: dict[int, list[dict]]) -> dict:
    receita = sum(r.valor_final for r in vendas)
    online = [r for r in vendas if not r.presencial]
    presencial = [r for r in vendas if r.presencial]
    return {
        "receita": round(receita, 2),
        "vendas": len(vendas),
        "ticket_medio": round(receita / len(vendas), 2) if vendas else 0,
        "itens": sum(i["quantidade"] for r in vendas for i in itens.get(r.id, [])),
        "clientes": len({r.cliente_id for r in online}),
        "online": {
            "vendas": len(online),
            "receita": round(sum(r.valor_final for r in online), 2),
        },
        "presencial": {
            "vendas": len(presencial),
            "receita": round(sum(r.valor_final for r in presencial), 2),
        },
    }


def resumo_meses(session: Session, agora: datetime | None = None) -> list[dict]:
    """Um item por mês, do primeiro mês com venda até o mês atual (sem lacunas)."""
    agora = agora or datetime.now()
    vendas = vendas_concluidas(session)

    agrupado: dict[tuple[int, int], list[Reserva]] = {}
    for r in vendas:
        chave = (r.data_conclusao.year, r.data_conclusao.month)
        agrupado.setdefault(chave, []).append(r)

    atual = (agora.year, agora.month)
    inicio = min([*agrupado, atual])
    fim = max([*agrupado, atual])

    meses = []
    ano, mes = inicio
    while (ano, mes) <= fim:
        do_mes = agrupado.get((ano, mes), [])
        receita = sum(r.valor_final for r in do_mes)
        meses.append(
            {
                "chave": _chave_mes(ano, mes),
                "label": f"{MESES_PT[mes]}/{ano}",
                "receita": round(receita, 2),
                "vendas": len(do_mes),
                "ticket_medio": round(receita / len(do_mes), 2) if do_mes else 0,
            }
        )
        ano, mes = _proximo_mes(ano, mes)
    return meses


def detalhe_mes(
    session: Session, ano: int, mes: int, agora: datetime | None = None
) -> dict:
    agora = agora or datetime.now()
    vendas = vendas_concluidas(session)
    do_mes = [
        r
        for r in vendas
        if (r.data_conclusao.year, r.data_conclusao.month) == (ano, mes)
    ]
    anterior = _mes_anterior(ano, mes)
    label_anterior = f"{MESES_PT[anterior[1]]}/{anterior[0]}"
    do_anterior = [
        r for r in vendas if (r.data_conclusao.year, r.data_conclusao.month) == anterior
    ]
    # mês em andamento: compara com o mesmo intervalo de dias do mês anterior,
    # senão meio mês sempre pareceria uma queda
    parcial = (ano, mes) == (agora.year, agora.month)
    if parcial:
        do_anterior = [r for r in do_anterior if r.data_conclusao.day <= agora.day]
        label_anterior = f"1–{agora.day} {label_anterior}"
    itens = _itens_por_venda(session, do_mes + do_anterior)

    total_dias = calendar.monthrange(ano, mes)[1]
    receita_dia = [0.0] * total_dias
    vendas_dia = [0] * total_dias
    for r in do_mes:
        receita_dia[r.data_conclusao.day - 1] += r.valor_final
        vendas_dia[r.data_conclusao.day - 1] += 1

    por_produto: dict[str, int] = {}
    for r in do_mes:
        for item in itens.get(r.id, []):
            por_produto[item["nome"]] = (
                por_produto.get(item["nome"], 0) + item["quantidade"]
            )
    top_produtos = sorted(por_produto.items(), key=lambda p: p[1], reverse=True)[:5]

    melhor_dia = None
    if do_mes:
        indice = max(range(total_dias), key=lambda i: receita_dia[i])
        melhor_dia = {"dia": indice + 1, "receita": round(receita_dia[indice], 2)}

    return {
        "chave": _chave_mes(ano, mes),
        "label": f"{MESES_PT[mes]}/{ano}",
        "resumo": _resumo(do_mes, itens),
        "parcial": parcial,
        "anterior": {"label": label_anterior, **_resumo(do_anterior, itens)},
        "dias": {
            "labels": list(range(1, total_dias + 1)),
            "receita": [round(v, 2) for v in receita_dia],
            "vendas": vendas_dia,
        },
        "melhor_dia": melhor_dia,
        "top_produtos": [{"nome": n, "quantidade": q} for n, q in top_produtos],
    }


def vendas_do_dia(session: Session, dia: date) -> dict:
    do_dia = sorted(
        (r for r in vendas_concluidas(session) if r.data_conclusao.date() == dia),
        key=lambda r: r.data_conclusao,
    )
    itens = _itens_por_venda(session, do_dia)

    nomes_clientes = {}
    ids_clientes = {r.cliente_id for r in do_dia if r.cliente_id is not None}
    if ids_clientes:
        nomes_clientes = dict(
            session.exec(
                select(Cliente.id, Cliente.nome).where(
                    col(Cliente.id).in_(ids_clientes)
                )
            ).all()
        )

    return {
        "data": dia.isoformat(),
        "resumo": _resumo(do_dia, itens),
        "vendas": [
            {
                "id": r.id,
                "hora": r.data_conclusao.strftime("%H:%M"),
                "comprador": (
                    (r.nome_comprador or "Venda presencial")
                    if r.presencial
                    else nomes_clientes.get(r.cliente_id, "Cliente removido")
                ),
                "presencial": r.presencial,
                "valor": round(r.valor_final, 2),
                "itens": itens.get(r.id, []),
            }
            for r in do_dia
        ],
    }


def padroes_de_venda(session: Session, ultimos_dias: int | None = None) -> dict:
    """Distribuição das vendas por dia da semana e por hora do dia."""
    vendas = vendas_concluidas(session)
    if ultimos_dias:
        limite = datetime.now() - timedelta(days=ultimos_dias)
        vendas = [r for r in vendas if r.data_conclusao >= limite]

    semana_receita = [0.0] * 7
    semana_vendas = [0] * 7
    hora_receita = [0.0] * 24
    hora_vendas = [0] * 24
    for r in vendas:
        dia_semana = r.data_conclusao.weekday()
        hora = r.data_conclusao.hour
        semana_receita[dia_semana] += r.valor_final
        semana_vendas[dia_semana] += 1
        hora_receita[hora] += r.valor_final
        hora_vendas[hora] += 1

    return {
        "dias_semana": {
            "labels": DIAS_SEMANA_PT,
            "receita": [round(v, 2) for v in semana_receita],
            "vendas": semana_vendas,
        },
        "horas": {
            "labels": [f"{h:02d}h" for h in range(24)],
            "receita": [round(v, 2) for v in hora_receita],
            "vendas": hora_vendas,
        },
    }
