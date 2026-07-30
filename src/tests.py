"""
Testes de backend (pytest) para a API FastAPI do projeto.

Não testam nada de frontend/HTML/CSS — apenas o comportamento das rotas,
regras de negócio e integridade dos dados.

Como rodar:
    pip install -r requirements.txt
    pytest tests.py -v

Cada teste roda contra um banco SQLite temporário e isolado (criado em um
diretório temporário do pytest), então rodar os testes NUNCA mexe no seu
database.db real.
"""

import io
import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

# precisa existir uma SECRET_KEY antes de importar o main.py,
# senão ele gera uma aleatória a cada import (não teria problema
# aqui, mas fica mais previsível assim)
os.environ.setdefault("SECRET_KEY", "chave-de-teste-fixa-para-pytest")

import main  # noqa: E402  (import depois do os.environ de propósito)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Cliente de testes com banco de dados totalmente isolado.

    - troca o "engine" do main.py por um SQLite temporário, então cada
      teste começa com um banco vazio (só com a Loja padrão, criada no
      startup).
    - muda o diretório de trabalho para a pasta temporária, para que
      uploads de imagem (logo/banner/produto) não sujem a pasta
      static/images do projeto real.
    """
    monkeypatch.chdir(tmp_path)

    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(main, "engine", test_engine)

    with TestClient(main.app) as c:
        yield c


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def criar_usuario(client, nome, senha="123456"):
    resposta = client.post("/criarusuario", json={"nome": nome, "senha": senha})
    assert resposta.status_code == 200
    return resposta


def login(client, nome, senha="123456"):
    return client.post("/login", params={"nome": nome, "senha": senha})


def criar_produto(client, nome="Produto", preco=100, estoque=5):
    resposta = client.post(
        "/produtos",
        json={"nome": nome, "preco": preco, "quantidade_em_estoque": estoque},
    )
    assert resposta.status_code == 200
    return resposta.json()["id"]


def id_do_cliente(client, nome):
    resposta = client.get("/db")
    for c in resposta.json()["clientes"]:
        if c["nome"] == nome:
            return c["id"]
    raise AssertionError(f"cliente '{nome}' não encontrado em /db")


# ---------------------------------------------------------------------
# Contas e login
# ---------------------------------------------------------------------


def test_primeiro_usuario_criado_vira_vendedor(client):
    criar_usuario(client, "dono")
    resposta = login(client, "dono")
    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "vendedor"


def test_segundo_usuario_criado_vira_cliente(client):
    criar_usuario(client, "dono")
    criar_usuario(client, "joao")
    resposta = login(client, "joao")
    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "cliente"


def test_nao_permite_usuario_duplicado(client):
    criar_usuario(client, "dono")
    resposta = client.post("/criarusuario", json={"nome": "dono", "senha": "outra"})
    assert resposta.status_code == 404


def test_login_com_senha_errada_falha(client):
    criar_usuario(client, "dono")
    resposta = login(client, "dono", senha="senha-errada")
    assert resposta.status_code == 404


def test_login_usuario_inexistente_falha(client):
    resposta = login(client, "fantasma")
    assert resposta.status_code == 404


def test_logout_remove_cookie(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    resposta = client.post("/logout")
    assert resposta.status_code == 200
    assert "session" not in client.cookies


def test_pagina_inicial_pede_criacao_de_conta_quando_nao_ha_vendedor(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "criarusuario" in resposta.text.lower() or "conta" in resposta.text.lower()


# ---------------------------------------------------------------------
# Autorização
# ---------------------------------------------------------------------


def test_rota_de_admin_exige_login(client):
    resposta = client.get("/stock")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_rota_de_admin(client):
    criar_usuario(client, "dono")
    criar_usuario(client, "joao")
    login(client, "joao")
    resposta = client.get("/stock")
    assert resposta.status_code == 403


def test_vendedor_acessa_rota_de_admin(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    resposta = client.get("/stock")
    assert resposta.status_code == 200


# ---------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------


def test_crud_produtos(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    produto_id = criar_produto(client, nome="Camiseta", preco=50, estoque=10)

    resposta = client.get(f"/produtos/{produto_id}")
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Camiseta"

    resposta = client.put(f"/produtos/{produto_id}", json={"nome": "Camiseta Azul"})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Camiseta Azul"

    resposta = client.delete(f"/produtos/{produto_id}")
    assert resposta.status_code == 200

    resposta = client.get(f"/produtos/{produto_id}")
    assert resposta.status_code == 404


def test_criar_produto_sem_login_falha(client):
    resposta = client.post(
        "/produtos",
        json={"nome": "Camiseta", "preco": 50, "quantidade_em_estoque": 10},
    )
    assert resposta.status_code == 401


def test_buscar_produto_inexistente_retorna_404(client):
    resposta = client.get("/produtos/9999")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------
# Configurações da loja / tema
# ---------------------------------------------------------------------


def test_loja_tem_valores_padrao(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/loja")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["nome"] == "Minha Loja"
    assert dados["cor_primaria"] == "#232978"


def test_atualizar_loja_reflete_no_theme_css(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.put(
        "/loja",
        json={"nome": "Loja da Maria", "cor_primaria": "#ff0000"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Loja da Maria"
    assert resposta.json()["cor_primaria"] == "#ff0000"

    resposta_css = client.get("/theme.css")
    assert resposta_css.status_code == 200
    assert resposta_css.headers["content-type"].startswith("text/css")
    assert "--cor-primaria: #ff0000" in resposta_css.text


def test_atualizar_loja_sem_login_falha(client):
    resposta = client.put("/loja", json={"nome": "Hackeada"})
    assert resposta.status_code == 401


def test_upload_de_logo_atualiza_loja(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    arquivo = io.BytesIO(b"conteudo-fake-de-imagem")
    resposta = client.post(
        "/loja/logo",
        files={"logo": ("logo.png", arquivo, "image/png")},
    )
    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True

    resposta_loja = client.get("/loja")
    assert resposta_loja.json()["logo"] is not None


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
