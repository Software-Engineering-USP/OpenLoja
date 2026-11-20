"""Regressões encontradas na revisão do PR de reorganização."""

from helpers import criar_produto, criar_usuario, id_do_cliente, login, vendedor_logado
from openloja.services import estatisticas
from openloja.database import new_session


def _reserva(client, cliente_id, itens):
    return client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "itens": [{"produto_id": p, "quantidade": q} for p, q in itens],
        },
    ).json()


def test_remover_produto_tira_do_carrinho_e_checkout_continua(client):
    vendedor_logado(client)
    removido = criar_produto(client, nome="Some")
    fica = criar_produto(client, nome="Fica", preco=30)
    criar_usuario(client, "joao")

    login(client, "joao")
    client.post("/carrinho/add", params={"produto_id": removido})
    client.post("/carrinho/add", params={"produto_id": fica})

    login(client, "dono")
    assert client.delete(f"/produtos/{removido}").status_code == 200

    login(client, "joao")
    resposta = client.post("/checkout")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 30
    assert [i["nome"] for i in resposta.json()["itens"]] == ["Fica"]


def test_remover_produto_recalcula_reserva_pendente(client):
    vendedor_logado(client)
    a = criar_produto(client, preco=100)
    b = criar_produto(client, preco=50)
    criar_usuario(client, "joao")
    reserva = _reserva(client, id_do_cliente(client, "joao"), [(a, 2), (b, 1)])
    assert reserva["valor"] == 250

    client.delete(f"/produtos/{a}")

    assert client.get(f"/reservas/{reserva['id']}").json()["valor"] == 50


def test_remover_produto_mantem_valor_de_venda_concluida(client):
    vendedor_logado(client)
    a = criar_produto(client, preco=100)
    criar_usuario(client, "joao")
    reserva = _reserva(client, id_do_cliente(client, "joao"), [(a, 1)])
    client.put(f"/reservas/{reserva['id']}/completar", json={})

    client.delete(f"/produtos/{a}")

    dados = client.get(f"/reservas/{reserva['id']}").json()
    assert dados["valor"] == 100
    assert dados["valor_efetivo"] == 100


def test_cliente_com_nome_em_branco_e_aceito(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": cliente_id,
            "nome_comprador": "",
            "itens": [{"produto_id": produto_id}],
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["cliente_id"] == cliente_id

    editada = client.put(
        f"/reservas/{resposta.json()['id']}",
        json={"cliente_id": cliente_id, "nome_comprador": "  "},
    )
    assert editada.status_code == 200


def test_top_produtos_ignora_reservas_pendentes(client):
    vendedor_logado(client)
    pendente = criar_produto(client, nome="Pendente", estoque=100)
    vendido = criar_produto(client, nome="Vendido", estoque=100)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    _reserva(client, cliente_id, [(pendente, 50)])
    venda = _reserva(client, cliente_id, [(vendido, 1)])
    client.put(f"/reservas/{venda['id']}/completar", json={})

    with new_session() as session:
        top = estatisticas.painel_estatisticas(session)["top_produtos"]

    assert top[0] == {"nome": "Vendido", "vendas": 1}
    assert {"nome": "Pendente", "vendas": 0} in top
