"""Configurações e tema da loja, página "Sobre"."""

from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile
from sqlmodel import Session, select

from ..database import SessionDep
from ..dependencies import Admin, OptionalUser
from ..models import Loja
from ..services.uploads import salvar_imagem
from ..templating import obter_loja_atual, templates

router = APIRouter()


def _loja(session: Session) -> Loja:
    loja = session.exec(select(Loja)).first()
    if loja is None:
        loja = Loja()
        session.add(loja)
        session.commit()
        session.refresh(loja)
    return loja


@router.get("/loja")
def buscar_loja(admin: Admin, session: SessionDep):
    return _loja(session)


@router.put("/loja")
def atualizar_loja(dados: Loja, admin: Admin, session: SessionDep):
    loja = _loja(session)
    loja.sqlmodel_update(dados.model_dump(exclude_unset=True, exclude={"id"}))

    session.add(loja)
    session.commit()
    session.refresh(loja)
    return loja


@router.post("/loja/logo")
def enviar_logo(
    logo: Annotated[UploadFile, File(...)], admin: Admin, session: SessionDep
):
    loja = _loja(session)
    loja.logo = salvar_imagem(logo, "loja_logo")
    session.add(loja)
    session.commit()
    return {"ok": True, "logo": loja.logo}


@router.post("/loja/banner")
def enviar_banner(
    banner: Annotated[UploadFile, File(...)], admin: Admin, session: SessionDep
):
    loja = _loja(session)
    loja.banner = salvar_imagem(banner, "loja_banner")
    session.add(loja)
    session.commit()
    return {"ok": True, "banner": loja.banner}


# CSS com as cores escolhidas pelo vendedor como variáveis
# (--cor-primaria etc.), importado antes dos demais .css
@router.get("/theme.css")
def theme_css():
    loja = obter_loja_atual()

    css = f"""/* gerado automaticamente a partir das configurações da loja */
:root {{
  --cor-primaria: {_cor(loja.cor_primaria)};
  --cor-secundaria: {_cor(loja.cor_secundaria)};
  --cor-destaque: {_cor(loja.cor_destaque)};
}}
"""
    return Response(
        content=css, media_type="text/css", headers={"Cache-Control": "no-cache"}
    )


def _cor(valor: str) -> str:
    # evita que um valor com ";" ou "}" injete regras extras no CSS
    return "".join(c for c in valor if c.isalnum() or c in "#(),.% ")


@router.get("/settings")
def settings_page(request: Request, admin: Admin):
    return templates.TemplateResponse(request=request, name="settings.html")


@router.get("/about")
def about(request: Request, user: OptionalUser, session: SessionDep):
    loja = session.exec(select(Loja)).first()
    return templates.TemplateResponse(
        request=request, name="about.html", context={"usuario": user, "loja": loja}
    )
