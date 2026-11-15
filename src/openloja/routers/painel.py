"""Painel do vendedor: home, estatísticas e visão geral do banco."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
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
    contexto = estatisticas.painel_estatisticas(session)
    resumo = contexto["estatisticas"]
    resumo["receita_mensal_fmt"] = formatar_moeda(resumo["receita_mensal"])
    resumo["ticket_medio_fmt"] = formatar_moeda(
        resumo["receita_mensal"] / resumo["vendas_mes"] if resumo["vendas_mes"] else 0
    )
    return templates.TemplateResponse(
        request=request, name="stat.html", context=contexto
    )


# dados do gráfico de receita mensal
@router.get("/estatisticas/receita-mensal")
def receita_mensal(admin: Admin, session: SessionDep):
    return estatisticas.receita_por_mes(session)


# resumo de todos os meses (sem lacunas), para o gráfico e o seletor de mês
@router.get("/estatisticas/meses")
def resumo_meses(admin: Admin, session: SessionDep):
    return estatisticas.resumo_meses(session)


# detalhamento de um mês: vendas por dia, comparação com o mês anterior etc.
@router.get("/estatisticas/mes/{ano}/{mes}")
def detalhe_mes(
    admin: Admin,
    session: SessionDep,
    ano: Annotated[int, Path(ge=2000, le=9999)],
    mes: Annotated[int, Path(ge=1, le=12)],
):
    return estatisticas.detalhe_mes(session, ano, mes)


# lista das vendas concluídas num dia (data no formato AAAA-MM-DD)
@router.get("/estatisticas/dia/{dia}")
def vendas_do_dia(admin: Admin, session: SessionDep, dia: date):
    return estatisticas.vendas_do_dia(session, dia)


# distribuição por dia da semana e hora do dia (opcionalmente só os últimos N dias)
@router.get("/estatisticas/padroes")
def padroes_de_venda(
    admin: Admin,
    session: SessionDep,
    dias: Annotated[int | None, Query(ge=1, le=3650)] = None,
):
    return estatisticas.padroes_de_venda(session, dias)


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
