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