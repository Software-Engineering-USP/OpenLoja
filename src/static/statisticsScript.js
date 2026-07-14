// ATUALIZAR COM A ROTA QUE RETORNA OS DADOS HISTÓRICOS DE RECEITA
// Espera-se um JSON no formato: { "labels": ["Jan", "Fev", ...], "valores": [1200, 1500, ...] }
async function carregarGraficoReceita() {
  let labels = [];
  let valores = [];

  try {
    const resposta = await fetch("/ROTA/receita-mensal");
    if (resposta.ok) {
      const dados = await resposta.json();
      labels = dados.labels;
      valores = dados.valores;
    }
  } catch (erro) {
    console.warn("Não foi possível carregar os dados de receita:", erro);
  }

  const ctx = document.getElementById("revenue-chart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Receita ($)",
          data: valores,
          borderColor: "#1d4ed8",
          backgroundColor: "rgba(29, 78, 216, 0.1)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

carregarGraficoReceita();
