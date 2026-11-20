"""Painel do vendedor: home e estatísticas."""

from datetime import datetime

from openloja.models import Reserva

from helpers import criar_produto, criar_usuario, id_do_cliente, login, sessao_db


# ---------------------------------------------------------------------
# show_profile (/home)
# ---------------------------------------------------------------------


def test_home_do_lojista_exige_login(client):
    resposta = client.get("/home")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_home_do_lojista(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/home")
    assert resposta.status_code == 403


def test_home_do_lojista_sem_vendas_mostra_zerado(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/home")
    assert resposta.status_code == 200


def test_home_do_lojista_reflete_estoque_atual(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_produto(client, nome="Copo", preco=15, estoque=5)

    resposta = client.get("/home")
    assert resposta.status_code == 200
    assert "15" in resposta.text
    assert "275" in resposta.text or "275,00" in resposta.text


def test_home_do_lojista_conta_venda_concluida_no_mes_atual(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 2}],
        },
    )
    reserva_id = resposta.json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    resposta = client.get("/home")
    assert resposta.status_code == 200
    assert "40" in resposta.text


def test_home_do_lojista_conta_novo_cliente_no_mes_atual(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )
    reserva_id = resposta.json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    resposta = client.get("/home")
    assert resposta.status_code == 200
    assert "1" in resposta.text


def test_home_do_lojista_nao_conta_reserva_pendente_como_venda(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )

    resposta = client.get("/home")
    assert resposta.status_code == 200
    assert "0" in resposta.text


# ---------------------------------------------------------------------
# GET /estatisticas/receita-mensal
# ---------------------------------------------------------------------


def test_receita_mensal_exige_login(client):
    resposta = client.get("/estatisticas/receita-mensal")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_receita_mensal(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/estatisticas/receita-mensal")
    assert resposta.status_code == 403


def test_receita_mensal_sem_vendas_retorna_listas_vazias(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/estatisticas/receita-mensal")
    assert resposta.status_code == 200
    assert resposta.json() == {"labels": [], "valores": []}


def test_receita_mensal_ignora_reserva_nao_concluida(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=10, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )

    resposta = client.get("/estatisticas/receita-mensal")
    assert resposta.json() == {"labels": [], "valores": []}


def test_receita_mensal_agrupa_por_mes_e_usa_valor_efetivo(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=10, estoque=100)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 3}],
        },
    )
    reserva_id = resposta.json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    with sessao_db() as session:
        reserva = session.get(Reserva, reserva_id)
        reserva.data_conclusao = datetime(2020, 1, 15)
        session.add(reserva)
        session.commit()

    client.put(f"/reservas/{reserva_id}/valor-efetivo", json={"valor_efetivo": 25.0})

    resposta = client.get("/estatisticas/receita-mensal")
    dados = resposta.json()
    assert dados["labels"] == ["Jan/2020"]
    assert dados["valores"] == [25.0]


def test_receita_mensal_ordena_meses_cronologicamente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=10, estoque=100)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    datas = [datetime(2021, 3, 1), datetime(2020, 1, 1), datetime(2020, 12, 1)]
    for data in datas:
        resposta = client.post(
            "/reservas",
            json={
                "cliente_id": cliente_id,
                "itens": [{"produto_id": produto_id, "quantidade": 1}],
            },
        )
        reserva_id = resposta.json()["id"]
        client.put(f"/reservas/{reserva_id}/completar", json={})

        with sessao_db() as session:
            reserva = session.get(Reserva, reserva_id)
            reserva.data_conclusao = data
            session.add(reserva)
            session.commit()

    resposta = client.get("/estatisticas/receita-mensal")
    assert resposta.json()["labels"] == ["Jan/2020", "Dez/2020", "Mar/2021"]


# ---------------------------------------------------------------------
# GET /statistics
# ---------------------------------------------------------------------


def test_statistics_exige_login(client):
    resposta = client.get("/statistics")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_statistics(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/statistics")
    assert resposta.status_code == 403


def test_statistics_sem_dados_retorna_pagina_valida(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/statistics")
    assert resposta.status_code == 200


def test_statistics_calcula_vendas_e_receita_do_mes_atual(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 2}],
        },
    )
    reserva_id = resposta.json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    resposta = client.get("/statistics")
    assert resposta.status_code == 200
    assert "40" in resposta.text


def test_statistics_ignora_reserva_concluida_em_mes_anterior(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 5}],
        },
    )
    reserva_id = resposta.json()["id"]
    client.put(f"/reservas/{reserva_id}/completar", json={})

    with sessao_db() as session:
        reserva = session.get(Reserva, reserva_id)
        reserva.data_conclusao = datetime(2020, 1, 1)
        session.add(reserva)
        session.commit()

    resposta = client.get("/statistics")
    assert resposta.status_code == 200
    # a venda de 2020 (R$ 100) não entra na receita deste mês
    assert "R$ 100" not in resposta.text
    assert "R$ 0" in resposta.text


def test_statistics_top_produtos_ordenado_por_vendas(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_mais_vendido = criar_produto(
        client, nome="Mais Vendido", preco=10, estoque=100
    )
    produto_menos_vendido = criar_produto(
        client, nome="Menos Vendido", preco=10, estoque=100
    )
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    for produto_id, quantidade in (
        (produto_mais_vendido, 5),
        (produto_menos_vendido, 1),
    ):
        reserva = client.post(
            "/reservas",
            json={
                "cliente_id": cliente_id,
                "itens": [{"produto_id": produto_id, "quantidade": quantidade}],
            },
        ).json()
        client.put(f"/reservas/{reserva['id']}/completar", json={})

    resposta = client.get("/statistics")
    assert resposta.status_code == 200
    pos_mais_vendido = resposta.text.find("Mais Vendido")
    pos_menos_vendido = resposta.text.find("Menos Vendido")
    assert pos_mais_vendido != -1
    assert pos_menos_vendido != -1
    assert pos_mais_vendido < pos_menos_vendido


def _venda(session, valor, data, valor_efetivo=None):
    session.add(
        Reserva(
            nome_comprador="Maria",
            valor=valor,
            valor_efetivo=valor_efetivo,
            concluida=True,
            estoque_baixado=True,
            data_conclusao=data,
        )
    )


def test_resumo_home_soma_vendas_do_dia(client):
    from openloja.services import estatisticas

    agora = datetime(2026, 3, 15, 18, 0)
    with sessao_db() as session:
        _venda(session, 50, datetime(2026, 3, 15, 9, 30))
        _venda(session, 40, datetime(2026, 3, 15, 17, 0), valor_efetivo=35)
        _venda(session, 100, datetime(2026, 3, 14, 23, 59))  # ontem
        _venda(session, 70, datetime(2025, 3, 15, 12, 0))  # mesmo dia, outro ano
        session.add(Reserva(nome_comprador="João", valor=999))  # pendente
        session.commit()

        resumo = estatisticas.resumo_home(session, agora=agora)

    assert resumo["receita_hoje"] == 85
    assert resumo["vendas_hoje"] == 2
    assert resumo["receita_mensal"] == 185


def test_home_do_lojista_mostra_vendas_de_hoje(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    with sessao_db() as session:
        _venda(session, 1234.5, datetime.now())
        session.commit()

    resposta = client.get("/home")
    assert "Vendas de Hoje" in resposta.text
    assert "R$ 1.234,50" in resposta.text
    assert "1 venda concluída hoje" in resposta.text
