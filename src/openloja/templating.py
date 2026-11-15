"""Configuração do Jinja2 compartilhada pelas rotas."""

from fastapi.templating import Jinja2Templates
from sqlmodel import select

from . import database
from .config import TEMPLATES_DIR
from .models import Loja

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def formatar_moeda(valor: float) -> str:
    """Formata como real: 1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_loja_atual() -> Loja:
    """Dados da loja para qualquer template (via global "loja_atual")."""
    with database.new_session() as session:
        loja = session.exec(select(Loja)).first()
        return loja if loja else Loja()


templates.env.globals["loja_atual"] = obter_loja_atual
templates.env.filters["moeda"] = formatar_moeda
