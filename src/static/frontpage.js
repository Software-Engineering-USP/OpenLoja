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

const inputBusca = document.getElementById("js-search-input");
const mensagem = document.getElementById("no-results");

if (inputBusca) {

    inputBusca.addEventListener("input", function () {

        const texto = this.value.toLowerCase().trim();

        let encontrados = 0;

        document.querySelectorAll(".product-card").forEach(card => {

            const nome = card.querySelector(".product-title")
                .textContent
                .toLowerCase();

            const categoria = (card.dataset.categoria || "").toLowerCase();

            const descricao = (card.dataset.descricao || "").toLowerCase();

            const tags = (card.dataset.tag || "")
                .toLowerCase()
                .split(",")
                .map(tag => tag.trim());

            if (
                nome.includes(texto) ||
                categoria.includes(texto) ||
                descricao.includes(texto) ||
                tags.some(tag => tag.includes(texto))
            ) {
                card.style.display = "";
                encontrados++;
            } else {
                card.style.display = "none";
            }

        });

        mensagem.style.display = encontrados ? "none" : "block";

    });

}

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
                    src="${produto.imagem}"
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

                <p class="product-detail-category">
                    ${produto.categoria}
                </p>

                <p class="product-detail-description">
                    ${produto.descricao}
                </p>

                <p class="product-detail-tags">
                    ${produto.tag}
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
