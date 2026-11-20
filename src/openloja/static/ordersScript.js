// escapa texto vindo do servidor antes de inseri-lo em HTML
// (nomes, avaliações etc. são digitados por usuários)
function escapeHtml(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// ---- Busca em tempo real ----
document.getElementById("orders-search").addEventListener("input", (e) => {
  const termo = e.target.value.toLowerCase();
  document
    .querySelectorAll("#orders-table tbody tr[data-cliente]")
    .forEach((linha) => {
      const cliente = linha.dataset.cliente;
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
const campoCliente = document.getElementById("campo-cliente");
const campoPresencial = document.getElementById("campo-presencial");
const modalNomeComprador = document.getElementById("modal-nome-comprador");
const campoEfetivar = document.getElementById("campo-efetivar");
const modalEfetivar = document.getElementById("modal-efetivar");
const campoValorEfetivo = document.getElementById("campo-valor-efetivo");
const modalValorEfetivo = document.getElementById("modal-valor-efetivo");
const radiosTipo = document.querySelectorAll('input[name="tipo-comprador"]');

function tipoComprador() {
  return document.querySelector('input[name="tipo-comprador"]:checked').value;
}

// mostra o seletor de cliente ou o campo de nome, conforme o tipo
function atualizarTipoComprador() {
  const presencial = tipoComprador() === "presencial";
  campoCliente.hidden = presencial;
  campoPresencial.hidden = !presencial;
}

function atualizarCampoValor() {
  campoValorEfetivo.hidden = !modalEfetivar.checked;
}

radiosTipo.forEach((radio) =>
  radio.addEventListener("change", () => {
    atualizarTipoComprador();
    // vendas presenciais normalmente são pagas na hora
    if (!modalReservaId.value) {
      modalEfetivar.checked = tipoComprador() === "presencial";
      atualizarCampoValor();
    }
    (tipoComprador() === "presencial" ? modalNomeComprador : modalCliente).focus();
  }),
);
modalEfetivar.addEventListener("change", atualizarCampoValor);

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
      <span class="order-item-nome">${escapeHtml(item.nome)} <span class="order-item-qtd">x${item.quantidade}</span></span>
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

function abrirModal({
  id = "",
  clienteId = "",
  itens = [],
  presencial = false,
  nomeComprador = "",
} = {}) {
  modalTitle.textContent = id ? "Editar Reserva" : "Nova Venda";
  modalReservaId.value = id;
  modalCliente.value = clienteId;
  modalNomeComprador.value = nomeComprador;

  radiosTipo.forEach((radio) => {
    radio.checked = radio.value === (presencial ? "presencial" : "cliente");
  });
  atualizarTipoComprador();

  // efetivar na hora só ao criar; reservas existentes usam o botão "Efetivar"
  campoEfetivar.hidden = Boolean(id);
  modalEfetivar.checked = !id && presencial;
  modalValorEfetivo.value = "";
  atualizarCampoValor();

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
      presencial: linha.dataset.presencial === "true",
      nomeComprador: linha.dataset.nomeComprador,
    });
  });
});

document.getElementById("modal-save").addEventListener("click", async () => {
  const presencial = tipoComprador() === "presencial";
  const nomeComprador = modalNomeComprador.value.trim();

  if (presencial && !nomeComprador) {
    alert("Informe o nome do comprador.");
    return;
  }

  if (!presencial && !modalCliente.value) {
    alert("Selecione um cliente.");
    return;
  }

  if (itensReserva.length === 0) {
    alert("Adicione ao menos um produto à reserva.");
    return;
  }

  const reservaId = modalReservaId.value;

  const dados = {
    itens: itensReserva.map((item) => ({
      produto_id: item.produto_id,
      quantidade: item.quantidade,
    })),
  };

  if (presencial) {
    dados.nome_comprador = nomeComprador;
  } else {
    dados.cliente_id = Number(modalCliente.value);
  }

  if (!reservaId && modalEfetivar.checked) {
    dados.concluir = true;

    const entrada = modalValorEfetivo.value.trim();
    if (entrada !== "") {
      const numero = Number(entrada.replace(",", "."));
      if (Number.isNaN(numero) || numero < 0) {
        alert("Valor cobrado inválido.");
        return;
      }
      dados.valor_efetivo = numero;
    }
  }

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
    const linha = btn.closest("tr");
    const valorCheio = linha.dataset.valor;

    const entrada = prompt(
      `Valor efetivo da venda (deixe em branco para usar o valor cheio: R$ ${Number(valorCheio).toFixed(2)}):`,
      "",
    );

    if (entrada === null) return; // cancelado

    const corpo = {};
    if (entrada.trim() !== "") {
      const numero = Number(entrada.replace(",", "."));
      if (Number.isNaN(numero) || numero < 0) {
        alert("Valor inválido.");
        return;
      }
      corpo.valor_efetivo = numero;
    }

    const resposta = await fetch(`/reservas/${btn.dataset.id}/completar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });

    if (resposta.ok) {
      window.location.reload();
    } else {
      const erro = await resposta.json().catch(() => ({}));
      alert(erro.detail || "Erro ao efetivar a reserva.");
    }
  });
});

// ---- Ajustar valor efetivo (ex: promoção aplicada após a venda concluída) ----
document.querySelectorAll(".edit-value-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const entrada = prompt("Novo valor efetivo da venda (R$):", "");

    if (entrada === null) return; // cancelado

    const numero = Number(entrada.replace(",", "."));
    if (entrada.trim() === "" || Number.isNaN(numero) || numero < 0) {
      alert("Valor inválido.");
      return;
    }

    const resposta = await fetch(`/reservas/${btn.dataset.id}/valor-efetivo`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ valor_efetivo: numero }),
    });

    if (resposta.ok) {
      window.location.reload();
    } else {
      const erro = await resposta.json().catch(() => ({}));
      alert(erro.detail || "Erro ao ajustar o valor efetivo.");
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
