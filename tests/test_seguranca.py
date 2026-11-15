"""Correções de segurança e validação encontradas na revisão do código."""

import io

from sqlmodel import select

from openloja.models import Cliente, Vendedor
from openloja.security import senha_tem_hash

from helpers import (
    criar_produto,
    criar_usuario,
    id_do_cliente,
    login,
    sessao_db,
    vendedor_logado,
)


def test_senhas_sao_guardadas_com_hash(client):
    criar_usuario(client, "dono", senha="segredo")
    criar_usuario(client, "joao", senha="outro")

    with sessao_db() as session:
        vendedor = session.exec(select(Vendedor)).one()
        cliente = session.exec(select(Cliente)).one()

    assert senha_tem_hash(vendedor.senha) and "segredo" not in vendedor.senha
    assert senha_tem_hash(cliente.senha) and "outro" not in cliente.senha


def test_conta_antiga_com_senha_em_texto_puro_ainda_loga_e_e_convertida(client):
    with sessao_db() as session:
        session.add(Vendedor(nome="antigo", senha="1234"))
        session.commit()

    assert login(client, "antigo", senha="errada").status_code == 404
    assert login(client, "antigo", senha="1234").status_code == 200

    with sessao_db() as session:
        vendedor = session.exec(select(Vendedor)).one()
    assert senha_tem_hash(vendedor.senha)
    assert login(client, "antigo", senha="1234").status_code == 200


def test_rota_db_nao_expoe_senhas(client):
    vendedor_logado(client)
    criar_usuario(client, "joao")

    dados = client.get("/db").json()
    assert all("senha" not in u for u in dados["clientes"] + dados["vendedores"])


def test_vendedor_nao_usa_carrinho_de_cliente_com_mesmo_id(client):
    # vendedor id=1 e cliente id=1 ficam em tabelas diferentes
    vendedor_logado(client)
    produto_id = criar_produto(client)

    resposta = client.post("/carrinho/add", params={"produto_id": produto_id})
    assert resposta.status_code == 403
    assert client.get("/carrinho").status_code == 403


def test_vendedor_nao_assina_avaliacao_como_cliente(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes", json={"nota": 5, "texto": "ótimo"}
    )
    assert resposta.status_code == 403


def test_carrinho_rejeita_produto_inexistente_e_quantidade_invalida(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")
    login(client, "joao")

    assert client.post("/carrinho/add", params={"produto_id": 999}).status_code == 404
    assert (
        client.post(
            "/carrinho/add", params={"produto_id": produto_id, "quantidade": 0}
        ).status_code
        == 400
    )


def test_reserva_rejeita_quantidade_zero_ou_negativa(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)
    criar_usuario(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": id_do_cliente(client, "joao"),
            "itens": [{"produto_id": produto_id, "quantidade": -2}],
        },
    )
    assert resposta.status_code == 422


def test_reserva_com_produto_repetido_soma_quantidades(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, preco=10)
    criar_usuario(client, "joao")

    resposta = client.post(
        "/reservas",
        json={
            "cliente_id": id_do_cliente(client, "joao"),
            "itens": [
                {"produto_id": produto_id, "quantidade": 1},
                {"produto_id": produto_id, "quantidade": 2},
            ],
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["valor"] == 30


def test_upload_rejeita_arquivo_que_nao_e_imagem(client):
    vendedor_logado(client)

    resposta = client.post(
        "/loja/logo",
        files={"logo": ("script.html", io.BytesIO(b"<script>"), "text/html")},
    )
    assert resposta.status_code == 400


def test_atualizar_produto_nao_troca_o_id(client):
    vendedor_logado(client)
    produto_id = criar_produto(client)

    resposta = client.put(f"/produtos/{produto_id}", json={"id": 999, "nome": "Novo"})
    assert resposta.status_code == 200
    assert resposta.json()["id"] == produto_id


def test_theme_css_nao_permite_injecao(client):
    vendedor_logado(client)
    client.put("/loja", json={"cor_primaria": "red;} body{display:none"})

    css = client.get("/theme.css").text
    assert "}" not in css.split("--cor-primaria:")[1].split(";")[0]
    assert "display:none" not in css
