"""Reservas, estoque e página de pedidos."""

from sqlmodel import delete

from openloja.models import Cliente, Produto

from helpers import criar_produto, criar_usuario, id_do_cliente, login, sessao_db


# ---------------------------------------------------------------------
# Reservas / estoque
# ---------------------------------------------------------------------


def test_cliente_cria_reserva_para_si_mesmo(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, estoque=5)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/reservas",
        json={"itens": [{"produto_id": produto_id, "quantidade": 2}]},
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["valor"] == 200
    assert dados["concluida"] is False


def test_reserva_sem_itens_falha(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post("/reservas", json={"itens": []})
    assert resposta.status_code == 400


def test_concluir_reserva_reduz_estoque(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, estoque=5)
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

    resposta = client.put(f"/reservas/{reserva_id}/completar", json={})
    assert resposta.status_code == 200
    assert resposta.json()["concluida"] is True

    resposta_produto = client.get(f"/produtos/{produto_id}")
    assert resposta_produto.json()["quantidade_em_estoque"] == 2


def test_concluir_reserva_sem_estoque_suficiente_falha(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, estoque=1)
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

    resposta = client.put(f"/reservas/{reserva_id}/completar", json={})
    assert resposta.status_code == 400


def test_deletar_reserva_concluida_repoe_estoque(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, estoque=5)
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

    resposta = client.delete(f"/reservas/{reserva_id}")
    assert resposta.status_code == 200

    resposta_produto = client.get(f"/produtos/{produto_id}")
    assert resposta_produto.json()["quantidade_em_estoque"] == 5


# ---------------------------------------------------------------------
# GET /reservas/{id} — buscar_reserva
# ---------------------------------------------------------------------


def test_buscar_reserva_exige_login(client):
    resposta = client.get("/reservas/1")
    assert resposta.status_code == 401


def test_cliente_nao_busca_reserva_pela_rota_de_admin(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/reservas/1")
    assert resposta.status_code == 403


def test_buscar_reserva_inexistente_retorna_404(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/reservas/9999")
    assert resposta.status_code == 404


def test_buscar_reserva_com_sucesso(client):
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

    resposta = client.get(f"/reservas/{reserva_id}")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["id"] == reserva_id
    assert dados["cliente_id"] == cliente_id
    assert dados["valor"] == 40


# ---------------------------------------------------------------------
# PUT /reservas/{id} — editar_reserva
# ---------------------------------------------------------------------


def test_editar_reserva_exige_login(client):
    resposta = client.put("/reservas/1", json={})
    assert resposta.status_code == 401


def test_cliente_nao_edita_reserva(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.put("/reservas/1", json={})
    assert resposta.status_code == 403


def test_editar_reserva_inexistente_retorna_404(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.put("/reservas/9999", json={})
    assert resposta.status_code == 404


def test_editar_reserva_ja_concluida_falha(client):
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

    resposta = client.put(
        f"/reservas/{reserva_id}",
        json={"itens": [{"produto_id": produto_id, "quantidade": 2}]},
    )
    assert resposta.status_code == 400


def test_editar_reserva_com_cliente_inexistente_falha(client):
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

    resposta = client.put(f"/reservas/{reserva_id}", json={"cliente_id": 9999})
    assert resposta.status_code == 404


def test_editar_reserva_troca_cliente_com_sucesso(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    criar_usuario(client, "maria")
    cliente_joao = id_do_cliente(client, "joao")
    cliente_maria = id_do_cliente(client, "maria")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_joao,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )
    reserva_id = resposta.json()["id"]

    resposta = client.put(f"/reservas/{reserva_id}", json={"cliente_id": cliente_maria})
    assert resposta.status_code == 200
    assert resposta.json()["cliente_id"] == cliente_maria


def test_editar_reserva_com_itens_vazios_falha(client):
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

    resposta = client.put(f"/reservas/{reserva_id}", json={"itens": []})
    assert resposta.status_code == 400


def test_editar_reserva_com_produto_inexistente_falha(client):
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

    resposta = client.put(
        f"/reservas/{reserva_id}",
        json={"itens": [{"produto_id": 9999, "quantidade": 1}]},
    )
    assert resposta.status_code == 404


def test_editar_reserva_substitui_itens_e_recalcula_valor(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_a = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    produto_b = criar_produto(client, nome="Copo", preco=15, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_a, "quantidade": 2}],
        },
    )
    reserva_id = resposta.json()["id"]
    assert resposta.json()["valor"] == 40

    resposta = client.put(
        f"/reservas/{reserva_id}",
        json={"itens": [{"produto_id": produto_b, "quantidade": 3}]},
    )
    assert resposta.status_code == 200
    assert resposta.json()["valor"] == 45


def test_editar_reserva_sem_alteracoes_retorna_reserva_inalterada(client):
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

    resposta = client.put(f"/reservas/{reserva_id}", json={})
    assert resposta.status_code == 200
    assert resposta.json()["valor"] == 20
    assert resposta.json()["cliente_id"] == cliente_id


# ---------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------


def test_orders_exige_login(client):
    resposta = client.get("/orders")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_orders(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/orders")
    assert resposta.status_code == 403


def test_orders_sem_reservas_retorna_pagina_vazia(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/orders")
    assert resposta.status_code == 200


def test_orders_retorna_itens_da_reserva(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca Especial", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 2}],
        },
    )

    resposta = client.get("/orders")
    assert resposta.status_code == 200
    assert "Caneca Especial" in resposta.text
    assert "joao" in resposta.text


def test_orders_ignora_item_cujo_produto_foi_removido(client):
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

    with sessao_db() as session:
        session.exec(delete(Produto).where(Produto.id == produto_id))
        session.commit()

    resposta = client.get("/orders")
    assert resposta.status_code == 200
    assert "Caneca" not in resposta.text


def test_orders_mostra_traco_quando_cliente_foi_removido(client):
    # cobre o branch "r.cliente.nome if r.cliente else '—'"
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

    with sessao_db() as session:
        session.exec(delete(Cliente).where(Cliente.id == cliente_id))
        session.commit()

    resposta = client.get("/orders")
    assert resposta.status_code == 200
    assert "—" in resposta.text
