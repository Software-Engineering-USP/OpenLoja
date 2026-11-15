"""Tabelas do banco de dados (SQLModel)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

CLIENTE_ID_FK = "cliente.id"
PRODUTO_ID_FK = "produto.id"


class Vendedor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    nome: str
    senha: str  # hash (ver security.py)


class Cliente(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    nome: str
    senha: str  # hash (ver security.py)

    reservas: list["Reserva"] = Relationship(back_populates="cliente")
    avaliacoes: list["Avaliacao"] = Relationship(back_populates="cliente")
    carrinho: Optional["Carrinho"] = Relationship(back_populates="cliente")


class ReservaProdutoLink(SQLModel, table=True):
    reserva_id: int | None = Field(
        default=None, foreign_key="reserva.id", primary_key=True
    )
    produto_id: int | None = Field(
        default=None, foreign_key=PRODUTO_ID_FK, primary_key=True
    )

    quantidade: int = Field(default=1)


class Produto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    quantidade_em_estoque: int
    nome: str
    preco: int

    descricao: str = Field(default="")
    categoria: str = Field(default="")
    tag: str = Field(default="")
    imagem: str | None = Field(default=None)

    avaliacoes: list["Avaliacao"] = Relationship(back_populates="produto")
    reservas: list["Reserva"] = Relationship(
        back_populates="produtos", link_model=ReservaProdutoLink
    )


class Reserva(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # None em vendas presenciais (comprador sem cadastro)
    cliente_id: int | None = Field(default=None, foreign_key=CLIENTE_ID_FK)
    # nome informado pelo vendedor em vendas presenciais
    nome_comprador: str | None = Field(default=None)

    valor: float = Field(default=0.0)
    concluida: bool = Field(default=False)
    valor_efetivo: float | None = Field(default=None)
    # horário local, sem fuso (mesmo formato das versões anteriores)
    data_conclusao: datetime | None = Field(default=None, sa_type=DateTime)

    cliente: Optional["Cliente"] = Relationship(back_populates="reservas")
    produtos: list["Produto"] = Relationship(
        back_populates="reservas", link_model=ReservaProdutoLink
    )

    @property
    def presencial(self) -> bool:
        return self.cliente_id is None

    @property
    def valor_final(self) -> float:
        """Valor que de fato entrou no caixa (efetivo, se ajustado)."""
        return self.valor_efetivo if self.valor_efetivo is not None else self.valor


class Avaliacao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    cliente_id: int | None = Field(default=None, foreign_key=CLIENTE_ID_FK)
    produto_id: int | None = Field(default=None, foreign_key=PRODUTO_ID_FK)

    nota: int
    texto: str
    dia: int
    mes: int
    ano: int
    horario: int  # HHMM

    produto: "Produto" = Relationship(back_populates="avaliacoes")
    cliente: "Cliente" = Relationship(back_populates="avaliacoes")


class CarrinhoProdutoLink(SQLModel, table=True):
    carrinho_id: int | None = Field(
        default=None, foreign_key="carrinho.id", primary_key=True
    )
    produto_id: int | None = Field(
        default=None, foreign_key=PRODUTO_ID_FK, primary_key=True
    )

    quantidade: int = Field(default=1)


class Carrinho(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    cliente_id: int | None = Field(default=None, foreign_key=CLIENTE_ID_FK)

    cliente: "Cliente" = Relationship(back_populates="carrinho")
    produtos: list["Produto"] = Relationship(link_model=CarrinhoProdutoLink)


class Loja(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Identidade
    nome: str = "Minha Loja"
    slogan: str = ""
    descricao: str = ""

    # Aparência
    logo: str | None = None
    banner: str | None = None

    cor_primaria: str = "#232978"
    cor_secundaria: str = "#0d6efd"
    cor_destaque: str = "#f59e0b"

    # Contato
    email: str = ""
    telefone: str = ""
    whatsapp: str = "5511999999999"
    endereco: str = ""

    # Redes sociais
    instagram: str = ""
    facebook: str = ""

    # Informações
    horario: str = ""
    trocas: str = ""
    devolucao: str = ""
