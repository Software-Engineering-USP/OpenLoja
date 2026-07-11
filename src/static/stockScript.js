// ---- Busca em tempo real ----
document.getElementById("stock-search").addEventListener("input", (e) => {
  const termo = e.target.value.toLowerCase();
  document
    .querySelectorAll("#stock-table tbody tr[data-nome]")
    .forEach((linha) => {
      const nome = linha.getAttribute("data-nome");
      linha.style.display = nome.includes(termo) ? "" : "none";
    });
});

// ---- Modal (adicionar / editar) ----
const modal = document.getElementById("product-modal");
const modalTitle = document.getElementById("modal-title");
const modalId = document.getElementById("modal-produto-id");
const modalNome = document.getElementById("modal-nome");
const modalQuantidade = document.getElementById("modal-quantidade");
const modalPreco = document.getElementById("modal-preco");

function abrirModal({ id = "", nome = "", quantidade = "", preco = "" } = {}) {
  modalTitle.textContent = id ? "Edit Product" : "Add Product";
  modalId.value = id;
  modalNome.value = nome;
  modalQuantidade.value = quantidade;
  modalPreco.value = preco;
  modal.classList.remove("hidden");
}

function fecharModal() {
  modal.classList.add("hidden");
}

document
  .getElementById("add-product-btn")
  .addEventListener("click", () => abrirModal());
document.getElementById("modal-cancel").addEventListener("click", fecharModal);

document.querySelectorAll(".edit-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const linha = btn.closest("tr");
    abrirModal({
      id: btn.dataset.id,
      nome: linha.querySelector(".product-name").textContent,
      quantidade: linha.children[1].textContent.trim(),
      preco: linha.children[2].textContent.replace("$", "").trim(),
    });
  });
});

document.getElementById("modal-save").addEventListener("click", async () => {
  const dados = {
    id: modalId.value || null,
    nome: modalNome.value,
    quantidade_em_estoque: Number(modalQuantidade.value),
    preco: Number(modalPreco.value),
  };

  // ATUALIZAR COM A ROTA DE CRIAR/EDITAR PRODUTO
  const resposta = await fetch(dados.id ? `/ROTA/${dados.id}` : "/ROTA", {
    method: dados.id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });

  if (resposta.ok) {
    window.location.reload();
  } else {
    alert("Erro ao salvar o produto.");
  }
});

// ---- Deletar produto ----
document.querySelectorAll(".delete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Tem certeza que deseja remover este produto?")) return;

    // ATUALIZAR COM A ROTA DE DELETAR PRODUTO
    const resposta = await fetch(`/ROTA/${btn.dataset.id}`, {
      method: "DELETE",
    });

    if (resposta.ok) {
      btn.closest("tr").remove();
    } else {
      alert("Erro ao remover o produto.");
    }
  });
});
