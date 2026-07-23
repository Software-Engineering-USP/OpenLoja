const openCart = document.getElementById("open-cart");
const cartOverlay = document.getElementById("cart-sidebar-overlay");
const closeCart = document.getElementById("close-cart");

openCart.addEventListener("click", function (e) {
    e.preventDefault();
    cartOverlay.classList.add("active");
});

closeCart.addEventListener("click", function () {
    cartOverlay.classList.remove("active");
});

cartOverlay.addEventListener("click", function (e) {
        if (e.target === cartOverlay) {
            cartOverlay.classList.remove("active");
        }
});
