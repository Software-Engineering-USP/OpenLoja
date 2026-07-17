from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional

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

class Usuario(SQLModel):
    nome: str
    senha: str

class Produto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    quantidade_em_estoque: int
    nome: str
    preco: int

    avaliacoes: List["Avaliacao"] = Relationship(back_populates="produto")
    reservas: List["Reserva"] = Relationship(back_populates="produto")
    

class Reserva(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    produto_id: int | None = Field(default=None, foreign_key="produto.id")
    cliente_id: int = Field(foreign_key="cliente.id")

    cliente: "Cliente" = Relationship(back_populates="reservas")
    produto: "Produto" = Relationship(back_populates="reservas")


class Avaliacao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nota: int
    texto: str
    dia: int
    horario: int
    cliente_id: int | None = Field(default=None, foreign_key="cliente.id")
    produto_id: int | None = Field(default=None, foreign_key="produto.id")

    produto: "Produto" = Relationship(back_populates="avaliacoes")
    cliente: "Cliente" = Relationship(back_populates="avaliacoes")
