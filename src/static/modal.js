// Variáveis do carrinho
const openCart = document.getElementById("open-cart");
const cartOverlay = document.getElementById("cart-sidebar-overlay");
const closeCart = document.getElementById("close-cart");
const checkoutBtn = document.querySelector(".checkout-btn");

// Variável com os botões que adicionam no carrinho
const botoes = document.querySelectorAll(".buy-btn");

// Função auxiliar para atulizar o HTML e mostrar o carrinho ao clicar
function mostrarCarrinho(itens) {
  const container = document.getElementById("cart-items");

    container.innerHTML = "";
    
  itens.forEach((item) => {
    container.innerHTML += `
            <div class="cart-item">
                
                <img src="/static/${item.imagem}" alt="${item.nome}">

                <div class="cart-info">
                    <h4>${item.nome}</h4>

                    <span>Quantidade: ${item.quantidade}</span>

                    <span>R$ ${item.preco.toFixed(2)}</span>
                </div>

                <button
                    class="remove-item"
                    data-id="${item.id}">
                    <i class="fas fa-trash"></i>
                </button>

            </div>
        `;
  });
}

document.addEventListener("click", async function (e) {
  const botao = e.target.closest(".remove-item");
  if (!botao) return;

  const produtoId = botao.dataset.id;

  if (usuarioLogado) {
    await fetch(`/carrinho/item/${produtoId}`, {
      method: "DELETE",
    });
  } else {
    let carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];

    carrinho = carrinho.filter((item) => item.id != produtoId);

    localStorage.setItem("carrinho", JSON.stringify(carrinho));
  }

  await carregarCarrinho();
});

// Função que carrega o carrinho do banco de dados ou do localStorage
async function carregarCarrinho() {
  if (usuarioLogado) {
    const response = await fetch("/carrinho");

    if (!response.ok) {
      console.error("Erro ao carregar carrinho");
      return;
    }

    const carrinho = await response.json();

    document.getElementById("cart-total").textContent =
      `R$ ${carrinho.total.toFixed(2)}`;

    mostrarCarrinho(carrinho.itens);

    const quantidade = carrinho.itens.reduce(
      (soma, item) => soma + item.quantidade,
      0,
    );

    atualizarCarrinho(quantidade);
  } else {
    const carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];

    mostrarCarrinho(carrinho);

    const total = carrinho.reduce(
      (soma, item) => soma + item.preco * item.quantidade,
      0,
    );

    document.getElementById("cart-total").textContent =
      `R$ ${total.toFixed(2)}`;

    const quantidade = carrinho.reduce(
      (soma, item) => soma + item.quantidade,
      0,
    );

    atualizarCarrinho(quantidade);
  }
}

async function sincronizarCarrinho() {
  const carrinhoLocal = JSON.parse(localStorage.getItem("carrinho")) || [];

  if (carrinhoLocal.length === 0) return;

  await fetch("/carrinho/sincronizar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(
      carrinhoLocal.map((item) => ({
        produto_id: item.id,
        quantidade: item.quantidade,
      })),
    ),
  });

  localStorage.removeItem("carrinho");
}

// Função para abrir a aba do carrinho
openCart.addEventListener("click", async function (e) {
  e.preventDefault();
  cartOverlay.classList.add("active");
  await carregarCarrinho();
});

// Função para fechar a aba do carrinho
closeCart.addEventListener("click", function () {
  cartOverlay.classList.remove("active");
});

// Função para fechar a aba do carrinho se clicar fora do overlay
cartOverlay.addEventListener("click", function (e) {
  if (e.target === cartOverlay) {
    cartOverlay.classList.remove("active");
  }
});

// Número de WhatsApp da loja, com código do país e DDD (ex: 55 11 999999999)
const NUMERO_WHATSAPP_LOJA = WHATSAPP_LOJA.replace(/\D/g, "");

// Monta o texto do resumo do pedido para enviar no WhatsApp
function montarResumoWhatsApp(dados) {
  let mensagem = `Olá! Gostaria de confirmar meu pedido #${dados.reserva_id}:\n\n`;

  dados.itens.forEach((item) => {
    mensagem += `• ${item.quantidade}x ${item.nome} - R$ ${item.preco.toFixed(2)}\n`;
  });

  mensagem += `\nTotal: R$ ${dados.total.toFixed(2)}`;

  return mensagem;
}

checkoutBtn.addEventListener("click", async function () {
  if (!usuarioLogado) {
    window.location.href = "/paginalogin";
    return;
  }

  // Abre a aba do WhatsApp já na hora do clique (antes do await),
  // para o navegador não bloquear o pop-up. A URL é preenchida depois.
  const abaWhatsApp = window.open("", "_blank");

  // aqui você coloca a página de pagamento
  try {
    const resposta = await fetch("/checkout", {
      method: "POST",
    });

    if (resposta.ok) {
      const dados = await resposta.json();

      const mensagem = montarResumoWhatsApp(dados);
      const urlWhatsApp = `https://wa.me/${NUMERO_WHATSAPP_LOJA}?text=${encodeURIComponent(mensagem)}`;

      if (abaWhatsApp) {
        abaWhatsApp.location.href = urlWhatsApp;
      } else {
        // caso o pop-up tenha sido bloqueado mesmo assim
        window.location.href = urlWhatsApp;
      }

      window.location.href = "/homeCliente";
    } else {
      if (abaWhatsApp) abaWhatsApp.close();
      const erro = await resposta.json();
      alert(
        "Erro ao finalizar compra: " + (erro.detail || "Erro desconhecido"),
      );
    }
  } catch (e) {
    if (abaWhatsApp) abaWhatsApp.close();
    console.error(e);
    alert("Ocorreu um erro ao tentar processar a compra.");
  }
});

// Função para adicionar produtos no carrinho
document.addEventListener("click", async function (e) {
  const botao = e.target.closest(".buy-btn");

  if (!botao) return;

  const produtoId = botao.dataset.id;
  const quantidadeId = document.getElementById("quantidade");
  const quantidade = Number(quantidadeId?.value) || 1;

  if (usuarioLogado) {
    await fetch(
      `/carrinho/add?produto_id=${produtoId}&quantidade=${quantidade}`,
      {
        method: "POST",
      },
    );

    await carregarCarrinho();
  } else {
    adicionarCarrinhoLocal(botao);
    await carregarCarrinho();
  }

  if (quantidadeId) {
    quantidadeId.value = 1;
  }
});

// Função auxiliar para adicionar no carrinho local se o usuário estiver deslogado
function adicionarCarrinhoLocal(botao) {
  const produto = {
    id: Number(botao.dataset.id),
    nome: botao.dataset.nome,
    preco: Number(botao.dataset.preco),
    imagem: botao.dataset.imagem,
    quantidade: Number(document.getElementById("quantidade")?.value) || 1,
  };

  let carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];
  const existente = carrinho.find((p) => p.id == produto.id);

  if (existente) {
    existente.quantidade += produto.quantidade;
  } else {
    carrinho.push(produto);
  }

  localStorage.setItem("carrinho", JSON.stringify(carrinho));

  const quantidade = carrinho.reduce((soma, item) => soma + item.quantidade, 0);
  atualizarCarrinho(quantidade);
}

window.addEventListener("DOMContentLoaded", async () => {
  await carregarCarrinho();
});
