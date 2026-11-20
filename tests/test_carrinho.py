"""Carrinho e checkout."""

from helpers import criar_produto, criar_usuario, login


# ---------------------------------------------------------------------
# Carrinho / checkout
# ---------------------------------------------------------------------


def test_fluxo_completo_de_carrinho_e_checkout(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, preco=25, estoque=10)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/carrinho/add", params={"produto_id": produto_id, "quantidade": 2}
    )
    assert resposta.status_code == 200

    resposta = client.get("/carrinho")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 50

    resposta = client.patch(
        "/carrinho/item", params={"produto_id": produto_id, "nova_quantidade": 1}
    )
    assert resposta.status_code == 200

    resposta = client.post("/checkout")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 25

    resposta = client.get("/carrinho")
    assert resposta.json()["itens"] == []


def test_checkout_com_carrinho_vazio_falha(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post("/checkout")
    assert resposta.status_code == 400


def test_remover_item_do_carrinho(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, preco=10, estoque=10)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    client.post("/carrinho/add", params={"produto_id": produto_id, "quantidade": 1})
    resposta = client.delete(f"/carrinho/item/{produto_id}")
    assert resposta.status_code == 200

    resposta = client.get("/carrinho")
    assert resposta.json()["itens"] == []


# ---------------------------------------------------------------------
# POST /carrinho/sincronizar
# ---------------------------------------------------------------------


def test_sincronizar_carrinho_exige_login(client):
    resposta = client.post("/carrinho/sincronizar", json=[])
    assert resposta.status_code == 401


def test_sincronizar_carrinho_com_lista_vazia_nao_altera_carrinho(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post("/carrinho/sincronizar", json=[])
    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True

    resposta = client.get("/carrinho")
    assert resposta.json()["itens"] == []


def test_sincronizar_carrinho_adiciona_itens_novos(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/carrinho/sincronizar",
        json=[{"produto_id": produto_id, "quantidade": 3}],
    )
    assert resposta.status_code == 200

    resposta = client.get("/carrinho")
    assert resposta.json()["total"] == 60


def test_sincronizar_carrinho_soma_quantidade_a_item_existente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    client.post("/carrinho/add", params={"produto_id": produto_id, "quantidade": 1})

    resposta = client.post(
        "/carrinho/sincronizar",
        json=[{"produto_id": produto_id, "quantidade": 2}],
    )
    assert resposta.status_code == 200

    resposta = client.get("/carrinho")
    assert resposta.json()["total"] == 60


def test_sincronizar_carrinho_com_multiplos_produtos(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_a = criar_produto(client, nome="Caneca", preco=20, estoque=10)
    produto_b = criar_produto(client, nome="Copo", preco=10, estoque=10)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/carrinho/sincronizar",
        json=[
            {"produto_id": produto_a, "quantidade": 1},
            {"produto_id": produto_b, "quantidade": 2},
        ],
    )
    assert resposta.status_code == 200

    resposta = client.get("/carrinho")
    assert resposta.json()["total"] == 40
