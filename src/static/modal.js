const openCart = document.getElementById("open-cart");
const cartOverlay = document.getElementById("cart-sidebar-overlay");
const closeCart = document.getElementById("close-cart");

function mostrarCarrinho(itens){

    const container = document.getElementById("cart-items");

    container.innerHTML = "";

    itens.forEach(item => {

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

async function carregarCarrinho(){

    const response = await fetch("/carrinho");

    if(!response.ok){
        console.error("Erro ao carregar carrinho");
        return;
    }

    const carrinho = await response.json();
    document.getElementById("cart-total").textContent =`R$ ${carrinho.total.toFixed(2)}`;
    mostrarCarrinho(carrinho.itens);

}

openCart.addEventListener("click", async function (e) {
    e.preventDefault();
    cartOverlay.classList.add("active");
    await carregarCarrinho();
});

closeCart.addEventListener("click", function () {
    cartOverlay.classList.remove("active");
});

cartOverlay.addEventListener("click", function (e) {
        if (e.target === cartOverlay) {
            cartOverlay.classList.remove("active");
        }
});
