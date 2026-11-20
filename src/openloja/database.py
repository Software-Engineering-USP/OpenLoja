"""Conexão com o banco, sessão por requisição e criação/migração das tabelas."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, inspect, text
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel, create_engine, select

from .config import settings
from .models import Loja, Reserva

engine: Engine = create_engine(settings.database_url)


def configure_engine(url: str) -> Engine:
    """Troca o banco usado pela aplicação (usado nos testes)."""
    global engine
    engine = create_engine(url)
    return engine


def new_session() -> Session:
    return Session(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with new_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def init_db() -> None:
    _migrate_sqlite()
    SQLModel.metadata.create_all(engine)

    with new_session() as session:
        if session.exec(select(Loja)).first() is None:
            session.add(Loja())
            session.commit()


# ---------------------------------------------------------------------
# Migrações leves para bancos SQLite criados por versões anteriores.
# create_all() só cria tabelas que não existem; colunas novas ou
# mudanças de restrição precisam ser aplicadas aqui.
# ---------------------------------------------------------------------


def _migrate_sqlite() -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("reserva"):
        return

    colunas = {c["name"]: c for c in inspector.get_columns("reserva")}

    # vendas presenciais: cliente_id passou a ser opcional e foi criada
    # a coluna nome_comprador. SQLite não permite remover NOT NULL com
    # ALTER TABLE, então a tabela é recriada (procedimento recomendado
    # em https://www.sqlite.org/lang_altertable.html).
    precisa_recriar = (
        "nome_comprador" not in colunas or not colunas["cliente_id"]["nullable"]
    )
    if precisa_recriar:
        _recriar_reserva(colunas)
    elif "estoque_baixado" not in colunas:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE reserva ADD COLUMN estoque_baixado "
                    "BOOLEAN NOT NULL DEFAULT 0"
                )
            )

    # reservas pendentes passaram a descontar o estoque. As concluídas
    # antes disso já tinham descontado; as pendentes antigas ainda não.
    if "estoque_baixado" not in colunas:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE reserva SET estoque_baixado = 1 WHERE concluida = 1")
            )


def _recriar_reserva(colunas: dict) -> None:
    novas_colunas = [c.name for c in Reserva.__table__.columns]
    comuns = [c for c in novas_colunas if c in colunas]
    lista = ", ".join(comuns)

    ddl = str(CreateTable(Reserva.__table__).compile(engine)).replace(
        "CREATE TABLE reserva", "CREATE TABLE reserva__nova", 1
    )

    with engine.connect() as conn:
        # PRAGMA foreign_keys não tem efeito dentro de transação
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()
        with conn.begin():
            conn.execute(text(ddl))
            conn.execute(
                text(f"INSERT INTO reserva__nova ({lista}) SELECT {lista} FROM reserva")
            )
            conn.execute(text("DROP TABLE reserva"))
            conn.execute(text("ALTER TABLE reserva__nova RENAME TO reserva"))
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()
