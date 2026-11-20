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


# ---------------------------------------------------------------------
# Página "Sobre nós"
# ---------------------------------------------------------------------


def test_formatar_telefone_e_link_whatsapp():
    from openloja.templating import formatar_telefone, link_whatsapp

    assert formatar_telefone("5511999999999") == "+55 (11) 99999-9999"
    assert formatar_telefone("1133334444") == "(11) 3333-4444"
    assert formatar_telefone("abc") == "abc"
    assert link_whatsapp("+55 (11) 99999-9999") == "https://wa.me/5511999999999"
    assert link_whatsapp("11999999999") == "https://wa.me/5511999999999"


def test_sobre_nos_mostra_whatsapp_formatado_com_link(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.put("/loja", json={"whatsapp": "5511988887777"})

    resposta = client.get("/about")
    assert resposta.status_code == 200
    assert 'href="https://wa.me/5511988887777"' in resposta.text
    assert "+55 (11) 98888-7777" in resposta.text
