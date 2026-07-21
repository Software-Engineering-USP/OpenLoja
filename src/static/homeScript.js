function pagina_criarconta() {
    window.location.href = "/paginacria";
}

function pagina_login() {
    window.location.href = "/paginalogin";
}

async function criarconta() {
    const dados = {
	nome: document.getElementById("usuario").value,
	senha: document.getElementById("senha").value,
    };

    const confirma_senha = document.getElementById("confirma_senha").value;

    if (dados.senha.length < 4) {
	alert("Senha precisa ter pelo menos 4 caracteres!");
	return;
    }

    if (dados.senha !== confirma_senha) {
	alert("Senhas diferem!");
	return;
    }

    const resposta = await fetch("/criarusuario", {
	method: "POST",
	headers: {
	    "Content-Type": "application/json",
	},
	body: JSON.stringify(dados),
    });

    if (resposta.ok) {
	const resultado = await resposta.json();
	alert("Usuário " + resultado.usuario + " criado!");
	window.location.href = "/paginalogin";
    } else {
	alert("Usuário já existente, tente outro!");
    }
}

async function login() {
    const nome = document.getElementById("usuario").value;
    const senha = document.getElementById("senha").value;

    const resposta = await fetch(
	"/login?nome=" +
	    encodeURIComponent(nome) +
	    "&senha=" +
	    encodeURIComponent(senha),
	{ method: "POST" },
    );

    if (resposta.ok) {
	const data = await resposta.json();
	window.location.href = "/"
    } else {
	alert("Usuário ou senha incorretos.");
    }
}
