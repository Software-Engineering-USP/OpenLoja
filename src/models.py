from sqlmodel import SQLModel, Field, Relationship


class Vendedor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    senha: str
    estacao_em_uso_id: int | None = Field(default=None, foreign_key="estacao.id")
    reservas: list["Reserva"] = Relationship(back_populates="vendedor")


class Cliente(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    senha: str
    reservas: list["Reserva"] = Relationship(back_populates="cliente")
    avaliacoes: list["Avaliacao"] = Relationship(back_populates="cliente")


class Loja(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nota: int
    nome: str
    vendedor_id: int | None = Field(default=None, foreign_key="vendedor.id")
    produtos: list["Produto"] = Relationship(back_populates="loja")


class Produto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    quantidade_em_estoque: int
    nome: str
    preco: int
    loja_id: int | None = Field(default=None, foreign_key="loja.id")
    reserva_id: int | None = Field(default=None, foreign_key="reserva.id")


class Reserva(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    produto_id: int | None = Field(default=None, foreign_key="produto.id")
    cliente_id: int = Field(foreign_key="usuario.id")
    loja_id: int = Field(foreign_key="loja.id")
    vendedor: "Vendedor" = Relationship(back_populates="reservas")
    cliente: "Cliente" = Relationship(back_populates="reservas")


class Avaliacao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nota: int
    texto: str
    dia: int
    horario: int
    produto_id: int | None = Field(default=None, foreign_key="produto.id")
