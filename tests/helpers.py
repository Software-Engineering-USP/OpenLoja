"""Atalhos usados pelos testes para montar cenários."""

from openloja.database import new_session


def criar_usuario(client, nome, senha="123456"):
    resposta = client.post("/criarusuario", json={"nome": nome, "senha": senha})
    assert resposta.status_code == 200
    return resposta


def login(client, nome, senha="123456"):
    return client.post("/login", json={"nome": nome, "senha": senha})


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


def vendedor_logado(client, nome="dono"):
    criar_usuario(client, nome)
    login(client, nome)


def sessao_db():
    """Sessão direta no banco do teste, para preparar cenários."""
    return new_session()
