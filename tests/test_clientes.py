"""Clientes (visão do vendedor e do próprio cliente)."""

from sqlmodel import delete

from openloja.models import Cliente

from helpers import criar_produto, criar_usuario, id_do_cliente, login, sessao_db


# ---------------------------------------------------------------------
# Perfil do cliente (visão do vendedor)
# ---------------------------------------------------------------------


def test_vendedor_ve_lista_de_clientes(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    criar_usuario(client, "joao")

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "joao" in resposta.text


def test_vendedor_ve_perfil_e_historico_do_cliente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Bone", preco=40)

    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )

    resposta = client.get(f"/clientes/{cliente_id}")
    assert resposta.status_code == 200
    assert "Bone" in resposta.text


def test_cliente_nao_acessa_perfil_pela_rota_de_admin(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")
    client.post("/logout")

    login(client, "joao")
    resposta = client.get(f"/clientes/{cliente_id}")
    assert resposta.status_code == 403


def test_perfil_de_cliente_inexistente_retorna_404(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    resposta = client.get("/clientes/9999")
    assert resposta.status_code == 404


def test_cliente_ve_seu_proprio_historico(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Mochila", preco=90)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
    )
    client.post("/logout")

    login(client, "joao")
    resposta = client.get("/cliente")
    assert resposta.status_code == 200
    assert "Mochila" in resposta.text
    # o cliente não vê quanto já gastou na loja
    assert "Total Gasto" not in resposta.text


# ---------------------------------------------------------------------
# /clientes — agregação de pedidos e total_gasto por cliente
# ---------------------------------------------------------------------


def test_lista_clientes_sem_reservas_mostra_zerado(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    criar_usuario(client, "joao")

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "joao" in resposta.text


def test_lista_clientes_nao_soma_reserva_pendente_no_total_gasto(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": produto_id, "quantidade": 3}],
        },
    )

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "1" in resposta.text


def test_lista_clientes_soma_valor_da_reserva_concluida(client):
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

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "40" in resposta.text


def test_lista_clientes_usa_valor_efetivo_quando_definido(client):
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
    client.put(
        f"/reservas/{reserva_id}/valor-efetivo",
        json={"valor_efetivo": 15.0},
    )

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "15" in resposta.text


def test_lista_clientes_soma_multiplos_pedidos_do_mesmo_cliente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=10, estoque=20)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    for _ in range(2):
        resposta = client.post(
            "/reservas",
            json={
                "cliente_id": cliente_id,
                "itens": [{"produto_id": produto_id, "quantidade": 1}],
            },
        )
        reserva_id = resposta.json()["id"]
        client.put(f"/reservas/{reserva_id}/completar", json={})

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "2" in resposta.text
    assert "20" in resposta.text


def test_lista_clientes_ignora_reserva_de_cliente_removido(client):
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

    resposta = client.get("/clientes")
    assert resposta.status_code == 200
    assert "joao" not in resposta.text
