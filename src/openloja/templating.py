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


def apenas_digitos(valor: str | None) -> str:
    """Remove tudo que não é dígito: '+55 (11) 9999-9999' -> '551199999999'."""
    return "".join(c for c in (valor or "") if c.isdigit())


def formatar_telefone(valor: str | None) -> str:
    """Formata telefone brasileiro: '5511999999999' -> '+55 (11) 99999-9999'.

    Aceita com ou sem DDI 55. Se o formato não for reconhecido, devolve o
    valor original.
    """
    digitos = apenas_digitos(valor)
    ddi = ""
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        ddi, digitos = "+55 ", digitos[2:]
    if len(digitos) not in (10, 11):
        return valor or ""
    ddd, numero = digitos[:2], digitos[2:]
    return f"{ddi}({ddd}) {numero[:-4]}-{numero[-4:]}"


def _com_ddi(valor: str | None) -> str:
    """Só os dígitos, com DDI 55 se vier apenas DDD + número."""
    digitos = apenas_digitos(valor)
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    return digitos


def link_whatsapp(valor: str | None) -> str:
    """Link wa.me para o número."""
    return f"https://wa.me/{_com_ddi(valor)}"


def link_telefone(valor: str | None) -> str:
    """Link tel: para o número (abre o discador no celular)."""
    return f"tel:+{_com_ddi(valor)}"


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
templates.env.filters["telefone"] = formatar_telefone
templates.env.filters["link_whatsapp"] = link_whatsapp
templates.env.filters["link_telefone"] = link_telefone
