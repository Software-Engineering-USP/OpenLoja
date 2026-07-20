const login = document.getElementById("login-form");
const register = document.getElementById("register-form");
const modal = document.getElementById("auth-modal");

// Abre a tela de cadastro
document.getElementById("show-register").onclick = function(e){

    e.preventDefault();

    login.style.display = "none";
    register.style.display = "block";

};

// Volta para a tela de login
document.getElementById("show-login").onclick = function(e){

    e.preventDefault();

    register.style.display = "none";
    login.style.display = "block";

};

// Fecha o modal
document.getElementById("close-modal").onclick = function(){

    modal.style.display = "none";

};

// Abre o modal ao clicar em "Entrar"
document.getElementById("open-login").onclick = function(){

    modal.style.display = "flex";

    login.style.display = "block";
    register.style.display = "none";

};

// Mostra o modal apenas na primeira visita
if(!localStorage.getItem("visited")){

    modal.style.display = "flex";
    localStorage.setItem("visited","true");

}else{

    modal.style.display = "none";

}


const cartOverlay = document.getElementById("cart-sidebar-overlay");

document.querySelector('a[href="#cart"]').onclick = function(e){

    e.preventDefault();

    cartOverlay.classList.add("active");

};

document.getElementById("close-cart").onclick = function(){

    cartOverlay.classList.remove("active");

};

cartOverlay.onclick = function(e){

    if(e.target === cartOverlay){

        cartOverlay.classList.remove("active");

    }

};