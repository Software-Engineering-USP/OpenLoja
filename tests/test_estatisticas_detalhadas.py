"""Visualizações detalhadas da página de estatísticas (/estatisticas/*)."""

from datetime import datetime

import pytest

from openloja.models import Reserva

from helpers import (
    criar_produto,
    criar_usuario,
    id_do_cliente,
    login,
    sessao_db,
    vendedor_logado,
)


def venda_concluida(client, produto_id, quando, quantidade=1, cliente_id=None):
    corpo = {"itens": [{"produto_id": produto_id, "quantidade": quantidade}]}
    if cliente_id is None:
        corpo["nome_comprador"] = "Maria Silva"
    else:
        corpo["cliente_id"] = cliente_id
    reserva_id = client.post("/reservas", json=corpo).json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    with sessao_db() as session:
        reserva = session.get(Reserva, reserva_id)
        reserva.data_conclusao = quando
        session.add(reserva)
        session.commit()
    return reserva_id


@pytest.fixture
def cenario(client):
    """Vendedor logado, um cliente e um produto de R$ 10 com estoque."""
    vendedor_logado(client)
    produto_id = criar_produto(client, nome="Caneca", preco=10, estoque=100)
    criar_usuario(client, "joao")
    return client, produto_id, id_do_cliente(client, "joao")


@pytest.mark.parametrize(
    "url",
    [
        "/estatisticas/meses",
        "/estatisticas/mes/2026/1",
        "/estatisticas/dia/2026-01-15",
        "/estatisticas/padroes",
    ],
)
def test_rotas_exigem_vendedor(client, url):
    assert client.get(url).status_code == 401

    criar_usuario(client, "dono")
    criar_usuario(client, "joao")
    login(client, "joao")
    assert client.get(url).status_code == 403


def test_meses_preenche_lacunas_ate_o_mes_atual(cenario):
    client, produto_id, _ = cenario
    agora = datetime.now()
    venda_concluida(client, produto_id, datetime(agora.year - 1, 11, 5), quantidade=2)

    meses = client.get("/estatisticas/meses").json()

    assert meses[0]["chave"] == f"{agora.year - 1}-11"
    assert meses[0]["receita"] == 20
    assert meses[0]["vendas"] == 1
    assert meses[0]["ticket_medio"] == 20
    assert meses[-1]["chave"] == f"{agora.year}-{agora.month:02d}"
    # nenhum mês pulado
    assert len(meses) == 12 * 1 + agora.month - 11 + 1
    assert all(m["vendas"] == 0 for m in meses[1:])


def test_meses_sem_vendas_retorna_so_o_mes_atual(cenario):
    client, _, _ = cenario
    meses = client.get("/estatisticas/meses").json()
    assert len(meses) == 1
    assert meses[0]["receita"] == 0


def test_detalhe_mes_agrupa_por_dia_e_compara_com_mes_anterior(cenario):
    client, produto_id, cliente_id = cenario
    venda_concluida(client, produto_id, datetime(2024, 2, 3, 10), 2, cliente_id)
    venda_concluida(client, produto_id, datetime(2024, 2, 3, 15), 1)
    venda_concluida(client, produto_id, datetime(2024, 2, 29, 9), 5)
    venda_concluida(client, produto_id, datetime(2024, 1, 10), 4)
    # pendente não conta
    client.post(
        "/reservas",
        json={"nome_comprador": "X", "itens": [{"produto_id": produto_id}]},
    )

    dados = client.get("/estatisticas/mes/2024/2").json()

    assert dados["label"] == "Fev/2024"
    assert dados["dias"]["labels"] == list(range(1, 30))  # 2024 é bissexto
    assert dados["dias"]["receita"][2] == 30
    assert dados["dias"]["vendas"][2] == 2
    assert dados["dias"]["receita"][28] == 50
    assert dados["melhor_dia"] == {"dia": 29, "receita": 50}

    resumo = dados["resumo"]
    assert resumo["receita"] == 80
    assert resumo["vendas"] == 3
    assert resumo["itens"] == 8
    assert resumo["clientes"] == 1
    assert resumo["online"] == {"vendas": 1, "receita": 20}
    assert resumo["presencial"] == {"vendas": 2, "receita": 60}

    assert dados["anterior"]["label"] == "Jan/2024"
    assert dados["anterior"]["receita"] == 40
    assert dados["top_produtos"] == [{"nome": "Caneca", "quantidade": 8}]


def test_detalhe_mes_de_janeiro_compara_com_dezembro(cenario):
    client, produto_id, _ = cenario
    venda_concluida(client, produto_id, datetime(2023, 12, 31))

    dados = client.get("/estatisticas/mes/2024/1").json()

    assert dados["anterior"]["label"] == "Dez/2023"
    assert dados["anterior"]["vendas"] == 1
    assert dados["melhor_dia"] is None


def test_detalhe_mes_invalido(cenario):
    client, _, _ = cenario
    assert client.get("/estatisticas/mes/2024/13").status_code == 422


def test_vendas_do_dia_lista_em_ordem_de_horario(cenario):
    client, produto_id, cliente_id = cenario
    venda_concluida(client, produto_id, datetime(2024, 5, 4, 18, 30), 1)
    venda_concluida(client, produto_id, datetime(2024, 5, 4, 9, 5), 3, cliente_id)
    venda_concluida(client, produto_id, datetime(2024, 5, 5, 9))

    dados = client.get("/estatisticas/dia/2024-05-04").json()

    assert [v["hora"] for v in dados["vendas"]] == ["09:05", "18:30"]
    assert dados["vendas"][0]["comprador"] == "joao"
    assert dados["vendas"][0]["presencial"] is False
    assert dados["vendas"][0]["itens"] == [{"nome": "Caneca", "quantidade": 3}]
    assert dados["vendas"][1]["comprador"] == "Maria Silva"
    assert dados["resumo"]["receita"] == 40


def test_vendas_do_dia_data_invalida(cenario):
    client, _, _ = cenario
    assert client.get("/estatisticas/dia/2024-02-30").status_code == 422


def test_padroes_por_dia_da_semana_e_hora(cenario):
    client, produto_id, _ = cenario
    venda_concluida(client, produto_id, datetime(2024, 5, 4, 18))  # sábado
    venda_concluida(client, produto_id, datetime(2024, 5, 11, 18, 59), 2)  # sábado

    dados = client.get("/estatisticas/padroes").json()

    assert dados["dias_semana"]["labels"][5] == "Sáb"
    assert dados["dias_semana"]["vendas"][5] == 2
    assert dados["dias_semana"]["receita"][5] == 30
    assert dados["horas"]["vendas"][18] == 2
    assert sum(dados["horas"]["vendas"]) == 2

    # filtrando pelos últimos dias, vendas antigas ficam de fora
    recentes = client.get("/estatisticas/padroes?dias=30").json()
    assert sum(recentes["dias_semana"]["vendas"]) == 0


def test_pagina_mostra_ticket_medio_formatado(cenario):
    client, produto_id, _ = cenario
    venda_concluida(client, produto_id, datetime.now(), 3)

    pagina = client.get("/statistics")
    assert pagina.status_code == 200
    assert "R$ 30,00" in pagina.text


def test_mes_em_andamento_compara_com_mesmo_periodo_do_mes_anterior(cenario):
    from openloja.services import estatisticas

    client, produto_id, _ = cenario
    venda_concluida(client, produto_id, datetime(2024, 1, 10))
    venda_concluida(client, produto_id, datetime(2024, 1, 20))  # depois do dia 15
    venda_concluida(client, produto_id, datetime(2024, 2, 5))

    with sessao_db() as session:
        dados = estatisticas.detalhe_mes(session, 2024, 2, agora=datetime(2024, 2, 15))

    assert dados["parcial"] is True
    assert dados["anterior"]["label"] == "1–15 Jan/2024"
    assert dados["anterior"]["vendas"] == 1
