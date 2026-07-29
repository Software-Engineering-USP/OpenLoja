const form = document.getElementById("settings-form");

const logoInput = document.getElementById("logo");
const bannerInput = document.getElementById("banner");

const logoPreview = document.getElementById("logo-preview");
const bannerPreview = document.getElementById("banner-preview");

window.addEventListener("DOMContentLoaded", async () => {

    const resposta = await fetch("/loja");

    if (!resposta.ok) return;

    const loja = await resposta.json();

    document.getElementById("nome-loja").value = loja.nome || "";
    document.getElementById("slogan").value = loja.slogan || "";
    document.getElementById("descricao").value = loja.descricao || "";

    document.getElementById("cor-primaria").value = loja.cor_primaria || "#232978";
    document.getElementById("cor-secundaria").value = loja.cor_secundaria || "#ffffff";
    document.getElementById("cor-destaque").value = loja.cor_destaque || "#0d6efd";

    document.getElementById("email").value = loja.email || "";
    document.getElementById("telefone").value = loja.telefone || "";
    document.getElementById("whatsapp").value = loja.whatsapp || "";
    document.getElementById("endereco").value = loja.endereco || "";

    document.getElementById("instagram").value = loja.instagram || "";
    document.getElementById("facebook").value = loja.facebook || "";

    document.getElementById("horario").value = loja.horario || "";
    document.getElementById("trocas").value = loja.trocas || "";
    document.getElementById("devolucao").value = loja.devolucao || "";

});

function mostrarPreview(input, preview){

    const arquivo = input.files[0];

    if(!arquivo){
        preview.style.display = "none";
        preview.src = "";
        return;
    }

    preview.src = URL.createObjectURL(arquivo);
    preview.style.display = "block";

}

logoInput.addEventListener("change", () =>
    mostrarPreview(logoInput, logoPreview)
);

bannerInput.addEventListener("change", () =>
    mostrarPreview(bannerInput, bannerPreview)
);

form.addEventListener("submit", async (e)=>{

    e.preventDefault();

    const dados = {
        nome: document.getElementById("nome-loja").value,
        slogan: document.getElementById("slogan").value,
        descricao: document.getElementById("descricao").value,

        cor_primaria: document.getElementById("cor-primaria").value,
        cor_secundaria: document.getElementById("cor-secundaria").value,
        cor_destaque: document.getElementById("cor-destaque").value,

        email: document.getElementById("email").value,
        telefone: document.getElementById("telefone").value,
        whatsapp: document.getElementById("whatsapp").value,
        endereco: document.getElementById("endereco").value,

        instagram: document.getElementById("instagram").value,
        facebook: document.getElementById("facebook").value,

        horario: document.getElementById("horario").value,
        trocas: document.getElementById("trocas").value,
        devolucao: document.getElementById("devolucao").value
    };

    const resposta = await fetch("/loja",{
        method:"PUT",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify(dados)
    });

    if(!resposta.ok){
        alert("Erro ao salvar.");
        return;
    }

    if(logoInput.files.length){

        const formLogo = new FormData();
        formLogo.append("logo",logoInput.files[0]);

        await fetch("/loja/logo",{
            method:"POST",
            body:formLogo
        });

    }

    if(bannerInput.files.length){

        const formBanner = new FormData();
        formBanner.append("banner",bannerInput.files[0]);

        await fetch("/loja/banner",{
            method:"POST",
            body:formBanner
        });

    }

    alert("Configurações salvas com sucesso.");

});