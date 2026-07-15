// ---- Editar produto ----
const modal = document.getElementById("product-modal");
const modalId = document.getElementById("modal-produto-id");
const modalNome = document.getElementById("modal-nome");
const modalQuantidade = document.getElementById("modal-quantidade");
const modalPreco = document.getElementById("modal-preco");

const editBtn = document.getElementById("edit-product-btn");

editBtn.addEventListener("click", () => {
  modalId.value = editBtn.dataset.id;
  modalNome.value = editBtn.dataset.nome;
  modalQuantidade.value = editBtn.dataset.quantidade;
  modalPreco.value = editBtn.dataset.preco;
  modal.classList.remove("hidden");
});

document.getElementById("modal-cancel").addEventListener("click", () => {
  modal.classList.add("hidden");
});

document.getElementById("modal-save").addEventListener("click", async () => {
  const dados = {
    nome: modalNome.value,
    quantidade_em_estoque: Number(modalQuantidade.value),
    preco: Number(modalPreco.value),
  };

  // ATUALIZAR COM A ROTA DE EDITAR PRODUTO
  const resposta = await fetch(`/ROTA/${modalId.value}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });

  if (resposta.ok) {
    window.location.reload();
  } else {
    alert("Erro ao salvar o produto.");
  }
});

// ---- Remover produto ----
document
  .getElementById("delete-product-btn")
  .addEventListener("click", async () => {
    if (!confirm("Tem certeza que deseja remover este produto?")) return;

    const produtoId = document.getElementById("delete-product-btn").dataset.id;

    // ATUALIZAR COM A ROTA DE DELETAR PRODUTO
    const resposta = await fetch(`/produtos/${produtoId}`, {
      method: "DELETE",
    });

    if (resposta.ok) {
      window.location.href = "/stock";
    } else {
      alert("Erro ao remover o produto.");
    }
  });
