"""Painel do vendedor: home, estatísticas e visão geral do banco."""

from fastapi import APIRouter, Request
from sqlmodel import select

from ..database import SessionDep
from ..dependencies import Admin
from ..models import Avaliacao, Cliente, Produto, Reserva, Vendedor
from ..schemas import UsuarioPublico
from ..services import estatisticas
from ..templating import formatar_moeda, templates

router = APIRouter()


@router.get("/home")
def show_profile(request: Request, admin: Admin, session: SessionDep):
    resumo = estatisticas.resumo_home(session)

    return templates.TemplateResponse(
        request=request,
        name="homeOwner.html",
        context={
            "receita_mensal_fmt": formatar_moeda(resumo["receita_mensal"]),
            "itens_em_estoque": resumo["itens_em_estoque"],
            "valor_em_estoque_fmt": formatar_moeda(resumo["valor_em_estoque"]),
            "vendas_mes": resumo["vendas_mes"],
            "novos_clientes": resumo["novos_clientes"],
        },
    )


@router.get("/statistics")
def statistics(request: Request, admin: Admin, session: SessionDep):
    return templates.TemplateResponse(
        request=request,
        name="stat.html",
        context=estatisticas.painel_estatisticas(session),
    )


# dados do gráfico de receita mensal
@router.get("/estatisticas/receita-mensal")
def receita_mensal(admin: Admin, session: SessionDep):
    return estatisticas.receita_por_mes(session)


# visão geral do banco para depuração (sem as senhas)
@router.get("/db")
def visualizar_db(admin: Admin, session: SessionDep):
    def publicos(modelo):
        return [
            UsuarioPublico.model_validate(u, from_attributes=True)
            for u in session.exec(select(modelo)).all()
        ]

    return {
        "clientes": publicos(Cliente),
        "vendedores": publicos(Vendedor),
        "produtos": session.exec(select(Produto)).all(),
        "reservas": session.exec(select(Reserva)).all(),
        "avaliacoes": session.exec(select(Avaliacao)).all(),
    }
