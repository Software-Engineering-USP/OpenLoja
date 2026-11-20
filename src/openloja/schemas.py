"""Modelos de entrada/saída da API (não são tabelas)."""

from sqlmodel import Field, SQLModel


class Usuario(SQLModel):
    nome: str
    senha: str


class UsuarioPublico(SQLModel):
    id: int | None
    nome: str


class ReservaItemInput(SQLModel):
    produto_id: int
    quantidade: int = Field(default=1, ge=1)


class ReservaCreate(SQLModel):
    # vendedor: informe cliente_id OU nome_comprador (venda presencial)
    cliente_id: int | None = None
    nome_comprador: str | None = None
    itens: list[ReservaItemInput] = []
    # efetiva a venda na hora (desconta estoque), comum em vendas presenciais
    concluir: bool = False
    valor_efetivo: float | None = None


class ReservaUpdate(SQLModel):
    cliente_id: int | None = None
    nome_comprador: str | None = None
    itens: list[ReservaItemInput] | None = None


class ValorEfetivoUpdate(SQLModel):
    valor_efetivo: float | None = None


class AvaliacaoCreate(SQLModel):
    nota: int
    texto: str


class CarrinhoItem(SQLModel):
    produto_id: int
    quantidade: int = Field(default=1, ge=1)
