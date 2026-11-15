"""Configuração do Jinja2 compartilhada pelas rotas."""

from fastapi.templating import Jinja2Templates
from sqlmodel import select

from . import database
from .config import STATIC_DIR, TEMPLATES_DIR
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


def static_url(caminho: str) -> str:
    """URL de um arquivo em /static com a data de modificação como versão.

    Assim o navegador baixa o CSS/JS de novo sempre que o arquivo muda,
    em vez de usar uma cópia antiga em cache.
    """
    try:
        versao = int((STATIC_DIR / caminho).stat().st_mtime)
    except OSError:
        return f"/static/{caminho}"
    return f"/static/{caminho}?v={versao}"


templates.env.globals["static_url"] = static_url
templates.env.globals["loja_atual"] = obter_loja_atual
templates.env.filters["moeda"] = formatar_moeda
