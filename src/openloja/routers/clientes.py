"""Página do cliente e gestão de clientes pelo vendedor."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select

from ..database import SessionDep
from ..dependencies import ActiveUser, Admin
from ..models import Cliente, Reserva, Vendedor
from ..services import reservas as svc
from ..templating import templates

router = APIRouter()

NOT_FOUND = {404: {"description": svc.CLIENT_NOT_FOUND}}


# página "Minha Conta" do cliente (vendedores voltam para o painel)
@router.get("/cliente", response_class=HTMLResponse, responses=NOT_FOUND)
def cliente_page(request: Request, user: ActiveUser, session: SessionDep):
    if isinstance(user, Vendedor):
        return RedirectResponse(url="/home", status_code=303)

    cliente = svc.buscar_cliente(session, user.id)

    return templates.TemplateResponse(
        request=request,
        name="clientPage.html",
        context={"cliente": cliente, **svc.historico_cliente(session, cliente.id)},
    )


@router.get("/clientes", response_class=HTMLResponse)
def listar_clientes_page(request: Request, admin: Admin, session: SessionDep):
    clientes = session.exec(select(Cliente)).all()
    resumo = {c.id: {"pedidos": 0, "total_gasto": 0.0} for c in clientes}

    for r in session.exec(select(Reserva)).all():
        dados = resumo.get(r.cliente_id)
        if dados is None:  # venda presencial ou cliente removido
            continue
        dados["pedidos"] += 1
        if r.concluida:
            dados["total_gasto"] += r.valor_final

    return templates.TemplateResponse(
        request=request,
        name="clientsList.html",
        context={
            "clientes": [{"id": c.id, "nome": c.nome, **resumo[c.id]} for c in clientes]
        },
    )


@router.get("/clientes/{cliente_id}", response_class=HTMLResponse, responses=NOT_FOUND)
def perfil_cliente_page(
    request: Request, cliente_id: int, admin: Admin, session: SessionDep
):
    cliente = svc.buscar_cliente(session, cliente_id)

    return templates.TemplateResponse(
        request=request,
        name="clientProfile.html",
        context={"cliente": cliente, **svc.historico_cliente(session, cliente_id)},
    )
