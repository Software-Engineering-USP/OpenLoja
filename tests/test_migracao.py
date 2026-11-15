"""Bancos criados por versões anteriores continuam funcionando."""

import sqlite3

from sqlalchemy import inspect

from openloja import database


def test_banco_antigo_ganha_suporte_a_venda_presencial(tmp_path):
    caminho = tmp_path / "antigo.db"

    # esquema da tabela reserva antes das vendas presenciais
    with sqlite3.connect(caminho) as conn:
        conn.executescript(
            """
            CREATE TABLE cliente (id INTEGER PRIMARY KEY, nome VARCHAR NOT NULL,
                                  senha VARCHAR NOT NULL);
            CREATE TABLE reserva (
                id INTEGER NOT NULL PRIMARY KEY,
                cliente_id INTEGER NOT NULL REFERENCES cliente (id),
                valor FLOAT NOT NULL,
                concluida BOOLEAN NOT NULL,
                valor_efetivo FLOAT,
                data_conclusao DATETIME
            );
            INSERT INTO cliente VALUES (1, 'joao', '123');
            INSERT INTO reserva VALUES (1, 1, 50.0, 1, 45.0, '2026-01-10 12:00:00');
            """
        )

    original = database.engine
    try:
        engine = database.configure_engine(f"sqlite:///{caminho}")
        database.init_db()
        database.init_db()  # idempotente

        colunas = {c["name"]: c for c in inspect(engine).get_columns("reserva")}
        assert "nome_comprador" in colunas
        assert colunas["cliente_id"]["nullable"]

        with engine.connect() as conn:
            linha = conn.exec_driver_sql(
                "SELECT id, cliente_id, valor, valor_efetivo FROM reserva"
            ).one()
        assert tuple(linha) == (1, 1, 50.0, 45.0)
        engine.dispose()
    finally:
        database.engine = original
