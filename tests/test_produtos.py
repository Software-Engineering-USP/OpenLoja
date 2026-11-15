"""Produtos, avaliações e páginas públicas."""

from helpers import criar_produto, criar_usuario, login


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
# Avaliações
# ---------------------------------------------------------------------


def test_criar_avaliacao_com_nota_minima_valida(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"nota": 0, "texto": "Nota minima"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["nota"] == 0


def test_criar_avaliacao_com_nota_maxima_valida(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"nota": 5, "texto": "Nota maxima"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["nota"] == 5


# ---------------------------------------------------------------------
# Avaliações (continuação)
# ---------------------------------------------------------------------


def test_criar_avaliacao_sem_nota_falha_validacao(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"texto": "Faltou a nota"},
    )
    assert resposta.status_code == 422


def test_criar_avaliacao_sem_texto_falha_validacao(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"nota": 4},
    )
    assert resposta.status_code == 422


def test_criar_avaliacao_com_nota_nao_numerica_falha_validacao(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"nota": "cinco", "texto": "Nota invalida"},
    )
    assert resposta.status_code == 422


def test_avaliacoes_de_produtos_diferentes_nao_se_misturam(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_a = criar_produto(client, nome="Produto A", preco=10)
    produto_b = criar_produto(client, nome="Produto B", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")
    client.post(
        f"/produtos/{produto_a}/avaliacoes",
        json={"nota": 5, "texto": "Sobre o produto A"},
    )
    client.post(
        f"/produtos/{produto_b}/avaliacoes",
        json={"nota": 1, "texto": "Sobre o produto B"},
    )

    avaliacoes_a = client.get(f"/produtos/{produto_a}/avaliacoes").json()
    avaliacoes_b = client.get(f"/produtos/{produto_b}/avaliacoes").json()

    assert len(avaliacoes_a) == 1
    assert avaliacoes_a[0]["texto"] == "Sobre o produto A"

    assert len(avaliacoes_b) == 1
    assert avaliacoes_b[0]["texto"] == "Sobre o produto B"


def test_criar_avaliacao_registra_dia_mes_ano_horario(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.post(
        f"/produtos/{produto_id}/avaliacoes",
        json={"nota": 3, "texto": "Ok"},
    )
    dados = resposta.json()
    assert isinstance(dados["dia"], int)
    assert 1 <= dados["mes"] <= 12
    assert dados["ano"] >= 2024
    assert isinstance(dados["horario"], int)


# ---------------------------------------------------------------------
# get_optional_user (via /homeCliente e /product/{id})
# ---------------------------------------------------------------------


def test_home_cliente_acessivel_sem_login(client):
    resposta = client.get("/homeCliente")
    assert resposta.status_code == 200


def test_home_cliente_acessivel_logado_como_cliente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get("/homeCliente")
    assert resposta.status_code == 200


def test_home_cliente_acessivel_logado_como_vendedor(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/homeCliente")
    assert resposta.status_code == 200


def test_pagina_produto_acessivel_sem_login(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    resposta = client.get(f"/product/{produto_id}")
    assert resposta.status_code == 200


def test_pagina_produto_acessivel_logado_como_cliente(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)
    client.post("/logout")

    criar_usuario(client, "joao")
    login(client, "joao")

    resposta = client.get(f"/product/{produto_id}")
    assert resposta.status_code == 200


def test_pagina_produto_acessivel_logado_como_vendedor(client):
    criar_usuario(client, "dono")
    login(client, "dono")
    produto_id = criar_produto(client, nome="Caneca", preco=20)

    resposta = client.get(f"/product/{produto_id}")
    assert resposta.status_code == 200


def test_pagina_produto_inexistente_retorna_404_mesmo_sem_login(client):
    resposta = client.get("/product/9999")
    assert resposta.status_code == 404


def test_pagina_produto_inexistente_retorna_404_mesmo_logado(client):
    criar_usuario(client, "dono")
    login(client, "dono")

    resposta = client.get("/product/9999")
    assert resposta.status_code == 404
