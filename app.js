const state = {
  data: null,
  snapshot: null,
  activePage: "projeto",
  loading: false,
};

const elements = {
  projectPage: document.querySelector("#project-page"),
  reportPage: document.querySelector("#report-page"),
  coverEntry: document.querySelector("#cover-entry"),
  nav: document.querySelector("#main-nav"),
  mobileMenu: document.querySelector("#mobile-menu"),
  title: document.querySelector("#page-title"),
  subtitle: document.querySelector("#page-subtitle"),
  filters: document.querySelector("#filters"),
  start: document.querySelector("#start-date"),
  end: document.querySelector("#end-date"),
  indicator: document.querySelector("#indicator-select"),
  export: document.querySelector("#export"),
  architectureProject: document.querySelector("#architecture-project"),
  status: document.querySelector("#status"),
  kpis: document.querySelector("#kpi-grid"),
  chart: document.querySelector("#chart"),
  chartTitle: document.querySelector("#chart-title"),
  chartUnit: document.querySelector("#chart-unit"),
  insights: document.querySelector("#insight-list"),
};

const pageMeta = {
  insights: ["Panorama Histórico", "Acompanhe 4 dos principais indicadores macroeconômicos"],
};

const friendlyNames = { 1: "Dólar", 432: "Selic", 433: "IPCA", 4389: "CDI" };
const symbols = { 1: "$", 432: "▥", 433: "◇", 4389: "▱" };

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function number(value, digits = 2) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return parsed.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function indicatorValue(code, value) {
  if (value === null || value === undefined) return "—";
  if (Number(code) === 1) return `R$ ${number(value, 4)}`;
  if (Number(code) === 433) return `${number(value, 2)}% a.m.`;
  return `${number(value, 2)}% a.a.`;
}

function compactValue(code, value) {
  if (Number(code) === 1) return `R$ ${number(value, 4)}`;
  return `${number(value, 2)}%`;
}

function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function setStatus(message = "", error = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle("is-hidden", !message);
  elements.status.classList.toggle("is-error", error);
}

function showPage(page, updateHash = true) {
  state.activePage = page;
  const isProject = page === "projeto";
  elements.projectPage.classList.toggle("is-hidden", !isProject);
  elements.reportPage.classList.toggle("is-hidden", isProject);
  if (isProject) {
    if (updateHash) history.replaceState(null, "", "#projeto");
    return;
  }

  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.page === page);
  });
  document.querySelectorAll(".page-view").forEach((view) => view.classList.add("is-hidden"));
  document.querySelector(`#${page}-view`)?.classList.remove("is-hidden");
  const meta = pageMeta[page] || pageMeta.insights;
  elements.title.textContent = meta[0];
  elements.subtitle.textContent = meta[1];
  elements.nav.classList.remove("is-open");
  if (updateHash) history.replaceState(null, "", `#${page}`);
  if (!state.data) loadDashboard();
}

function renderLoading() {
  elements.kpis.innerHTML = Array.from({ length: 4 }, () => '<div class="loading-card">Carregando…</div>').join("");
  elements.chart.innerHTML = '<div class="chart-empty">Consultando a camada Ouro…</div>';
  elements.insights.innerHTML = '<div class="loading-card">Preparando insights…</div>';
}

function renderKpis(indicators) {
  elements.kpis.innerHTML = indicators.map((item) => {
    const delta = Number(item.delta);
    const trendClass = delta < 0 ? "trend-down" : "trend-up";
    const arrow = delta < 0 ? "↓" : delta > 0 ? "↑" : "→";
    return `
      <article class="kpi-card">
        <div class="kpi-top">
          <span class="kpi-name"><span aria-hidden="true">${symbols[item.code]}</span>${friendlyNames[item.code]}</span>
          <span class="kpi-code">SGS ${item.code}</span>
        </div>
        <div class="kpi-body">
          <p class="kpi-value">${indicatorValue(item.code, item.value)}</p>
          <div class="kpi-meta">
            <span>Ref. ${formatDate(item.date)}</span>
            <span class="${trendClass}">${arrow} ${compactValue(item.code, Math.abs(delta || 0))}</span>
          </div>
        </div>
      </article>`;
  }).join("");
}

function sampledSeries(series, limit = 160) {
  if (series.length <= limit) return series;
  const step = (series.length - 1) / (limit - 1);
  return Array.from({ length: limit }, (_, index) => series[Math.round(index * step)]);
}

function lineChart(series, code) {
  if (!series?.length) return '<div class="chart-empty">Nenhuma observação encontrada para o período.</div>';
  const data = sampledSeries(series);
  const values = data.map((item) => Number(item.value));
  const width = 900;
  const height = 330;
  const pad = { top: 20, right: 20, bottom: 45, left: 68 };
  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  if (minimum === maximum) { minimum -= 1; maximum += 1; }
  const margin = (maximum - minimum) * 0.08;
  minimum -= margin;
  maximum += margin;
  const x = (index) => pad.left + (index / Math.max(1, data.length - 1)) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((maximum - value) / (maximum - minimum)) * (height - pad.top - pad.bottom);
  const points = data.map((item, index) => `${x(index).toFixed(1)},${y(Number(item.value)).toFixed(1)}`).join(" ");
  const area = `${pad.left},${height - pad.bottom} ${points} ${width - pad.right},${height - pad.bottom}`;
  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = minimum + ((maximum - minimum) * (4 - index)) / 4;
    const position = pad.top + (index / 4) * (height - pad.top - pad.bottom);
    return `<line class="grid-line" x1="${pad.left}" y1="${position}" x2="${width - pad.right}" y2="${position}" />
      <text class="axis-label" x="${pad.left - 10}" y="${position + 4}" text-anchor="end">${escapeHtml(compactValue(code, value))}</text>`;
  }).join("");
  const labelIndexes = [0, Math.floor((data.length - 1) / 2), data.length - 1];
  const labels = labelIndexes.map((index) => `<text class="axis-label" x="${x(index)}" y="${height - 15}" text-anchor="middle">${formatDate(data[index].date)}</text>`).join("");
  const pointIndexes = data.length < 25 ? data.map((_, index) => index) : [0, Math.floor(data.length / 2), data.length - 1];
  const circles = pointIndexes.map((index) => `<circle class="series-point" cx="${x(index)}" cy="${y(values[index])}" r="4"><title>${formatDate(data[index].date)} — ${indicatorValue(code, data[index].value)}</title></circle>`).join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Série histórica com ${series.length} observações">
    <defs><linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4ba6ec" stop-opacity=".48"/><stop offset="100%" stop-color="#4ba6ec" stop-opacity=".05"/></linearGradient></defs>
    ${grid}<polygon class="series-area" points="${area}"/><polyline class="series-line" points="${points}"/>${circles}${labels}
  </svg>`;
}

function renderInsights(data) {
  const stats = data.stats;
  const selected = data.selected_indicator;
  elements.chartTitle.textContent = `Evolução — ${friendlyNames[data.filters.code] || "Indicador"}`;
  elements.chartUnit.textContent = selected?.unit || "Unidade não informada";
  elements.chart.innerHTML = lineChart(data.series, data.filters.code);
  if (!stats || !selected) {
    elements.insights.innerHTML = '<div class="chart-empty">Sem dados para produzir insights.</div>';
    return;
  }
  const change = Number(stats.change);
  const direction = change > 0 ? "alta" : change < 0 ? "queda" : "estabilidade";
  const insights = [
    ["◎", "Cenário atual", `Último valor: ${indicatorValue(selected.code, stats.last)}, em ${formatDate(stats.end_date)}.`],
    ["↕", "Amplitude do período", `Mínimo de ${compactValue(selected.code, stats.minimum)} e máximo de ${compactValue(selected.code, stats.maximum)}.`],
    ["⌁", "Tendência observada", `O intervalo terminou em ${direction}, com variação absoluta de ${compactValue(selected.code, Math.abs(change))}.`],
    ["▦", "Cobertura", `${stats.observations.toLocaleString("pt-BR")} observações entre ${formatDate(stats.start_date)} e ${formatDate(stats.end_date)}.`],
  ];
  elements.insights.innerHTML = insights.map(([icon, title, text]) => `<div class="insight-item"><span class="insight-symbol" aria-hidden="true">${icon}</span><div><strong>${title}</strong><p>${text}</p></div></div>`).join("");
}

function render(data) {
  renderKpis(data.indicators);
  renderInsights(data);
}

function filterSeries(series, start, end) {
  return series.filter((item) => (!start || item.date >= start) && (!end || item.date <= end));
}

function staticStats(series) {
  if (!series.length) return null;
  const values = series.map((item) => Number(item.value));
  const total = values.reduce((sum, value) => sum + value, 0);
  return {
    minimum: String(Math.min(...values)),
    maximum: String(Math.max(...values)),
    average: String(total / values.length),
    first: String(values[0]),
    last: String(values.at(-1)),
    change: String(values.at(-1) - values[0]),
    observations: values.length,
    start_date: series[0].date,
    end_date: series.at(-1).date,
  };
}

function buildStaticPayload(snapshot, code, start, end) {
  const indicators = Object.entries(snapshot.series).flatMap(([indicatorCode, fullSeries]) => {
    const series = filterSeries(fullSeries, start, end);
    if (!series.length) return [];
    const latest = series.at(-1);
    const previous = series.at(-2);
    const metadata = snapshot.indicators.find((item) => Number(item.code) === Number(indicatorCode));
    return [{
      ...metadata,
      code: Number(indicatorCode),
      date: latest.date,
      value: latest.value,
      previous_date: previous?.date ?? null,
      previous_value: previous?.value ?? null,
      delta: previous ? String(Number(latest.value) - Number(previous.value)) : null,
    }];
  });
  const series = filterSeries(snapshot.series[String(code)] || [], start, end);
  return {
    generated_at: snapshot.generated_at,
    filters: { code, start: start || null, end: end || null },
    indicators,
    selected_indicator: indicators.find((item) => Number(item.code) === code) || null,
    series,
    stats: staticStats(series),
  };
}

async function loadStaticDashboard(code, start, end) {
  if (!state.snapshot) {
    const response = await fetch("./data/dashboard.json", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Snapshot público do relatório não encontrado.");
    state.snapshot = await response.json();
  }
  return buildStaticPayload(state.snapshot, code, start, end);
}

async function loadDashboard() {
  if (state.loading) return;
  state.loading = true;
  setStatus();
  renderLoading();
  const params = new URLSearchParams({ code: elements.indicator.value });
  if (elements.start.value) params.set("start", elements.start.value);
  if (elements.end.value) params.set("end", elements.end.value);
  try {
    let payload;
    try {
      const response = await fetch(`/api/dashboard?${params.toString()}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("API local indisponível");
      payload = await response.json();
    } catch {
      payload = await loadStaticDashboard(
        Number(elements.indicator.value),
        elements.start.value,
        elements.end.value,
      );
    }
    state.data = payload;
    render(payload);
  } catch (error) {
    setStatus(error.message || "Não foi possível carregar os dados.", true);
    elements.kpis.innerHTML = "";
    elements.chart.innerHTML = '<div class="chart-empty">Verifique o PostgreSQL e as configurações do arquivo .env.</div>';
  } finally {
    state.loading = false;
  }
}

function exportCsv() {
  if (!state.data?.series?.length) return;
  const code = state.data.filters.code;
  const rows = [["data_referencia", "codigo_sgs", "indicador", "valor", "unidade"]];
  state.data.series.forEach((item) => rows.push([item.date, code, friendlyNames[code], item.value, state.data.selected_indicator?.unit || ""]));
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(";")).join("\n");
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `indicador_${code}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

elements.coverEntry.addEventListener("click", () => showPage("insights"));
elements.nav.addEventListener("click", (event) => {
  const button = event.target.closest("[data-page]");
  if (button) showPage(button.dataset.page);
});
elements.mobileMenu.addEventListener("click", () => elements.nav.classList.toggle("is-open"));
elements.export.addEventListener("click", exportCsv);
elements.architectureProject.addEventListener("click", () => showPage("projeto"));
elements.indicator.addEventListener("change", loadDashboard);
elements.start.addEventListener("change", loadDashboard);
elements.end.addEventListener("change", loadDashboard);

const initialPage = location.hash.replace("#", "");
showPage(initialPage === "projeto" ? "projeto" : "insights", false);
function normalizeNavigationLabels() {
  document.querySelectorAll('[data-page="insights"]').forEach((control) => {
    const textNodes = document.createTreeWalker(control, NodeFilter.SHOW_TEXT);
    let textNode = textNodes.nextNode();

    while (textNode) {
      textNode.textContent = textNode.textContent.replace(
        "Entrar no Relatório",
        "Relatório",
      );
      textNode = textNodes.nextNode();
    }
  });

}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", normalizeNavigationLabels);
} else {
  normalizeNavigationLabels();
}

