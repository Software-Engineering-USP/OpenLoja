"""Vendas presenciais: o vendedor registra a venda só com o nome do comprador."""

from helpers import (
    criar_produto,
    criar_usuario,
    id_do_cliente,
    login,
    vendedor_logado,
)


def venda_presencial(client, produto_id, quantidade=1, **extra):
    return client.post(
        "/reservas",
        json={
            "nome_comprador": "Maria Silva",
            "itens": [{"produto_id": produto_id, "quantidade": quantidade}],
            **extra,
        },
    )


def test_vendedor_cria_venda_presencial_pendente(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, preco=30, estoque=5)

    resposta = venda_presencial(client, produto_id, quantidade=2)

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["cliente_id"] is None
    assert dados["nome_comprador"] == "Maria Silva"
    assert dados["valor"] == 60
    assert dados["concluida"] is False
    # pendente já reserva o estoque, para o item não ser vendido duas vezes
    assert client.get(f"/produtos/{produto_id}").json()["quantidade_em_estoque"] == 3


def test_venda_presencial_efetivada_na_hora_desconta_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, preco=30, estoque=5)

    resposta = venda_presencial(client, produto_id, quantidade=2, concluir=True)

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["concluida"] is True
    assert dados["valor_efetivo"] == 60
    assert dados["data_conclusao"] is not None
    assert client.get(f"/produtos/{produto_id}").json()["quantidade_em_estoque"] == 3


def test_venda_presencial_com_valor_cobrado_diferente(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, preco=30, estoque=5)

    resposta = venda_presencial(client, produto_id, concluir=True, valor_efetivo=25)

    assert resposta.json()["valor_efetivo"] == 25


def test_venda_presencial_sem_estoque_nao_cria_reserva(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=1)

    resposta = venda_presencial(client, produto_id, quantidade=3, concluir=True)

    assert resposta.status_code == 400
    assert client.get("/reservas").json() == []
    assert client.get(f"/produtos/{produto_id}").json()["quantidade_em_estoque"] == 1


def test_venda_presencial_exige_nome(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)

    resposta = client.post(
        "/reservas",
        json={"nome_comprador": "   ", "itens": [{"produto_id": produto_id}]},
    )
    assert resposta.status_code == 400


def test_nao_aceita_cliente_e_nome_ao_mesmo_tempo(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": id_do_cliente(client, "joao"),
            "nome_comprador": "Maria",
            "itens": [{"produto_id": produto_id}],
        },
    )
    assert resposta.status_code == 400


def test_vendedor_sem_cliente_nem_nome_falha(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)

    resposta = client.post("/reservas", json={"itens": [{"produto_id": produto_id}]})
    assert resposta.status_code == 400


def test_cliente_nao_pode_efetivar_a_propria_reserva(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/reservas",
        json={"itens": [{"produto_id": produto_id}], "concluir": True},
    )
    assert resposta.status_code == 403


def test_cliente_nao_cria_venda_presencial_em_nome_de_outro(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        "/reservas",
        json={"nome_comprador": "Outra", "itens": [{"produto_id": produto_id}]},
    )
    assert resposta.status_code == 200
    assert resposta.json()["cliente_id"] is not None
    assert resposta.json()["nome_comprador"] is None


def test_orders_mostra_comprador_presencial(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, nome="Caneca")
    venda_presencial(client, produto_id)

    pagina = client.get("/orders")
    assert pagina.status_code == 200
    assert "Maria Silva" in pagina.text
    assert "Presencial" in pagina.text


def test_orders_tem_um_unico_botao_de_nova_venda(client):
    vendedor_logado(client)
    pagina = client.get("/orders")

    assert pagina.text.count('id="add-order-btn"') == 1
    assert "add-walkin-btn" not in pagina.text


def test_editar_troca_cliente_por_venda_presencial_e_volta(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")
    cliente_id = id_do_cliente(client, "joao")

    reserva = client.post(
        "/reservas",
        json={"cliente_id": cliente_id, "itens": [{"produto_id": produto_id}]},
    ).json()

    editada = client.put(
        f"/reservas/{reserva['id']}", json={"nome_comprador": "Maria"}
    ).json()
    assert editada["cliente_id"] is None
    assert editada["nome_comprador"] == "Maria"

    de_volta = client.put(
        f"/reservas/{reserva['id']}", json={"cliente_id": cliente_id}
    ).json()
    assert de_volta["cliente_id"] == cliente_id
    assert de_volta["nome_comprador"] is None


def test_venda_presencial_entra_na_receita_mas_nao_em_novos_clientes(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, preco=40, estoque=5)
    venda_presencial(client, produto_id, concluir=True)

    dados = client.get("/estatisticas/receita-mensal").json()
    assert dados["valores"] == [40.0]

    home = client.get("/home")
    assert home.status_code == 200
    assert "R$ 40,00" in home.text


def test_venda_presencial_nao_aparece_na_lista_de_clientes(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    venda_presencial(client, produto_id, concluir=True)

    pagina = client.get("/clientes")
    assert pagina.status_code == 200
    assert "Maria Silva" not in pagina.text


def test_deletar_venda_presencial_concluida_repoe_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva = venda_presencial(client, produto_id, quantidade=2, concluir=True).json()

    assert client.delete(f"/reservas/{reserva['id']}").status_code == 200
    assert client.get(f"/produtos/{produto_id}").json()["quantidade_em_estoque"] == 5
