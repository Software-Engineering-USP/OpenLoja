from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

class Usuario(SQLModel):
    nome: str
    senha: str


class Vendedor(SQLModel, table=True):
    id: Optional[int] | None = Field(default=None, primary_key=True)

    nome: str
    senha: str


class Cliente(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    nome: str
    senha: str

    reservas: List["Reserva"] = Relationship(back_populates="cliente")
    avaliacoes: List["Avaliacao"] = Relationship(back_populates="cliente")
    carrinho: Optional["Carrinho"] = Relationship(back_populates="cliente")


class ReservaProdutoLink(SQLModel, table=True):
    reserva_id: int | None = Field(
        default=None, foreign_key="reserva.id", primary_key=True
    )
    produto_id: int | None = Field(
        default=None, foreign_key="produto.id", primary_key=True
    )

    quantidade: int = Field(default=1)


class Produto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    quantidade_em_estoque: int
    nome: str
    preco: int

    imagem: str | None = Field(default=None)

    avaliacoes: List["Avaliacao"] = Relationship(back_populates="produto")
    reservas: List["Reserva"] = Relationship(
        back_populates="produtos", link_model=ReservaProdutoLink
    )


class Reserva(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    cliente_id: int = Field(foreign_key="cliente.id")

    valor: float = Field(default=0.0)
    concluida: bool = Field(default=False)
    valor_efetivo: float | None = Field(default=None)
    data_conclusao: datetime | None = Field(default=None)


    cliente: "Cliente" = Relationship(back_populates="reservas")
    produtos: List["Produto"] = Relationship(
        back_populates="reservas", link_model=ReservaProdutoLink
    )


class Avaliacao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    cliente_id: int | None = Field(default=None, foreign_key="cliente.id")
    produto_id: int | None = Field(default=None, foreign_key="produto.id")

    nota: int
    texto: str
    dia: int
    horario: int

    produto: "Produto" = Relationship(back_populates="avaliacoes")
    cliente: "Cliente" = Relationship(back_populates="avaliacoes")


class CarrinhoProdutoLink(SQLModel, table=True):
    carrinho_id: int | None = Field(
        default=None, foreign_key="carrinho.id", primary_key=True
    )
    produto_id: int | None = Field(
        default=None, foreign_key="produto.id", primary_key=True
    )

    quantidade: int = Field(default=1)


class Carrinho(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    cliente_id: int | None = Field(default=None, foreign_key="cliente.id")

    cliente: "Cliente" = Relationship(back_populates="carrinho")
    produtos: List["Produto"] = Relationship(link_model=CarrinhoProdutoLink)
