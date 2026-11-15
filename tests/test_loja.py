"""Configurações e tema da loja."""

import io

from helpers import criar_usuario, login


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
# GET /loja — buscar_loja
# ---------------------------------------------------------------------


def test_buscar_loja_exige_login(client):
    resposta = client.get("/loja")
    assert resposta.status_code == 401


def test_cliente_nao_acessa_buscar_loja(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/loja")
    assert resposta.status_code == 403
