// ---- Busca em tempo real ----
document.getElementById("orders-search").addEventListener("input", (e) => {
  const termo = e.target.value.toLowerCase();
  document
    .querySelectorAll("#orders-table tbody tr[data-cliente]")
    .forEach((linha) => {
      const cliente = linha.getAttribute("data-cliente");
      linha.style.display = cliente.includes(termo) ? "" : "none";
    });
});

// ---- Modal (nova / editar reserva) ----
const modal = document.getElementById("order-modal");
const modalTitle = document.getElementById("order-modal-title");
const modalReservaId = document.getElementById("modal-reserva-id");
const modalCliente = document.getElementById("modal-cliente");
const modalProduto = document.getElementById("modal-produto");
const modalQuantidade = document.getElementById("modal-quantidade");
const itemsList = document.getElementById("order-items-list");
const itemsEmpty = document.getElementById("order-items-empty");
const totalEl = document.getElementById("order-total");

let itensReserva = []; // [{produto_id, nome, preco, quantidade}]

function formatarMoeda(valor) {
  return `R$ ${valor.toFixed(2)}`;
}

function renderizarItens() {
  itemsList.querySelectorAll(".order-item-row").forEach((el) => el.remove());

  if (itensReserva.length === 0) {
    itemsEmpty.style.display = "block";
  } else {
    itemsEmpty.style.display = "none";
  }

  itensReserva.forEach((item, indice) => {
    const linha = document.createElement("div");
    linha.className = "order-item-row";
    linha.innerHTML = `
      <span class="order-item-nome">${item.nome} <span class="order-item-qtd">x${item.quantidade}</span></span>
      <span class="order-item-subtotal">${formatarMoeda(item.preco * item.quantidade)}</span>
      <button type="button" class="order-item-remove" data-indice="${indice}" title="Remover">&times;</button>
    `;
    itemsList.appendChild(linha);
  });

  const total = itensReserva.reduce(
    (soma, item) => soma + item.preco * item.quantidade,
    0,
  );
  totalEl.textContent = formatarMoeda(total);
}

itemsList.addEventListener("click", (evento) => {
  if (evento.target.classList.contains("order-item-remove")) {
    const indice = Number(evento.target.dataset.indice);
    itensReserva.splice(indice, 1);
    renderizarItens();
  }
});

document.getElementById("add-item-btn").addEventListener("click", () => {
  const opcao = modalProduto.selectedOptions[0];
  const quantidade = Number(modalQuantidade.value);

  if (!opcao || !opcao.value) {
    alert("Selecione um produto.");
    return;
  }

  if (!quantidade || quantidade < 1) {
    alert("Informe uma quantidade válida.");
    return;
  }

  const produtoId = Number(opcao.value);
  const existente = itensReserva.find((item) => item.produto_id === produtoId);

  if (existente) {
    existente.quantidade += quantidade;
  } else {
    itensReserva.push({
      produto_id: produtoId,
      nome: opcao.dataset.nome,
      preco: Number(opcao.dataset.preco),
      quantidade: quantidade,
    });
  }

  modalProduto.value = "";
  modalQuantidade.value = 1;
  renderizarItens();
});

function abrirModal({ id = "", clienteId = "", itens = [] } = {}) {
  modalTitle.textContent = id ? "Editar Reserva" : "Nova Reserva";
  modalReservaId.value = id;
  modalCliente.value = clienteId;

  itensReserva = itens.map((item) => ({
    produto_id: item.produto_id,
    nome: item.nome,
    preco: item.preco,
    quantidade: item.quantidade,
  }));

  modalProduto.value = "";
  modalQuantidade.value = 1;
  renderizarItens();

  modal.classList.remove("hidden");
}

function fecharModal() {
  modal.classList.add("hidden");
}

document
  .getElementById("add-order-btn")
  .addEventListener("click", () => abrirModal());
document.getElementById("modal-cancel").addEventListener("click", fecharModal);

document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const linha = btn.closest("tr");
    const itens = JSON.parse(linha.dataset.itens || "[]");
    abrirModal({
      id: btn.dataset.id,
      clienteId: linha.dataset.clienteId,
      itens: itens,
    });
  });
});

document.getElementById("modal-save").addEventListener("click", async () => {
  if (!modalCliente.value) {
    alert("Selecione um cliente.");
    return;
  }

  if (itensReserva.length === 0) {
    alert("Adicione ao menos um produto à reserva.");
    return;
  }

  const dados = {
    cliente_id: Number(modalCliente.value),
    itens: itensReserva.map((item) => ({
      produto_id: item.produto_id,
      quantidade: item.quantidade,
    })),
  };

  const reservaId = modalReservaId.value;

  const resposta = await fetch(
    reservaId ? `/reservas/${reservaId}` : "/reservas",
    {
      method: reservaId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    },
  );

  if (resposta.ok) {
    window.location.reload();
  } else {
    const erro = await resposta.json().catch(() => ({}));
    alert(erro.detail || "Erro ao salvar a reserva.");
  }
});

// ---- Efetivar reserva ----
document.querySelectorAll(".complete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Efetivar esta reserva?")) return;

    const resposta = await fetch(`/reservas/${btn.dataset.id}/completar`, {
      method: "PUT",
    });

    if (resposta.ok) {
      window.location.reload();
    } else {
      const erro = await resposta.json().catch(() => ({}));
      alert(erro.detail || "Erro ao efetivar a reserva.");
    }
  });
});

// ---- Deletar reserva ----
document.querySelectorAll(".delete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Tem certeza que deseja remover esta reserva?")) return;

    const resposta = await fetch(`/reservas/${btn.dataset.id}`, {
      method: "DELETE",
    });

    if (resposta.ok) {
      btn.closest("tr").remove();
    } else {
      const erro = await resposta.json().catch(() => ({}));
      alert(erro.detail || "Erro ao remover a reserva.");
    }
  });
});
