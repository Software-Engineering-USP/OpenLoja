
// Variáveis do carrinho
const openCart = document.getElementById("open-cart");
const cartOverlay = document.getElementById("cart-sidebar-overlay");
const closeCart = document.getElementById("close-cart");

// Variável com os botões que adicionam no carrinho
const botoes = document.querySelectorAll(".buy-btn");

// Função auxiliar para atulizar o HTML e mostrar o carrinho ao clicar 
function mostrarCarrinho(itens){

    const container = document.getElementById("cart-items");

    container.innerHTML = "";

    itens.forEach(item => {

        container.innerHTML += `
            <div class="cart-item">

                <img src="${item.imagem}" alt="${item.nome}">

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
            method: "DELETE"
        });

    } else {

        let carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];

        carrinho = carrinho.filter(item => item.id != produtoId);

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
            0
        );

        atualizarCarrinho(quantidade);

    } else {

        const carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];

        mostrarCarrinho(carrinho);

        const total = carrinho.reduce(
            (soma, item) => soma + item.preco * item.quantidade,
            0
        );

        document.getElementById("cart-total").textContent =
            `R$ ${total.toFixed(2)}`;

        const quantidade = carrinho.reduce(
            (soma, item) => soma + item.quantidade,
            0
        );

        atualizarCarrinho(quantidade);
    }
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

// Função para adicionar produtos no carrinho
botoes.forEach(botao => {
    botao.addEventListener("click", async function(){
	const produtoId = this.dataset.id;

	if(usuarioLogado){
	    await fetch(
            `/carrinho/add?produto_id=${produtoId}&quantidade=1`,
            {
                method: "POST"
            }
        );

        await carregarCarrinho();
	}

	else{
	    adicionarCarrinhoLocal(this);
        await carregarCarrinho();
	}
    });
});
    
// Função auxiliar para adicionar no carrinho local se o usuário estiver deslogado
function adicionarCarrinhoLocal(botao){
    const card = botao.closest(".product-card");

    const produto = {
	id: Number(botao.dataset.id),
	nome: card.querySelector(".product-title").textContent,
	preco: Number(card.querySelector(".product-price")
		      .textContent
		      .replace("R$", "")
		      .replace(",", ".")
		      .trim()
		     ),
	imagem: card.querySelector("img").src,
	quantidade: 1
    };

    let carrinho = JSON.parse(localStorage.getItem("carrinho")) || [];
    const existente = carrinho.find(p => p.id == produto.id);

    if(existente){
	existente.quantidade++;
    }
    else{
	carrinho.push(produto);
    }

    localStorage.setItem("carrinho", JSON.stringify(carrinho));
    atualizarCarrinho();
}

window.addEventListener("DOMContentLoaded", async () => {
    await carregarCarrinho();
    atualizarCarrinho();
});
