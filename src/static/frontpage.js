function pagina_criarconta() {
    window.location.href = "/paginacria";
}

function pagina_login() {
    window.location.href = "/paginalogin";
}

function atualizarCarrinho(quantidade) {
    console.log("atualizarCarrinho");
    const badge = document.getElementById("cart-count");

    if (quantidade === 0) {
        badge.style.display = "none";
    } else {
        badge.style.display = "inline-flex";
        badge.textContent = quantidade;
    }
}

const linksProduto = document.querySelectorAll(
    ".product-image, .product-title-link"
);


linksProduto.forEach(link => {

    link.addEventListener("click", async function(e){

        e.preventDefault();

        const produtoId = this.dataset.id;

        abrirProduto(produtoId);

    });

});

function voltarCatalogo(){

    document.getElementById("product-view")
        .style.display = "none";


    document.getElementById("catalog-view")
        .style.display = "block";

}

async function abrirProduto(id){

    const response = await fetch(`/produtos/${id}`);

    const produto = await response.json();

    console.log(produto);

    document.getElementById("catalog-view")
        .style.display = "none";


    const view = document.getElementById("product-view");

    view.style.display = "block";


    view.innerHTML = `

        <button id="voltar-catalogo">
            ← Voltar
        </button>


        <section class="product-detail">

            <div class="product-detail-image">

                <img 
                    src="/static/${produto.imagem}"
                    alt="${produto.nome}"
                >

            </div>


            <div class="product-detail-info">

                <h1>
                    ${produto.nome}
                </h1>


                <p class="product-detail-price">
                    R$ ${produto.preco}
                </p>


                <p>
                    Disponível:
                    ${produto.quantidade_em_estoque}
                </p>


                <label>
                    Quantidade
                </label>


                <input
                    id="quantidade"
                    type="number"
                    value="1"
                    min="1"
                    max="${produto.quantidade_em_estoque}"
                >


                <button
                    class="buy-btn"
                    data-id="${produto.id}"
                    data-nome="${produto.nome}"
                    data-preco="${produto.preco}"
                    data-imagem="${produto.imagem}">
                    
                    Adicionar ao Carrinho

                </button>


            </div>

        </section>

    `;


    document
        .getElementById("voltar-catalogo")
        .onclick = voltarCatalogo;

}
