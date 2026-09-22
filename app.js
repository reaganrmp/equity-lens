const FACTOR_LABELS = {
  narrative_fit: "Narrative fit",
  dilution: "Dilution",
  usage: "Usage / growth",
  volume_legitimacy: "Volume legitimacy",
  team_backers: "Team / backers",
  valuation: "Valuation vs peers",
};

function scoreClass(score, max = 2) {
  if (score === null || score === undefined) return "na";
  if (score >= max * 0.75) return "good";
  if (score >= max * 0.4) return "mid";
  return "bad";
}

function fmtDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function renderFramework(framework) {
  const strip = document.getElementById("framework-strip");
  strip.innerHTML = framework
    .map((f) => `<span class="chip">${FACTOR_LABELS[f] || f}</span>`)
    .join("");
}

function renderCard(result) {
  if (result.error) {
    return `
      <div class="card error-card">
        <strong>${result.ticker}</strong> — failed to load: ${result.error}
      </div>`;
  }

  const cls = scoreClass(result.overall_score, result.overall_max);
  const factorsHtml = Object.entries(result.factors)
    .map(([key, f]) => {
      const dotCls = f.manual ? "na" : scoreClass(f.score);
      return `
        <div class="factor">
          <div class="label">
            <span>${FACTOR_LABELS[key] || key}</span>
            <span class="dot ${dotCls}"></span>
          </div>
          <div class="detail">${f.detail}</div>
        </div>`;
    })
    .join("");

  return `
    <div class="card">
      <div class="card-head">
        <div class="ticker-block">
          <h2>${result.ticker}</h2>
          <div class="name">${result.name || ""}</div>
        </div>
        <div class="price-block">
          <div class="price">${result.price ? "$" + result.price.toLocaleString() : "—"}</div>
          <div class="sector">${result.sector || ""}</div>
        </div>
      </div>
      <div class="overall-score">
        Overall
        <span class="num ${cls}">${result.overall_score ?? "—"}</span>
        / ${result.overall_max}
      </div>
      <div class="narrative">${result.factors.narrative_fit?.detail || ""}</div>
      <div class="factors">${factorsHtml}</div>
    </div>`;
}

async function main() {
  try {
    const res = await fetch("data/results.json", { cache: "no-store" });
    const data = await res.json();

    document.getElementById("generated-at").textContent =
      "Updated " + fmtDate(data.generated_at);
    document.getElementById("ticker-count").textContent =
      data.results.length + " tickers screened";

    renderFramework(data.framework);
    document.getElementById("grid").innerHTML = data.results
      .map(renderCard)
      .join("");
  } catch (e) {
    document.getElementById("grid").innerHTML = `
      <div class="card error-card">
        Could not load data/results.json — run screener.py first (locally or
        via the GitHub Action) to generate it.
      </div>`;
    console.error(e);
  }
}

main();
