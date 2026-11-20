"""Reservas pendentes já descontam o estoque, evitando vender o mesmo item duas vezes."""

import sqlite3

from openloja import database
from openloja.models import Reserva

from helpers import criar_produto, sessao_db, vendedor_logado


def estoque(client, produto_id):
    return client.get(f"/produtos/{produto_id}").json()["quantidade_em_estoque"]


def reservar(client, produto_id, quantidade, **extra):
    return client.post(
        "/reservas",
        json={
            "nome_comprador": "Maria",
            "itens": [{"produto_id": produto_id, "quantidade": quantidade}],
            **extra,
        },
    )


def test_reserva_pendente_desconta_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)

    assert reservar(client, produto_id, 3).status_code == 200
    assert estoque(client, produto_id) == 2


def test_item_reservado_nao_pode_ser_reservado_de_novo(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=1)

    assert reservar(client, produto_id, 1).status_code == 200
    resposta = reservar(client, produto_id, 1)

    assert resposta.status_code == 400
    assert "Estoque insuficiente" in resposta.json()["detail"]
    assert len(client.get("/reservas").json()) == 1


def test_efetivar_reserva_pendente_nao_desconta_de_novo(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva_id = reservar(client, produto_id, 3).json()["id"]

    resposta = client.put(f"/reservas/{reserva_id}/completar", json={})

    assert resposta.status_code == 200
    assert estoque(client, produto_id) == 2


def test_efetivar_reserva_do_ultimo_item(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=1)
    reserva_id = reservar(client, produto_id, 1).json()["id"]

    assert client.put(f"/reservas/{reserva_id}/completar", json={}).status_code == 200
    assert estoque(client, produto_id) == 0


def test_deletar_reserva_pendente_devolve_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva_id = reservar(client, produto_id, 3).json()["id"]

    assert client.delete(f"/reservas/{reserva_id}").status_code == 200
    assert estoque(client, produto_id) == 5


def test_editar_reserva_pendente_ajusta_estoque(client):
    vendedor_logado(client)
    produto_a = criar_produto(client, nome="A", estoque=5)
    produto_b = criar_produto(client, nome="B", estoque=5)
    reserva_id = reservar(client, produto_a, 5).json()["id"]

    # mantém os 5 de A (o próprio estoque reservado conta) e adiciona 2 de B
    resposta = client.put(
        f"/reservas/{reserva_id}",
        json={
            "itens": [
                {"produto_id": produto_a, "quantidade": 5},
                {"produto_id": produto_b, "quantidade": 2},
            ]
        },
    )
    assert resposta.status_code == 200
    assert estoque(client, produto_a) == 0
    assert estoque(client, produto_b) == 3

    # reduz A para 1
    client.put(
        f"/reservas/{reserva_id}",
        json={"itens": [{"produto_id": produto_a, "quantidade": 1}]},
    )
    assert estoque(client, produto_a) == 4
    assert estoque(client, produto_b) == 5


def test_editar_reserva_alem_do_estoque_falha_sem_alterar_nada(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva_id = reservar(client, produto_id, 2).json()["id"]

    resposta = client.put(
        f"/reservas/{reserva_id}",
        json={"itens": [{"produto_id": produto_id, "quantidade": 6}]},
    )

    assert resposta.status_code == 400
    assert estoque(client, produto_id) == 3
    assert client.get(f"/reservas/{reserva_id}").json()["valor"] == 200


def test_checkout_desconta_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    client.post("/logout")

    client.post("/criarusuario", json={"nome": "joao", "senha": "123456"})
    client.post("/login", json={"nome": "joao", "senha": "123456"})
    client.post(f"/carrinho/add?produto_id={produto_id}&quantidade=2")

    assert client.post("/checkout").status_code == 200
    assert estoque(client, produto_id) == 3


def _reserva_pendente_antiga(client, produto_id, quantidade):
    """Reserva pendente criada antes desta mudança (estoque ainda não baixado)."""
    reserva_id = reservar(client, produto_id, quantidade).json()["id"]
    with sessao_db() as session:
        reserva = session.get(Reserva, reserva_id)
        reserva.estoque_baixado = False
        session.add(reserva)
        session.commit()
    # simula o estoque como era antes: nada descontado
    produto = client.get(f"/produtos/{produto_id}").json()
    produto["quantidade_em_estoque"] += quantidade
    client.put(f"/produtos/{produto_id}", json=produto)
    return reserva_id


def test_reserva_pendente_antiga_desconta_ao_efetivar(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva_id = _reserva_pendente_antiga(client, produto_id, 3)
    assert estoque(client, produto_id) == 5

    assert client.put(f"/reservas/{reserva_id}/completar", json={}).status_code == 200
    assert estoque(client, produto_id) == 2


def test_deletar_reserva_pendente_antiga_nao_altera_estoque(client):
    vendedor_logado(client)
    produto_id = criar_produto(client, estoque=5)
    reserva_id = _reserva_pendente_antiga(client, produto_id, 3)

    assert client.delete(f"/reservas/{reserva_id}").status_code == 200
    assert estoque(client, produto_id) == 5


def test_migracao_marca_vendas_concluidas_como_estoque_baixado(tmp_path):
    caminho = tmp_path / "antigo.db"
    with sqlite3.connect(caminho) as conn:
        conn.executescript(
            """
            CREATE TABLE cliente (id INTEGER PRIMARY KEY, nome VARCHAR NOT NULL,
                                  senha VARCHAR NOT NULL);
            CREATE TABLE reserva (
                id INTEGER NOT NULL PRIMARY KEY,
                cliente_id INTEGER REFERENCES cliente (id),
                nome_comprador VARCHAR,
                valor FLOAT NOT NULL,
                concluida BOOLEAN NOT NULL,
                valor_efetivo FLOAT,
                data_conclusao DATETIME
            );
            INSERT INTO cliente VALUES (1, 'joao', '123');
            INSERT INTO reserva VALUES (1, 1, NULL, 50.0, 1, 45.0, '2026-01-10');
            INSERT INTO reserva VALUES (2, 1, NULL, 30.0, 0, NULL, NULL);
            """
        )

    original = database.engine
    try:
        engine = database.configure_engine(f"sqlite:///{caminho}")
        database.init_db()
        database.init_db()  # idempotente

        with engine.connect() as conn:
            linhas = conn.exec_driver_sql(
                "SELECT id, estoque_baixado FROM reserva ORDER BY id"
            ).all()
        assert [tuple(linha) for linha in linhas] == [(1, 1), (2, 0)]
        engine.dispose()
    finally:
        database.engine = original
