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
const inputImagem = document.getElementById("modal-imagem");
const preview = document.getElementById("modal-preview");

function abrirModal({ id = "", nome = "", quantidade = "", preco = "" } = {}) {
    modalTitle.textContent = id ? "Editar Produto" : "Adicionar Produto";

    modalId.value = id;
    modalNome.value = nome;
    modalQuantidade.value = quantidade;
    modalPreco.value = preco;

    inputImagem.value = "";
    preview.style.display = "none";
    preview.src = "";

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
        nome: modalNome.value,
        quantidade_em_estoque: Number(modalQuantidade.value),
        preco: Number(modalPreco.value),
    };

    const resposta = await fetch(
        modalId.value ? `/produtos/${modalId.value}` : "/produtos",
        {
            method: modalId.value ? "PUT" : "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(dados)
        }
    );

    if (!resposta.ok) {
        alert("Erro ao salvar o produto.");
        return;
    }

    const produto = await resposta.json();

    
    const id = modalId.value || produto.id;

    if (inputImagem.files.length > 0) {
        const imagemData = new FormData();
        imagemData.append("imagem", inputImagem.files[0]);

        await fetch(`/produtos/${id}/imagem`, {
            method: "POST",
            body: imagemData,
        });
    }

    window.location.reload();
});

inputImagem.addEventListener("change", () => {
    const arquivo = inputImagem.files[0];

    if (!arquivo) {
        preview.style.display = "none";
        return;
    }

    preview.src = URL.createObjectURL(arquivo);
    preview.style.display = "block";
});

// ---- Deletar produto ----
document.querySelectorAll(".delete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Tem certeza que deseja remover este produto?")) return;

    // ATUALIZAR COM A ROTA DE DELETAR PRODUTO
    const resposta = await fetch(`/produtos/${btn.dataset.id}`, {
      method: "DELETE",
    });

    if (resposta.ok) {
      btn.closest("tr").remove();
    } else {
      alert("Erro ao remover o produto.");
    }
  });
});
