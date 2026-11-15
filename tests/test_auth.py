"""Contas, login e autorização."""

from helpers import criar_usuario, login


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
