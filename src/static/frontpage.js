function pagina_criarconta() {
    window.location.href = "/paginacria";
}

function pagina_login() {
    window.location.href = "/paginalogin";
}

function atualizarCarrinho(quantidade) {
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

    const avaliacoesResponse = await fetch( `/produtos/${id}/avaliacoes` );
    const avaliacoes = await avaliacoesResponse.json();

    let avaliacoesHTML = "";

    if (avaliacoes.length === 0) {
	avaliacoesHTML = `<p>Nenhuma avaliação ainda.</p> `;
    } else {

	avaliacoesHTML = avaliacoes.map(avaliacao => {

	    const horario = String(avaliacao.horario).padStart(4, "0");
	    const hora = horario.slice(0, 2);
	    const minuto = horario.slice(2, 4);
	    
	    return `

            <div class="avaliacao">
                <h3>
                    ${avaliacao.cliente}
                </h3>

                <p>
                    Nota: ${avaliacao.nota}/5
                </p>
                
                <br>
                <p>
                    ${avaliacao.texto}
                </p>
                <br>
 
                <small>
                    ${avaliacao.dia}/${avaliacao.mes}/${avaliacao.ano} às ${hora}:${minuto}
                </small>
            </div>

        `;

	}).join("");
    }

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

        <section class="avaliacoes">

            <h2>Avaliações</h2>

            <div class="lista-avaliacoes">
                ${avaliacoesHTML}
            </div>

            <div class="nova-avaliacao">

                <h2>Faça sua Avaliação!</h2>

                <label for="nota">
                    Nota
                </label> 

                <select id="nota">
                    <option value="5">5 - Excelente</option>
                    <option value="4">4 - Muito bom</option>
                    <option value="3">3 - Bom</option>
                    <option value="2">2 - Ruim</option>
                    <option value="1">1 - Muito ruim</option>
                    <option value="0">0 - Péssimo</option>
                </select>


                <label for="texto-avaliacao">
                    Sua avaliação
                </label>

                <textarea
                   id="texto-avaliacao"
                   placeholder="Escreva sua avaliação..."
                ></textarea>


                <button id="enviar-avaliacao">
                    Enviar avaliação
                </button>
            </div>

        </section>

    `;


    document
        .getElementById("voltar-catalogo")
        .onclick = voltarCatalogo;

    document.getElementById("enviar-avaliacao").onclick = async function() {

        const nota = Number(
            document.getElementById("nota").value
        );

        const texto =
            document.getElementById("texto-avaliacao").value;


        const response = await fetch(
            `/produtos/${produto.id}/avaliacoes`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    nota: nota,
                    texto: texto
                })
            }
        );


        if (response.ok) {
            alert("Avaliação enviada!");
        } else {
            alert("Erro ao enviar avaliação.");
        }
    }

}

// implementação de filtragem por tags
const tagButtons = document.querySelectorAll(".tag-btn");
const products = document.querySelectorAll(".product-card");

tagButtons.forEach(button => {
    button.addEventListener("click", () => {

        tagButtons.forEach(btn => btn.classList.remove("active"));
        button.classList.add("active");

        const selectedTag = button.dataset.tag;

        products.forEach(product => {
	    const productTags = product.dataset.tag.split(",").map(tag => tag.trim().toLowerCase());
	    if (selectedTag === "all" || productTags.includes(selectedTag)) {
		product.style.display = "";
	    } else {
		product.style.display = "none";
	    }

        });

    });

});
