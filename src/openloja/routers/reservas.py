"""Reservas (pedidos) e vendas, incluindo vendas presenciais."""

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from ..database import SessionDep
from ..dependencies import ActiveUser, Admin
from ..models import Cliente, Produto, Reserva, Vendedor
from ..schemas import ReservaCreate, ReservaUpdate, ValorEfetivoUpdate
from ..services import reservas as svc
from ..templating import templates

router = APIRouter()

NOT_FOUND = {404: {"description": svc.RESERVE_NOT_FOUND}}


# página de pedidos do vendedor
@router.get("/orders")
def orders(request: Request, admin: Admin, session: SessionDep):
    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={
            "reservas": svc.listar_visoes(session),
            "clientes": session.exec(select(Cliente)).all(),
            "produtos": session.exec(select(Produto)).all(),
        },
    )


# Cria uma reserva.
# - cliente: a reserva é sempre dele.
# - vendedor: informa "cliente_id" (cliente cadastrado) ou "nome_comprador"
#   (venda presencial, sem cadastro). Com "concluir": true a venda já é
#   efetivada na hora, descontando o estoque.
@router.post(
    "/reservas",
    responses={
        404: {"description": "Produto ou cliente não encontrado"},
        400: {"description": "Reserva inválida ou estoque insuficiente"},
        403: {"description": "Cliente não pode efetivar vendas"},
    },
)
def criar_reserva(dados: ReservaCreate, user: ActiveUser, session: SessionDep):
    if not dados.itens:
        raise HTTPException(400, "A reserva precisa ter ao menos um produto.")

    reserva = Reserva()

    if isinstance(user, Vendedor):
        if dados.cliente_id is None and dados.nome_comprador is None:
            raise HTTPException(
                400,
                "Informe o cliente para quem a reserva será criada "
                "ou o nome do comprador (venda presencial).",
            )
        svc.definir_comprador(session, reserva, dados.cliente_id, dados.nome_comprador)
    else:
        if dados.concluir:
            raise HTTPException(403, "Apenas vendedores podem efetivar vendas.")
        reserva.cliente_id = user.id

    svc.definir_itens(session, reserva, dados.itens)

    if dados.concluir:
        svc.efetivar(session, reserva, dados.valor_efetivo)

    session.commit()
    session.refresh(reserva)
    return reserva


@router.get("/reservas")
def listar_reservas(admin: Admin, session: SessionDep):
    return session.exec(select(Reserva)).all()


@router.get("/reservas/{reserva_id}", responses=NOT_FOUND)
def buscar_reserva(reserva_id: int, admin: Admin, session: SessionDep):
    return svc.buscar_reserva(session, reserva_id)


# edita uma reserva pendente: comprador (cliente ou presencial) e/ou itens
@router.put(
    "/reservas/{reserva_id}",
    responses={
        404: {"description": "Reserva, cliente ou produto não encontrado"},
        400: {"description": "Reserva já concluída ou inválida"},
    },
)
def editar_reserva(
    reserva_id: int, dados: ReservaUpdate, admin: Admin, session: SessionDep
):
    reserva = svc.buscar_reserva(session, reserva_id)

    if reserva.concluida:
        raise HTTPException(400, "Reserva já concluída não pode ser editada")

    svc.definir_comprador(session, reserva, dados.cliente_id, dados.nome_comprador)

    if dados.itens is not None:
        svc.definir_itens(session, reserva, dados.itens)

    session.add(reserva)
    session.commit()
    session.refresh(reserva)
    return reserva


@router.delete("/reservas/{reserva_id}", responses=NOT_FOUND)
def deletar_reserva(reserva_id: int, admin: Admin, session: SessionDep):
    svc.remover(session, svc.buscar_reserva(session, reserva_id))
    session.commit()
    return {"message": "Reserva removida"}


@router.put(
    "/reservas/{reserva_id}/completar",
    responses={
        404: {"description": "Reserva ou produto não encontrados"},
        400: {
            "description": "Reserva já concluída, valor efetivo inválido "
            "ou produto sem estoque suficiente"
        },
    },
)
def concluir_reserva(
    reserva_id: int,
    admin: Admin,
    session: SessionDep,
    dados: ValorEfetivoUpdate | None = None,
):
    reserva = svc.buscar_reserva(session, reserva_id)
    svc.efetivar(session, reserva, dados.valor_efetivo if dados else None)

    session.commit()
    session.refresh(reserva)
    return reserva


# ajusta o valor efetivo de uma venda já concluída (ex.: desconto)
@router.put(
    "/reservas/{reserva_id}/valor-efetivo",
    responses={
        **NOT_FOUND,
        400: {"description": "Reserva não concluída ou valor efetivo inválido"},
    },
)
def editar_valor_efetivo(
    reserva_id: int, dados: ValorEfetivoUpdate, admin: Admin, session: SessionDep
):
    if dados.valor_efetivo is None:
        raise HTTPException(400, "Informe o novo valor efetivo.")

    if dados.valor_efetivo < 0:
        raise HTTPException(400, "O valor efetivo não pode ser negativo.")

    reserva = svc.buscar_reserva(session, reserva_id)

    if not reserva.concluida:
        raise HTTPException(
            400, "A reserva precisa estar efetivada para ajustar o valor."
        )

    reserva.valor_efetivo = dados.valor_efetivo
    session.add(reserva)
    session.commit()
    session.refresh(reserva)
    return reserva
