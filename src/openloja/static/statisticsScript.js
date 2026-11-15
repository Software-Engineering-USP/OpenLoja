// Página de estatísticas: gráfico mensal, detalhes do mês, vendas do dia
// e padrões de venda (dia da semana / horário). Dados vindos de /estatisticas/*.

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const numero = new Intl.NumberFormat("pt-BR");
const NOMES_METRICA = { receita: "Receita", vendas: "Vendas", ticket_medio: "Ticket médio" };

const estado = {
  meses: [],
  mesSelecionado: null, // "AAAA-MM"
  detalheMes: null,
  padroes: null,
  metricaMeses: "receita",
  periodoMeses: 12,
  metricaDias: "receita",
  metricaPadroes: "receita",
  periodoPadroes: 90,
};
const graficos = {};

// ---------------------------------------------------------------------
// utilitários
// ---------------------------------------------------------------------

function cssVar(nome, padrao) {
  const valor = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return valor || padrao;
}

function comAlpha(cor, alpha) {
  // aceita #rgb / #rrggbb; outras notações ficam sem transparência
  const hex = cor.replace("#", "");
  if (!/^[0-9a-f]{3}([0-9a-f]{3})?$/i.test(hex)) return cor;
  const cheio = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(cheio.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function formatar(metrica, valor) {
  return metrica === "vendas" || metrica === "itens" || metrica === "clientes"
    ? numero.format(valor)
    : moeda.format(valor);
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function dataIso(d) {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

function dataPorExtenso(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

async function buscar(url) {
  const resposta = await fetch(url);
  if (!resposta.ok) throw new Error(`${url}: ${resposta.status}`);
  return resposta.json();
}

function ligarSegmentado(grupo, aoMudar) {
  const caixa = document.querySelector(`.segmented[data-grupo="${grupo}"]`);
  if (!caixa) return;
  caixa.addEventListener("click", (evento) => {
    const botao = evento.target.closest("button[data-valor]");
    if (!botao || botao.classList.contains("ativo")) return;
    caixa.querySelectorAll("button").forEach((b) => b.classList.toggle("ativo", b === botao));
    aoMudar(botao.dataset.valor);
  });
}

// gráfico de barras de uma série só; destaque opcional de uma barra
function graficoBarras(id, { labels, valores, metrica, destaque = -1, aoClicar, titulos }) {
  const canvas = document.getElementById(id);
  if (!canvas || typeof Chart === "undefined") return;

  const primaria = cssVar("--cor-primaria", "#232978");
  const cores = valores.map((_, i) =>
    destaque === -1 || i === destaque ? primaria : comAlpha(primaria, 0.35)
  );

  const dados = {
    labels,
    datasets: [
      {
        label: NOMES_METRICA[metrica],
        data: valores,
        backgroundColor: cores,
        hoverBackgroundColor: primaria,
        borderRadius: 4,
        borderSkipped: "bottom",
        maxBarThickness: 36,
      },
    ],
  };

  if (graficos[id]) {
    graficos[id].data = dados;
    graficos[id].$metrica = metrica;
    graficos[id].update();
    return;
  }

  graficos[id] = new Chart(canvas, {
    type: "bar",
    data: dados,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      onClick: (_evento, elementos) => {
        if (aoClicar && elementos.length) aoClicar(elementos[0].index);
      },
      onHover: (evento, elementos) => {
        if (aoClicar) evento.native.target.style.cursor = elementos.length ? "pointer" : "default";
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (itens) => (titulos ? titulos(itens[0].dataIndex) : itens[0].label),
            label: (item) =>
              ` ${NOMES_METRICA[graficos[id].$metrica]}: ${formatar(graficos[id].$metrica, item.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#6b7280", autoSkip: true, maxRotation: 0 } },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: "#eceef6" },
          ticks: {
            color: "#6b7280",
            precision: 0,
            callback: (v) =>
              graficos[id]?.$metrica === "vendas"
                ? numero.format(v)
                : moeda.format(v).replace(/,00$/, ""),
          },
        },
      },
    },
  });
  graficos[id].$metrica = metrica;
}

// ---------------------------------------------------------------------
// desempenho por mês
// ---------------------------------------------------------------------

function mesesVisiveis() {
  return estado.periodoMeses ? estado.meses.slice(-estado.periodoMeses) : estado.meses;
}

function desenharMeses() {
  const meses = mesesVisiveis();
  graficoBarras("months-chart", {
    labels: meses.map((m) => m.label),
    valores: meses.map((m) => m[estado.metricaMeses]),
    metrica: estado.metricaMeses,
    destaque: meses.findIndex((m) => m.chave === estado.mesSelecionado),
    aoClicar: (i) => selecionarMes(meses[i].chave, { rolar: true }),
    titulos: (i) => `${meses[i].label} · ${numero.format(meses[i].vendas)} venda(s)`,
  });
}

function preencherSeletorMes() {
  const seletor = document.getElementById("seletor-mes");
  seletor.innerHTML = [...estado.meses]
    .reverse()
    .map((m) => `<option value="${m.chave}">${escapar(m.label)}</option>`)
    .join("");
}

// ---------------------------------------------------------------------
// detalhes do mês
// ---------------------------------------------------------------------

async function selecionarMes(chave, { rolar = false } = {}) {
  estado.mesSelecionado = chave;
  document.getElementById("seletor-mes").value = chave;

  const indice = estado.meses.findIndex((m) => m.chave === chave);
  document.getElementById("mes-anterior").disabled = indice <= 0;
  document.getElementById("mes-seguinte").disabled = indice >= estado.meses.length - 1;

  desenharMeses();
  if (rolar) document.getElementById("detalhe-mes").scrollIntoView({ behavior: "smooth" });

  const [ano, mes] = chave.split("-");
  try {
    estado.detalheMes = await buscar(`/estatisticas/mes/${ano}/${Number(mes)}`);
  } catch (erro) {
    console.warn("Não foi possível carregar o mês:", erro);
    return;
  }
  if (estado.mesSelecionado !== chave) return; // o usuário já trocou de mês
  desenharDetalheMes();
}

function textoDelta(atual, anterior, labelAnterior) {
  if (!anterior && !atual) return { texto: `sem vendas em ${labelAnterior}`, classe: "" };
  if (!anterior) return { texto: `novo em relação a ${labelAnterior}`, classe: "sobe" };
  const variacao = ((atual - anterior) / anterior) * 100;
  const seta = variacao > 0 ? "▲" : variacao < 0 ? "▼" : "•";
  const classe = variacao > 0 ? "sobe" : variacao < 0 ? "desce" : "";
  return {
    texto: `${seta} ${Math.abs(variacao).toFixed(0)}% vs ${labelAnterior}`,
    classe,
  };
}

function desenharDetalheMes() {
  const d = estado.detalheMes;
  const r = d.resumo;

  for (const chave of ["receita", "vendas", "ticket_medio", "itens", "clientes"]) {
    document.querySelector(`[data-kpi="${chave}"]`).textContent = formatar(chave, r[chave]);
    const delta = textoDelta(r[chave], d.anterior[chave], d.anterior.label);
    const alvo = document.querySelector(`[data-delta="${chave}"]`);
    alvo.textContent = delta.texto;
    alvo.className = `delta ${delta.classe}`;
  }

  desenharDias();

  const melhor = document.getElementById("melhor-dia");
  melhor.textContent = d.melhor_dia
    ? `Melhor dia: ${d.melhor_dia.dia} (${moeda.format(d.melhor_dia.receita)}). Clique em um dia para ver as vendas dele.`
    : "Nenhuma venda concluída neste mês.";

  // canal de venda
  const total = r.online.receita + r.presencial.receita;
  const pctOnline = total ? (r.online.receita / total) * 100 : 0;
  document.querySelector(".split-online").style.width = `${pctOnline}%`;
  document.querySelector(".split-presencial").style.width = total ? `${100 - pctOnline}%` : "0";
  const descrever = (canal) =>
    `${moeda.format(canal.receita)} · ${numero.format(canal.vendas)} venda(s)` +
    (total ? ` · ${((canal.receita / total) * 100).toFixed(0)}%` : "");
  document.getElementById("canal-online").textContent = descrever(r.online);
  document.getElementById("canal-presencial").textContent = descrever(r.presencial);

  // top produtos do mês
  const top = document.getElementById("top-produtos-mes");
  top.innerHTML = d.top_produtos.length
    ? d.top_produtos
        .map(
          (p) =>
            `<div class="stat-row"><span>${escapar(p.nome)}</span><span>${numero.format(p.quantidade)} vendidos</span></div>`
        )
        .join("")
    : '<p class="empty-row">Sem vendas neste mês.</p>';
}

function desenharDias() {
  const d = estado.detalheMes;
  if (!d) return;
  const [ano, mes] = d.chave.split("-").map(Number);
  const diaSelecionado = document.getElementById("seletor-dia").value;
  const destaque = diaSelecionado.startsWith(d.chave) ? Number(diaSelecionado.slice(8)) - 1 : -1;

  graficoBarras("days-chart", {
    labels: d.dias.labels,
    valores: d.dias[estado.metricaDias],
    metrica: estado.metricaDias,
    destaque,
    aoClicar: (i) => selecionarDia(dataIso(new Date(ano, mes - 1, i + 1)), { rolar: true }),
    titulos: (i) => {
      const data = new Date(ano, mes - 1, i + 1);
      const titulo = data.toLocaleDateString("pt-BR", { weekday: "short", day: "numeric", month: "short" });
      return `${titulo} · ${numero.format(d.dias.vendas[i])} venda(s)`;
    },
  });
}

// ---------------------------------------------------------------------
// vendas do dia
// ---------------------------------------------------------------------

async function selecionarDia(iso, { rolar = false } = {}) {
  const seletor = document.getElementById("seletor-dia");
  seletor.value = iso;
  if (rolar) document.getElementById("vendas-dia").scrollIntoView({ behavior: "smooth" });

  // mantém o gráfico do mês em sincronia com o dia escolhido
  const chaveMes = iso.slice(0, 7);
  if (chaveMes !== estado.mesSelecionado && estado.meses.some((m) => m.chave === chaveMes)) {
    selecionarMes(chaveMes);
  } else {
    desenharDias();
  }

  let dados;
  try {
    dados = await buscar(`/estatisticas/dia/${iso}`);
  } catch (erro) {
    console.warn("Não foi possível carregar o dia:", erro);
    return;
  }
  if (seletor.value !== iso) return;

  const r = dados.resumo;
  document.getElementById("resumo-dia").textContent = r.vendas
    ? `${dataPorExtenso(iso)}: ${numero.format(r.vendas)} venda(s), ${moeda.format(r.receita)} ` +
      `(ticket médio ${moeda.format(r.ticket_medio)}, ${numero.format(r.itens)} itens)`
    : `${dataPorExtenso(iso)}: nenhuma venda concluída.`;

  const corpo = document.getElementById("tabela-dia");
  corpo.innerHTML = dados.vendas.length
    ? dados.vendas
        .map(
          (v) => `<tr>
            <td>${escapar(v.hora)}</td>
            <td>${escapar(v.comprador)}</td>
            <td><span class="canal">${v.presencial ? "Presencial" : "Online"}</span></td>
            <td class="itens-cell">${v.itens.map((i) => `${i.quantidade}× ${escapar(i.nome)}`).join(", ") || "–"}</td>
            <td class="num">${moeda.format(v.valor)}</td>
          </tr>`
        )
        .join("")
    : '<tr><td colspan="5" class="empty-row">Sem vendas neste dia.</td></tr>';
}

function moverDia(delta) {
  const atual = document.getElementById("seletor-dia").value;
  if (!atual) return;
  const [a, m, d] = atual.split("-").map(Number);
  selecionarDia(dataIso(new Date(a, m - 1, d + delta)));
}

// ---------------------------------------------------------------------
// padrões de venda
// ---------------------------------------------------------------------

async function carregarPadroes() {
  const periodo = estado.periodoPadroes;
  try {
    const dados = await buscar(`/estatisticas/padroes${periodo ? `?dias=${periodo}` : ""}`);
    if (periodo !== estado.periodoPadroes) return;
    estado.padroes = dados;
  } catch (erro) {
    console.warn("Não foi possível carregar os padrões de venda:", erro);
    return;
  }
  desenharPadroes();
}

function desenharPadroes() {
  const p = estado.padroes;
  if (!p) return;
  const metrica = estado.metricaPadroes;
  graficoBarras("weekday-chart", {
    labels: p.dias_semana.labels,
    valores: p.dias_semana[metrica],
    metrica,
    titulos: (i) => `${p.dias_semana.labels[i]} · ${numero.format(p.dias_semana.vendas[i])} venda(s)`,
  });
  graficoBarras("hours-chart", {
    labels: p.horas.labels,
    valores: p.horas[metrica],
    metrica,
    titulos: (i) => `${p.horas.labels[i]} · ${numero.format(p.horas.vendas[i])} venda(s)`,
  });
}

// ---------------------------------------------------------------------
// inicialização
// ---------------------------------------------------------------------

function ligarControles() {
  ligarSegmentado("metrica-meses", (v) => {
    estado.metricaMeses = v;
    desenharMeses();
  });
  ligarSegmentado("periodo-meses", (v) => {
    estado.periodoMeses = Number(v);
    desenharMeses();
  });
  ligarSegmentado("metrica-dias", (v) => {
    estado.metricaDias = v;
    desenharDias();
  });
  ligarSegmentado("metrica-padroes", (v) => {
    estado.metricaPadroes = v;
    desenharPadroes();
  });
  ligarSegmentado("periodo-padroes", (v) => {
    estado.periodoPadroes = Number(v);
    carregarPadroes();
  });

  document.getElementById("seletor-mes").addEventListener("change", (e) => selecionarMes(e.target.value));
  const passoMes = (delta) => {
    const i = estado.meses.findIndex((m) => m.chave === estado.mesSelecionado) + delta;
    if (estado.meses[i]) selecionarMes(estado.meses[i].chave);
  };
  document.getElementById("mes-anterior").addEventListener("click", () => passoMes(-1));
  document.getElementById("mes-seguinte").addEventListener("click", () => passoMes(1));

  document.getElementById("seletor-dia").addEventListener("change", (e) => {
    if (e.target.value) selecionarDia(e.target.value);
  });
  document.getElementById("dia-anterior").addEventListener("click", () => moverDia(-1));
  document.getElementById("dia-seguinte").addEventListener("click", () => moverDia(1));
}

async function iniciar() {
  ligarControles();
  carregarPadroes();

  try {
    estado.meses = await buscar("/estatisticas/meses");
  } catch (erro) {
    console.warn("Não foi possível carregar os meses:", erro);
    return;
  }
  preencherSeletorMes();

  const hoje = dataIso(new Date());
  document.getElementById("seletor-dia").value = hoje;
  await selecionarMes(estado.meses[estado.meses.length - 1].chave);
  selecionarDia(hoje);
}

iniciar();
