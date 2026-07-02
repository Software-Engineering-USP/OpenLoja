function pagina_criarconta() {
    window.location.href = "/criarcontahtml";
}

function pagina_login() {
    window.location.href = "/";
}

async function criarconta(){
    const dados = {
	usuario: document.getElementById("usuario").value,
	senha: document.getElementById("senha").value,
    };

    const confirma_senha = document.getElementById("confirma_senha").value;

    if(dados.senha !== confirma_senha){
	alert("Senhas diferem!");
	return;
    }

    // PRECISA ATUALIZAR COM A ROTA DE CRIAR USUARIOS
    const resposta = await fetch('/ROTA', {
	method: 'POST',
	headers: {
	    'Content-Type': 'application/json'
	},
	body: JSON.stringify(dados)
    });

    
    if (resposta.ok){
	const resultado = await resposta.json();
	alert("Usuário " + resultado.usuario + " criado!");
    } else {
	alert("Usuário já existente, tente outro!");
    }
}

async function login() {

    const usuario = document.getElementById('usuario').value;
    const senha = document.getElementById('senha').value;
    
    // ATUALIZAR COM A ROTA DE LOGIN
    const resposta = await fetch('/ROTA?usuario=' + usuario + '&senha=' + senha, {
	method: 'POST'
    });


    if (resposta.ok) {
	
	// ATUALIZAR COM A ROTA PARA A HOME DO VENDEDOR
	window.location.href = "/ROTA";
    } else {
	alert("Usuário ou senha incorretos.");
    }

}

