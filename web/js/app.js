/* app.js (type="module") */

// ----------------------------
// LIVE BTC PRICE (separat vom Tagesschlusskurs aus btc.json)
// Binance WebSocket (BTCUSDT) + Coinbase USD Fallback
// ----------------------------
let liveWS = null;
let lastTick = 0;

function setLiveText(text) {
  const el = document.getElementById("kpiLive");
  if (el) el.textContent = text;
}

function setLivePrice(num, unit, src) {
  const n = Number(num);
  if (!isFinite(n)) return;
  setLiveText(`Live: ${n.toLocaleString("de-DE")} ${unit}${src ? ` (${src})` : ""}`);
}

async function fetchLiveBTC_CoinbaseUSD() {
  const url = "https://api.coinbase.com/v2/prices/BTC-USD/spot";
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error("Coinbase HTTP " + r.status);
  const j = await r.json();
  const amount = j?.data?.amount;
  const px = amount != null ? Number(amount) : null;
  return isFinite(px) ? px : null;
}

function startLiveBTC(intervalMs = 5000) {
  setLiveText("Live: lade…");

  const wsUrl = "wss://stream.binance.com:9443/ws/btcusdt@trade";

  function connectWS() {
    try { if (liveWS) liveWS.close(); } catch {}
    liveWS = null;

    let ws;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      setLiveText("Live: – (WebSocket nicht möglich)");
      return;
    }
    liveWS = ws;

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const px = Number(msg?.p);
        if (isFinite(px)) {
          lastTick = Date.now();
          setLivePrice(px, "USDT", "Binance");
        }
      } catch {}
    };

    ws.onerror = () => { try { ws.close(); } catch {} };
    ws.onclose = () => {
      setLiveText("Live: – (reconnect…)");
      setTimeout(connectWS, 1500);
    };
  }

  connectWS();

  // Watchdog: wenn WS hängen bleibt -> reconnect
  setInterval(() => {
    if (lastTick && (Date.now() - lastTick > 20000)) {
      try { liveWS?.close(); } catch {}
    }
  }, 5000);

  // USD-Fallback (nur wenn WS nicht liefert)
  setInterval(async () => {
    try {
      if (lastTick && (Date.now() - lastTick < 8000)) return; // WS ok
      const px = await fetchLiveBTC_CoinbaseUSD();
      if (px != null) setLivePrice(px, "USD", "Coinbase");
    } catch {
      if (!lastTick || (Date.now() - lastTick > 8000)) {
        setLiveText("Live: – (nicht verfügbar)");
      }
    }
  }, Math.max(2000, intervalMs));
}

// ----------------------------
// Helpers
// ----------------------------
function fmtNumber(n) {
  try { return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 }); }
  catch { return String(n); }
}
function fmtDateTimeLocal(d) {
  return d.toLocaleString(undefined, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function fmtUSD(x){ return `${fmtNumber(x)} USD`; }
function fmtPct(x){ return `${x>=0?"+":""}${fmtNumber(x*100)}%`; }

function priceForRatioPct(ratioPct, lastTrough, lastPeak) {
  const w = lastPeak - lastTrough;
  if (!isFinite(w) || w <= 0) return null;
  return lastTrough + (ratioPct / 100) * w;
}

function maxDrawdown(values){
  let peak = -Infinity;
  let maxDD = 0;
  for (const v of values){
    if (v == null || !isFinite(v)) continue;
    if (v > peak) peak = v;
    const dd = peak > 0 ? (v/peak - 1) : 0;
    if (dd < maxDD) maxDD = dd;
  }
  return maxDD; // negative
}

function meanStd(values){
  let n = 0, mean = 0, M2 = 0;
  for (const v0 of values){
    const v = Number(v0);
    if (!isFinite(v)) continue;
    n++;
    const delta = v - mean;
    mean += delta / n;
    M2 += delta * (v - mean);
  }
  const variance = (n > 1) ? (M2 / (n - 1)) : 0;
  const std = Math.sqrt(Math.max(variance, 0));
  return { n, mean, std };
}

// ----------------------------
// Strategy: Sell-Ladder (g0/g1/g2) + Re-Entry Modes
// ----------------------------

// Sell ladder as function of ratio (g0/g1/g2)
function sellWeight(r, sellStart, ladder) {
  if (r <= sellStart) return 1.0;
  if (r >= 100) return 0.0;

  const width = 100 - sellStart;
  if (width <= 0) return 0;

  const x = clamp((r - sellStart) / width, 0, 1); // 0..1 im Sell-Bereich

  if (ladder === "g0") {
    // soft / konkav: 1 - x^2 (höhere Exposure als linear)
    return clamp(1 - x * x, 0, 1);
  }

  if (ladder === "g2") {
    // aggressiv: (1 - x)^2
    const base = clamp(1 - x, 0, 1);
    return base * base;
  }

  // g1 default: linear 1 - x
  return clamp(1 - x, 0, 1);
}

/**
 * Schrittlogik mit Zustand:
 * - state.inSell: ob wir jemals im Sell-Regime waren (ratio >= sellStart)
 * - state.reentryAnchorW: nur für "gradual": Start-Quote beim Unterschreiten von SellStart
 */
function stepWeightWithState(prevW, r, params, state) {
  const { ladder, sellStart, buyTh, reentryMode } = params;

  // Enter/Stay in sell regime
  if (r >= sellStart) {
    state.inSell = true;
    state.reentryAnchorW = null;
    const wT = sellWeight(r, sellStart, ladder);
    const delta = wT - prevW;
    if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
    if (delta > 0) return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
    return { w: wT, action: "SELL / REBALANCE DOWN", tag: "sell" };
  }

  // Below SellStart
  // If never entered sell regime before => always 100% (neutral)
  if (!state.inSell) {
    const wT = 1.0;
    const delta = wT - prevW;
    if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
    return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
  }

  // We were in sell regime before => apply chosen re-entry behavior
  if (reentryMode === "instant") {
    const wT = 1.0;
    state.inSell = false;
    state.reentryAnchorW = null;
    const delta = wT - prevW;
    if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
    return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
  }

  if (reentryMode === "wait") {
    // Wait until BuyTh to return to 100%, otherwise HOLD position
    if (r <= buyTh) {
      const wT = 1.0;
      state.inSell = false;
      state.reentryAnchorW = null;
      const delta = wT - prevW;
      if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
      return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
    }
    return { w: prevW, action: "HOLD (WAIT RE-ENTRY)", tag: "hold" };
  }

  // gradual: "pö a pö" hochkaufen (ohne BuyTh-Zwang)
  // -> Wir verwenden eine feste "Re-Entry Zone" unter SellStart.
  //    Zielquote wächst mit Abstand unter SellStart.
  //    BuyTh bleibt UI-mäßig deaktiviert (wird hier nicht benötigt).
  {
    const wAnchor = (state.reentryAnchorW == null) ? prevW : state.reentryAnchorW;
    if (state.reentryAnchorW == null) state.reentryAnchorW = wAnchor;

    // Zone-Breite: dynamisch aber stabil (keine extra UI nötig)
    const zone = Math.max(8, sellStart * 0.40); // z.B. SellStart=46 -> ~18.4
    const t = clamp((sellStart - r) / zone, 0, 1); // 0..1
    const wT = wAnchor + (1 - wAnchor) * t;

    // Optional: wenn Ratio wieder sehr niedrig (<= 5%), beenden wir "inSell"
    // damit bei längeren Low-Phasen wieder neutral gilt.
    if (r <= 5) {
      state.inSell = false;
      state.reentryAnchorW = null;
    }

    const delta = wT - prevW;
    if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
    if (delta > 0) return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
    return { w: wT, action: "SELL / REBALANCE DOWN", tag: "sell" };
  }
}

// ----------------------------
// Charts
// ----------------------------
function renderRatioDistributionSinceStart({ ratioSeries, currentRatio, startDateLabel, COLORS }) {
  const hintEl = document.getElementById("distHint");

  const vals = (ratioSeries || [])
    .map(v => clamp(Number(v), 0, 100))
    .filter(v => isFinite(v));

  if (vals.length < 2) {
    if (hintEl) hintEl.textContent = startDateLabel ? `Seit ${startDateLabel}: zu wenig Daten` : "Zu wenig Daten";
    Plotly.react("distChart", [], {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { l: 48, r: 18, t: 10, b: 35 },
      font: { size: 11, color: "rgba(255,255,255,.85)" },
      annotations: [{
        text: "Zu wenig Daten für Verteilung",
        xref: "paper", yref: "paper", x: 0.5, y: 0.5, showarrow: false
      }]
    }, { responsive: true, displayModeBar: false, displaylogo: false });
    return;
  }

  const { n, mean, std } = meanStd(vals);
  const m1 = clamp(mean - std, 0, 100);
  const p1 = clamp(mean + std, 0, 100);
  const cur = isFinite(currentRatio) ? clamp(Number(currentRatio), 0, 100) : null;

  if (hintEl) {
    hintEl.textContent =
      `${startDateLabel ? `Seit ${startDateLabel} | ` : ""}n=${n} | μ=${fmtNumber(mean)} | σ=${fmtNumber(std)} | -1σ=${fmtNumber(m1)} | +1σ=${fmtNumber(p1)}` +
      (cur != null ? ` | Jetzt=${fmtNumber(cur)}` : "");
  }

  const traces = [{
    type: "histogram",
    x: vals,
    xbins: { start: 0, end: 101, size: 1 },
    marker: { color: COLORS.ratio },
    opacity: 0.85,
    hovertemplate: "Position: %{x:.0f}%<br>Anzahl: %{y}<extra></extra>",
    name: "Häufigkeit"
  }];

  const shapes = [
    { type: "rect", xref: "x", yref: "paper", x0: m1, x1: p1, y0: 0, y1: 1, fillcolor: "rgba(255,255,255,.06)", line: { width: 0 } },
    { type: "line", xref: "x", yref: "paper", x0: mean, x1: mean, y0: 0, y1: 1, line: { color: "rgba(255,255,255,.45)", width: 2 } },
    { type: "line", xref: "x", yref: "paper", x0: m1, x1: m1, y0: 0, y1: 1, line: { color: "rgba(255,255,255,.28)", width: 1, dash: "dot" } },
    { type: "line", xref: "x", yref: "paper", x0: p1, x1: p1, y0: 0, y1: 1, line: { color: "rgba(255,255,255,.28)", width: 1, dash: "dot" } },
  ];

  const annotations = [
    { x: mean, y: 1.05, xref: "x", yref: "paper", text: `μ ${fmtNumber(mean)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.85)" } },
    { x: m1,   y: 1.05, xref: "x", yref: "paper", text: `-1σ ${fmtNumber(m1)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.75)" } },
    { x: p1,   y: 1.05, xref: "x", yref: "paper", text: `+1σ ${fmtNumber(p1)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.75)" } }
  ];

  if (cur != null) {
    shapes.push({ type: "line", xref: "x", yref: "paper", x0: cur, x1: cur, y0: 0, y1: 1, line: { color: COLORS.strat, width: 2, dash: "dash" } });
    annotations.push({ x: cur, y: 1.05, xref: "x", yref: "paper", text: `Jetzt ${fmtNumber(cur)}`, showarrow: false, font: { size: 11, color: COLORS.strat } });
  }

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 48, r: 18, t: 22, b: 38 },
    font: { size: 11, color: "rgba(255,255,255,.85)" },
    bargap: 0.05,
    xaxis: {
      title: "Kanal-Position (%)",
      range: [0, 100],
      dtick: 10,
      showgrid: true,
      gridcolor: "rgba(255,255,255,.06)",
      tickfont: { color: "rgba(255,255,255,.70)" }
    },
    yaxis: {
      title: "Häufigkeit",
      showgrid: true,
      gridcolor: "rgba(255,255,255,.08)",
      zerolinecolor: "rgba(255,255,255,.10)",
      tickfont: { color: "rgba(255,255,255,.70)" }
    },
    shapes,
    annotations
  };

  Plotly.react("distChart", traces, layout, { responsive: true, displayModeBar: false, displaylogo: false });
}

function renderExposureVsRatioChart({ sellStart, ladder, rNow, wNow, COLORS }) {
  const hintEl = document.getElementById("expoHint");
  if (!(sellStart < 100)) return;

  const ladderLabel =
    ladder === "g0" ? "g0 (1-x²)" :
    ladder === "g2" ? "g2 ((1-x)²)" : "g1 (1-x)";

  if (hintEl) hintEl.textContent = `Sell ≥ ${sellStart} → Leiter ${ladderLabel} (darunter je nach Re-Entry-Modus)`;

  const xs = [];
  const ys = [];
  for (let r = 0; r <= 100; r += 1) {
    xs.push(r);
    let wTarget = 1.0;
    if (r >= sellStart) wTarget = sellWeight(r, sellStart, ladder);
    ys.push(wTarget * 100);
  }

  const traces = [
    { x: xs, y: ys, name: "Sell-Leiter (Ziel)", mode: "lines", line: { color: COLORS.ratio, width: 2.2 } },
    { x: [rNow], y: [wNow * 100], name: "Jetzt", mode: "markers", marker: { size: 9, color: COLORS.strat } }
  ];

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 48, r: 18, t: 10, b: 35 },
    font: { size: 11, color: "rgba(255,255,255,.85)" },
    legend: {
      orientation: "h",
      x: 0, y: 1.18,
      xanchor: "left", yanchor: "top",
      bgcolor: "rgba(0,0,0,0)",
      font: { size: 10, color: "rgba(255,255,255,.78)" }
    },
    xaxis: {
      title: "Kanal-Position / Ratio (%)",
      range: [0, 100],
      showgrid: true,
      gridcolor: "rgba(255,255,255,.06)",
      tickfont: { color: "rgba(255,255,255,.70)" }
    },
    yaxis: {
      title: "BTC-Exposure (%)",
      range: [0, 100],
      showgrid: true,
      gridcolor: "rgba(255,255,255,.08)",
      zerolinecolor: "rgba(255,255,255,.10)",
      tickfont: { color: "rgba(255,255,255,.70)" }
    },
    shapes: [
      { type: "line", x0: sellStart, x1: sellStart, y0: 0, y1: 100, line: { color: "rgba(255,255,255,.22)", width: 1, dash: "dash" } }
    ]
  };

  Plotly.react("expoChart", traces, layout, { responsive: true, displayModeBar: false, displaylogo: false });
}

// ----------------------------
// Main
// ----------------------------
async function main() {
  const isMobile = window.matchMedia("(max-width: 700px)").matches;

  // Load data
  const res = await fetch("./data/btc.json", { cache: "no-store" });
  const data = await res.json();

  const d = data.series.date;
  const price = data.series.price;
  const fair = data.series.fair;
  const log10r = data.series.log10_r;
  const ratio = data.series.ratio;

  const de = data.extended.date;
  const fairExt = data.extended.fair;
  const peakLine = data.extended.peak_line_price;
  const troughLine = data.extended.trough_line_price;
  const peakLog = data.extended.peak_line_log10;
  const troughLog = data.extended.trough_line_log10;

  // Meta / KPI
  const lastDate = d?.length ? d[d.length - 1] : "unbekannt";
  const lastClose = price?.length ? Number(price[price.length - 1]) : null;
  const lastRatio = ratio?.length ? ratio[ratio.length - 1] : null;

  const updatedUtcRaw = data.meta?.updated_utc || null;
  const updatedUtc = updatedUtcRaw ? new Date(updatedUtcRaw) : null;
  const updatedLocal = updatedUtc ? fmtDateTimeLocal(updatedUtc) : "unbekannt";

  const metaEl = document.getElementById("meta");
  if (metaEl) {
    metaEl.textContent =
      `Letzte Aktualisierung: ${updatedLocal}` +
      ` | Datenstand: ${lastDate}` +
      (lastClose !== null ? ` | Close: ${fmtNumber(lastClose)} USD` : "");
  }

  const kpiPriceEl = document.getElementById("kpiPrice");
  const kpiPriceSubEl = document.getElementById("kpiPriceSub");
  if (kpiPriceEl) kpiPriceEl.textContent = (lastClose !== null ? `${fmtNumber(lastClose)} USD` : "–");
  if (kpiPriceSubEl) kpiPriceSubEl.textContent = (lastClose !== null ? `Tagesschlusskurs (Close) — ${lastDate}` : "Tagesschlusskurs (Close)");

  // Live
  setLiveText("Live: –");
  startLiveBTC(5000);

  const kpiRatioEl = document.getElementById("kpiRatio");
  const kpiRatioSubEl = document.getElementById("kpiRatioSub");
  if (kpiRatioEl) kpiRatioEl.textContent = (lastRatio !== null ? `${fmtNumber(lastRatio)} %` : "–");
  if (kpiRatioSubEl) kpiRatioSubEl.textContent = "Position im Peak/Trough-Kanal";

  const kpiDateEl = document.getElementById("kpiDate");
  const kpiDateSubEl = document.getElementById("kpiDateSub");
  if (kpiDateEl) kpiDateEl.textContent = lastDate || "–";
  if (kpiDateSubEl) kpiDateSubEl.textContent = "Letzter Datenpunkt";

  const kpiUpdatedEl = document.getElementById("kpiUpdated");
  const kpiUpdatedSubEl = document.getElementById("kpiUpdatedSub");
  if (kpiUpdatedEl) kpiUpdatedEl.textContent = updatedLocal;
  if (kpiUpdatedSubEl) kpiUpdatedSubEl.textContent = updatedUtcRaw ? `Quelle: ${updatedUtcRaw}` : "–";

  // Colors
  const COLORS = {
    price: "rgba(170,170,170,0.95)",
    log10r: "rgba(170,170,170,0.95)",
    fair:  "#2ca02c",
    peak:  "#d62728",
    trough:"#1f77b4",
    ratio: "#9467bd",
    strat: "#57d38c",
    hold: "rgba(170,170,170,0.70)"
  };

  // Map channel lines by date
  const peakByDate = new Map();
  const troughByDate = new Map();
  for (let i = 0; i < de.length; i++) {
    peakByDate.set(de[i], peakLine[i]);
    troughByDate.set(de[i], troughLine[i]);
  }

  // ratioFair = (Fair - Trough) / (Peak - Trough) * 100
  const ratioFair = d.map((dateStr, i) => {
    const pk = peakByDate.get(dateStr);
    const tr = troughByDate.get(dateStr);
    const fv = fair[i];
    if (pk == null || tr == null || fv == null) return null;
    const width = pk - tr;
    if (!isFinite(width) || width <= 0) return null;
    return clamp(((fv - tr) / width) * 100, 0, 100);
  });

  // Last-day channel for price estimation
  const lastDateStr = d[d.length - 1];
  const pk0 = peakByDate.get(lastDateStr);
  const tr0 = troughByDate.get(lastDateStr);
  const lastPeak = (pk0 != null) ? pk0 : peakLine[peakLine.length - 1];
  const lastTrough = (tr0 != null) ? tr0 : troughLine[troughLine.length - 1];

  // ----------------------------
  // ---- EXPLAIN SECTION (Herleitung) ----
  // ----------------------------
  const explainNowLineEl = document.getElementById("explainNowLine");
  const explainRegimeEl = document.getElementById("explainRegime");
  const explainRegimeSubEl = document.getElementById("explainRegimeSub");
  const explainWhyEl = document.getElementById("explainWhy");
  const explainWhySubEl = document.getElementById("explainWhySub");
  const explainNextEl = document.getElementById("explainNext");
  const explainNextSubEl = document.getElementById("explainNextSub");

  const rNow0 = Number(ratio[ratio.length - 1]);
  const close0 = Number(price[price.length - 1]);

  if (explainNowLineEl) {
    const chWidth = (lastPeak - lastTrough);
    explainNowLineEl.textContent =
      `Jetzt (${lastDate}): Close ${fmtNumber(close0)} USD | Ratio ${fmtNumber(rNow0)}% | Kanalbreite ${isFinite(chWidth) ? fmtNumber(chWidth) : "–"} USD`;
  }

  function updateExplainFromStrategyParams() {
    const ladder = String(document.getElementById("strategySelect")?.value || "g1");
    const buyTh = Number(document.getElementById("buyTh")?.value);
    const sellStart = Number(document.getElementById("sellStart")?.value);

    // Regime
    if (rNow0 >= sellStart) {
      if (explainRegimeEl) explainRegimeEl.textContent = "Sell-Regime aktiv";
      if (explainRegimeSubEl) explainRegimeSubEl.textContent = `Ratio ${fmtNumber(rNow0)}% ≥ SellStart ${fmtNumber(sellStart)}%`;
    } else {
      if (explainRegimeEl) explainRegimeEl.textContent = "Neutral / Voll investiert";
      if (explainRegimeSubEl) explainRegimeSubEl.textContent = `Ratio ${fmtNumber(rNow0)}% < SellStart ${fmtNumber(sellStart)}% → Zielquote = 100%`;
    }

    // Warum Zielquote
    let wT = 1.0;
    if (rNow0 >= sellStart) wT = sellWeight(rNow0, sellStart, ladder);

    if (explainWhyEl) explainWhyEl.textContent = `Zielquote ≈ ${fmtNumber(wT * 100)}% BTC`;
    if (explainWhySubEl) {
      const ladderLabel = ladder === "g0" ? "g0 (1-x²)" : ladder === "g2" ? "g2 ((1-x)²)" : "g1 (1-x)";
      explainWhySubEl.textContent = `Leiter: ${ladderLabel} | BuyTh ${fmtNumber(buyTh)} | SellStart ${fmtNumber(sellStart)}`;
    }

    // Nächster Schritt (grob)
    if (rNow0 < sellStart) {
      const px = priceForRatioPct(sellStart, lastTrough, lastPeak);
      if (explainNextEl) explainNextEl.textContent = `Wenn Ratio ≥ ${fmtNumber(sellStart)}% → reduzieren`;
      if (explainNextSubEl) explainNextSubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${px == null ? "–" : fmtUSD(px)}`;
    } else {
      const rUp = clamp(Math.ceil(rNow0 + 1e-9), sellStart, 100);
      const rDown = clamp(Math.floor(rNow0 - 1e-9), 0, 100);
      const pxUp = priceForRatioPct(rUp, lastTrough, lastPeak);
      const pxDown = priceForRatioPct(rDown, lastTrough, lastPeak);
      if (explainNextEl) explainNextEl.textContent = `Up/Down: Ratio ${fmtNumber(rUp)}% / ${fmtNumber(rDown)}%`;
      if (explainNextSubEl) explainNextSubEl.textContent =
        `Preis-Schätzung: ${pxUp == null ? "–" : fmtUSD(pxUp)} / ${pxDown == null ? "–" : fmtUSD(pxDown)}`;
    }
  }

  // initial + bei Strategy-Änderung refresh
  updateExplainFromStrategyParams();
  ["strategySelect", "buyTh", "sellStart"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", updateExplainFromStrategyParams);
  });

  // ----------------------------
  // Strategy UI wiring
  // ----------------------------
  const strategySelect = document.getElementById("strategySelect");
  const startDateEl = document.getElementById("startDate");
  const startWeightEl = document.getElementById("startWeight");
  const buyThEl = document.getElementById("buyTh");
  const sellStartEl = document.getElementById("sellStart");
  const reentryModeEl = document.getElementById("reentryMode");
  const buyHintEl = document.getElementById("buyHint");

  const btnApply = document.getElementById("btnApply");
  const pillLabelEl = document.getElementById("pillLabel");

  const recWeightEl = document.getElementById("recWeight");
  const recActionEl = document.getElementById("recAction");
  const recTagEl = document.getElementById("recTag");

  const nextTriggerSellEl = document.getElementById("nextTriggerSell");
  const nextTriggerSellSubEl = document.getElementById("nextTriggerSellSub");
  const nextTriggerBuyEl = document.getElementById("nextTriggerBuy");
  const nextTriggerBuySubEl = document.getElementById("nextTriggerBuySub");

  const lastTradeEl = document.getElementById("lastTrade");
  const lastTradeSubEl = document.getElementById("lastTradeSub");
  const ladderHintEl = document.getElementById("ladderHint");

  const perfDiffEl = document.getElementById("perfDiff");
  const perfSubEl  = document.getElementById("perfSub");
  const perfTinyEl = document.getElementById("perfTiny");

  let strategyChartInited = false;

  function renderTag(tag) {
    if (!recTagEl) return;
    recTagEl.classList.remove("buy","sell","hold");
    recTagEl.classList.add(tag);
    recTagEl.textContent = tag.toUpperCase();
  }

  function resetMiniTiles() {
    if (nextTriggerSellEl) nextTriggerSellEl.textContent = "SELL: –";
    if (nextTriggerSellSubEl) nextTriggerSellSubEl.textContent = "–";
    if (nextTriggerBuyEl) nextTriggerBuyEl.textContent = "BUY: –";
    if (nextTriggerBuySubEl) nextTriggerBuySubEl.textContent = "–";
    if (lastTradeEl) lastTradeEl.textContent = "–";
    if (lastTradeSubEl) lastTradeSubEl.textContent = "–";
    if (perfDiffEl) perfDiffEl.textContent = "–";
    if (perfSubEl) perfSubEl.textContent = "–";
    if (perfTinyEl) perfTinyEl.textContent = "–";
    if (ladderHintEl) ladderHintEl.textContent = "–";
  }

  function updateBuyThUI() {
    const mode = String(reentryModeEl?.value || "instant");
    const isWait = mode === "wait";
    if (buyThEl) buyThEl.disabled = !isWait;
    if (buyHintEl) buyHintEl.textContent = isWait
      ? "Wird genutzt im Re-Entry Modus „Wait“."
      : "Deaktiviert (nur für Modus „Wait“).";
    if (buyThEl) buyThEl.style.opacity = isWait ? "1" : "0.6";
  }

  updateBuyThUI();
  if (reentryModeEl) reentryModeEl.addEventListener("change", () => {
    updateBuyThUI();
    computeStrategyAndRender();
  });

  function computeStrategyAndRender() {
    const ladder = String(strategySelect?.value || "g1");
    const sellStart = Number(sellStartEl?.value);
    const buyTh = Number(buyThEl?.value);
    const reentryMode = String(reentryModeEl?.value || "instant");
    const startDate = String(startDateEl?.value || "2018-01-01");
    const startW = clamp(Number(startWeightEl?.value) / 100, 0, 1);

    if (pillLabelEl) pillLabelEl.textContent = `sell${fmtNumber(sellStart)} | reentry: ${reentryMode}`;

    // --- Distribution: seit Startdatum ---
    const startIdxForDist = d.findIndex(x => x >= startDate);
    renderRatioDistributionSinceStart({
      ratioSeries: startIdxForDist < 0 ? [] : ratio.slice(startIdxForDist),
      currentRatio: Number(ratio[ratio.length - 1]),
      startDateLabel: startDate,
      COLORS
    });

    // Validations
    if (!(isFinite(sellStart) && sellStart > 0 && sellStart < 100)) {
      if (recWeightEl) recWeightEl.textContent = "–";
      if (recActionEl) recActionEl.textContent = "Fehler: Sell Start muss zwischen 0 und 100 liegen.";
      renderTag("hold");
      resetMiniTiles();
      renderExposureVsRatioChart({ sellStart: clamp(sellStart, 0, 100), ladder, rNow: Number(ratio[ratio.length - 1]), wNow: startW, COLORS });
      return;
    }

    const startIdx = d.findIndex(x => x >= startDate);
    if (startIdx < 0) {
      if (recWeightEl) recWeightEl.textContent = "–";
      if (recActionEl) recActionEl.textContent = "Startdatum liegt nach dem letzten Datenpunkt.";
      renderTag("hold");
      resetMiniTiles();
      renderExposureVsRatioChart({ sellStart, ladder, rNow: Number(ratio[ratio.length - 1]), wNow: startW, COLORS });
      return;
    }

    // --- Build weight series (w at end of each day) ---
    const wArr = new Array(d.length).fill(null);
    let w = startW;
    let lastTrade = null;

    const state = { inSell: false, reentryAnchorW: null };

    const params = { ladder, sellStart, buyTh, reentryMode };

    for (let i = startIdx; i < d.length; i++) {
      const r = Number(ratio[i]);
      const step = stepWeightWithState(w, r, params, state);
      const changed = Math.abs(step.w - w) > 1e-12;
      if (changed) lastTrade = { date: d[i], action: step.action, ratio: r, w: step.w, tag: step.tag };
      w = step.w;
      wArr[i] = w;
    }

    // current day action (recompute one-step vs yesterday)
    const rNow = Number(ratio[ratio.length - 1]);
    let wBefore = startW;

    const state2 = { inSell: false, reentryAnchorW: null };
    for (let i = startIdx; i < d.length - 1; i++) {
      wBefore = stepWeightWithState(wBefore, Number(ratio[i]), params, state2).w;
    }
    const nowStep = stepWeightWithState(wBefore, rNow, params, state2);
    const wNow = wArr[d.length - 1] ?? startW;

    if (recWeightEl) recWeightEl.textContent = `${fmtNumber(wNow * 100)}% BTC`;
    if (recActionEl) recActionEl.textContent = `Jetzt (${d[d.length-1]} | Ratio ${fmtNumber(rNow)}): ${nowStep.action}`;
    renderTag(nowStep.tag);

    renderExposureVsRatioChart({ sellStart, ladder, rNow, wNow, COLORS });

    // ladder hint
    const w50 = sellWeight(50, sellStart, ladder) * 100;
    const w70 = sellWeight(70, sellStart, ladder) * 100;
    const w90 = sellWeight(90, sellStart, ladder) * 100;
    if (ladderHintEl) ladderHintEl.textContent = `${fmtNumber(w50)}% / ${fmtNumber(w70)}% / ${fmtNumber(w90)}%`;

    // NEXT TRIGGERS
    if (rNow < sellStart) {
      const sellPx = priceForRatioPct(sellStart, lastTrough, lastPeak);
      if (nextTriggerSellEl) nextTriggerSellEl.textContent = `SELL: beginnt @ Ratio ${fmtNumber(sellStart)}`;
      if (nextTriggerSellSubEl) nextTriggerSellSubEl.textContent =
        `Preis-Schätzung (heutiger Kanal): ${sellPx == null ? "–" : fmtUSD(sellPx)} — Ab hier wird nach Leiter reduziert.`;

      if (reentryMode === "wait") {
        const buyPx = priceForRatioPct(buyTh, lastTrough, lastPeak);
        if (nextTriggerBuyEl) nextTriggerBuyEl.textContent = `RE-ENTRY: 100% @ Ratio ${fmtNumber(buyTh)}`;
        if (nextTriggerBuySubEl) nextTriggerBuySubEl.textContent =
          `Preis-Schätzung (heutiger Kanal): ${buyPx == null ? "–" : fmtUSD(buyPx)} — Erst dann zurück auf 100%.`;
      } else if (reentryMode === "instant") {
        if (nextTriggerBuyEl) nextTriggerBuyEl.textContent = `RE-ENTRY: sofort 100% (unter SellStart)`;
        if (nextTriggerBuySubEl) nextTriggerBuySubEl.textContent = `Sobald Ratio < ${fmtNumber(sellStart)}%, wird direkt auf 100% erhöht.`;
      } else {
        if (nextTriggerBuyEl) nextTriggerBuyEl.textContent = `RE-ENTRY: gradual (pö a pö)`;
        if (nextTriggerBuySubEl) nextTriggerBuySubEl.textContent = `Unter SellStart wird schrittweise hochgekauft (ohne BuyTh).`;
      }
    } else {
      const rUp = clamp(Math.ceil(rNow + 1e-9), sellStart, 100);
      const rDown = clamp(Math.floor(rNow - 1e-9), 0, 100);
      const pxUp = priceForRatioPct(rUp, lastTrough, lastPeak);
      const pxDown = priceForRatioPct(rDown, lastTrough, lastPeak);

      if (nextTriggerSellEl) nextTriggerSellEl.textContent = `DOWN: niedrigere BTC-Quote @ Ratio ${fmtNumber(rUp)}`;
      if (nextTriggerSellSubEl) nextTriggerSellSubEl.textContent =
        `Preis-Schätzung (heutiger Kanal): ${pxUp == null ? "–" : fmtUSD(pxUp)} — Bei steigender Ratio wird weiter reduziert.`;

      if (nextTriggerBuyEl) nextTriggerBuyEl.textContent = `UP: höhere BTC-Quote @ Ratio ${fmtNumber(rDown)}`;
      if (nextTriggerBuySubEl) nextTriggerBuySubEl.textContent =
        `Preis-Schätzung (heutiger Kanal): ${pxDown == null ? "–" : fmtUSD(pxDown)} — Bei fallender Ratio wird hochrebalanced (je nach Re-Entry-Modus).`;
    }

    // Last trade
    if (lastTrade && lastTradeEl && lastTradeSubEl) {
      lastTradeEl.textContent = `${lastTrade.action.split(" ")[0]} → ${fmtNumber(lastTrade.w*100)}%`;
      lastTradeSubEl.textContent = `${lastTrade.date} | Ratio ${fmtNumber(lastTrade.ratio)}`;
    } else if (lastTradeEl && lastTradeSubEl) {
      lastTradeEl.textContent = "–";
      lastTradeSubEl.textContent = "Seit Start keine Anpassung.";
    }

    // Performance vs HODL + Exposure chart
    const dates = d.slice(startIdx);
    const p = price.slice(startIdx).map(Number);
    const wPct = wArr.slice(startIdx).map(x => (x == null ? null : x*100));

    const holdEq = new Array(dates.length).fill(null);
    const stratEq = new Array(dates.length).fill(null);
    holdEq[0] = 1.0;
    stratEq[0] = 1.0;

    for (let i = 0; i < dates.length - 1; i++) {
      const p0 = p[i], p1 = p[i+1];
      const wi = wArr[startIdx + i];
      if (!isFinite(p0) || !isFinite(p1) || p0 <= 0 || wi == null) break;

      const retBTC = p1 / p0;
      holdEq[i+1] = (holdEq[i] ?? 1.0) * retBTC;

      const portRet = wi * retBTC + (1 - wi) * 1.0;
      stratEq[i+1] = (stratEq[i] ?? 1.0) * portRet;
    }

    const lastHold = holdEq[holdEq.length - 1];
    const lastStrat = stratEq[stratEq.length - 1];

    if (perfDiffEl && perfSubEl && perfTinyEl) {
      if (isFinite(lastHold) && isFinite(lastStrat) && lastHold > 0) {
        const diff = lastStrat / lastHold - 1;
        perfDiffEl.textContent = fmtPct(diff);
        perfDiffEl.style.color = (diff >= 0) ? "var(--ok)" : "var(--warn)";

        const ddStrat = maxDrawdown(stratEq);
        const ddHold = maxDrawdown(holdEq);

        perfSubEl.textContent =
          `Strat ${fmtPct(lastStrat-1)} | HODL ${fmtPct(lastHold-1)} | MaxDD Strat ${fmtPct(ddStrat)} | HODL ${fmtPct(ddHold)}`;
        perfTinyEl.textContent =
          `Strat ${fmtPct(lastStrat-1)} vs HODL ${fmtPct(lastHold-1)} (Δ ${fmtPct(diff)})`;
      } else {
        perfDiffEl.textContent = "–";
        perfSubEl.textContent = "Nicht genug Daten für Vergleich.";
        perfTinyEl.textContent = "–";
      }
    }

    const stratTraces = [
      { x: dates, y: wPct, name: "BTC-Quote (%)", mode: "lines", line: { color: COLORS.ratio, width: 2 }, yaxis: "y" },
      { x: dates, y: holdEq, name: "HODL (rel.)", mode: "lines", line: { color: COLORS.hold, width: 1.4 }, yaxis: "y2" },
      { x: dates, y: stratEq, name: "Strategie (rel.)", mode: "lines", line: { color: COLORS.strat, width: 2 }, yaxis: "y2" }
    ];

    const stratLayout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { l: 45, r: 45, t: 10, b: 30 },
      font: { size: 11, color: "rgba(255,255,255,.85)" },
      legend: {
        orientation: "h",
        x: 0, y: 1.12,
        xanchor: "left", yanchor: "top",
        bgcolor: "rgba(0,0,0,0)",
        font: { size: 10, color: "rgba(255,255,255,.78)" }
      },
      xaxis: { showgrid: true, gridcolor: "rgba(255,255,255,.06)", tickfont: { color: "rgba(255,255,255,.70)" } },
      yaxis:  { title: "BTC %", range: [0, 100], showgrid: true, gridcolor: "rgba(255,255,255,.08)", zerolinecolor: "rgba(255,255,255,.10)",
                tickfont: { color: "rgba(255,255,255,.70)" } },
      yaxis2: { title: "Value (rel.)", overlaying: "y", side: "right", showgrid: false, tickfont: { color: "rgba(255,255,255,.70)" } }
    };

    const stratConfig = { responsive: true, displaylogo: false, displayModeBar: false };

    if (!strategyChartInited) {
      Plotly.newPlot("strategyChart", stratTraces, stratLayout, stratConfig);
      strategyChartInited = true;
    } else {
      Plotly.react("strategyChart", stratTraces, stratLayout, stratConfig);
    }
  }

  if (btnApply) btnApply.addEventListener("click", computeStrategyAndRender);
  [strategySelect, startDateEl, startWeightEl, buyThEl, sellStartEl, reentryModeEl].forEach(el => {
    if (el) el.addEventListener("change", computeStrategyAndRender);
  });

  // init
  computeStrategyAndRender();

  // ----------------------------
  // Main/Explain Chart (Preis/Kanal/Ratio)
  // Hinweis: Falls #chart doppelt vorhanden ist, nimmt querySelectorAll den ersten.
  // ----------------------------
  const chartEls = document.querySelectorAll("#chart");
  const chartTarget = chartEls?.length ? chartEls[0] : null;

  if (chartTarget) {
    const fairZeroLine = new Array(de.length).fill(0);

    const traces = [
      // Row 1
      { x: d,  y: price,     name: "BTC Preis", mode: "lines", xaxis: "x",  yaxis: "y",
        line: { color: COLORS.price, width: 1.2 }, showlegend: true },
      { x: d,  y: fair,      name: "Fair (orig)", mode: "lines", xaxis: "x",  yaxis: "y",
        line: { color: COLORS.fair, width: 1.8 }, showlegend: true },
      { x: de, y: fairExt,   name: "Fair (ext)", mode: "lines", xaxis: "x",  yaxis: "y",
        line: { color: COLORS.fair, width: 1.2, dash: "dot" }, opacity: 0.85, showlegend: true },
      { x: de, y: peakLine,  name: "Obergrenze (Preis)", mode: "lines", xaxis: "x",  yaxis: "y",
        line: { color: COLORS.peak, width: 2, dash: "dash" }, showlegend: true },
      { x: de, y: troughLine,name: "Untergrenze (Preis)", mode: "lines", xaxis: "x",  yaxis: "y",
        line: { color: COLORS.trough, width: 2, dash: "dash" }, showlegend: true },

      // Row 2
      { x: d,  y: log10r,    name: "log10(R)", mode: "lines", xaxis: "x2", yaxis: "y2",
        line: { color: COLORS.log10r, width: 1.2 }, showlegend: true },
      { x: de, y: fairZeroLine, name: "Fair (R=1 → 0-Linie)", mode: "lines", xaxis: "x2", yaxis: "y2",
        line: { color: COLORS.fair, width: 1.4 }, showlegend: true },
      { x: de, y: peakLog,   name: "Obergrenze (log10)", mode: "lines", xaxis: "x2", yaxis: "y2",
        line: { color: COLORS.peak, width: 2, dash: "dash" }, showlegend: true },
      { x: de, y: troughLog, name: "Untergrenze (log10)", mode: "lines", xaxis: "x2", yaxis: "y2",
        line: { color: COLORS.trough, width: 2, dash: "dash" }, showlegend: true },

      // Row 3
      { x: d,  y: ratio,     name: "Kanal-Position (%)", mode: "lines", xaxis: "x3", yaxis: "y3",
        line: { color: COLORS.ratio, width: 1.9 }, showlegend: true },
      { x: d,  y: ratioFair, name: "Fair (transformiert → %)", mode: "lines", xaxis: "x3", yaxis: "y3",
        line: { color: COLORS.fair, width: 1.4, dash: "dot" }, showlegend: true, visible: "legendonly" },
    ];

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: isMobile ? { l: 46, r: 10, t: 18, b: 90 } : { l: 55, r: 20, t: 18, b: 85 },
      font: { size: isMobile ? 11 : 12, color: "rgba(255,255,255,.88)" },

      legend: {
        orientation: "h",
        x: 0, y: -0.25,
        xanchor: "left", yanchor: "top",
        font: { size: isMobile ? 10 : 11, color: "rgba(255,255,255,.82)" },
        bgcolor: "rgba(0,0,0,0)"
      },

      grid: { rows: 3, columns: 1, pattern: "independent", roworder: "top to bottom" },

      yaxis:  { title: "Preis", automargin: true, gridcolor: "rgba(255,255,255,.08)", zerolinecolor: "rgba(255,255,255,.10)" },
      yaxis2: { title: "log10(R)", automargin: true, gridcolor: "rgba(255,255,255,.08)", zeroline: true, zerolinewidth: 1, zerolinecolor: "rgba(255,255,255,.18)" },
      yaxis3: { title: "Position (%)", range: [0, 100], automargin: true, gridcolor: "rgba(255,255,255,.08)", zerolinecolor: "rgba(255,255,255,.10)" },

      xaxis:  { showticklabels: false, gridcolor: "rgba(255,255,255,.06)" },
      xaxis2: { matches: "x", showticklabels: false, gridcolor: "rgba(255,255,255,.06)" },
      xaxis3: {
        matches: "x",
        title: "Datum",
        showticklabels: true,
        gridcolor: "rgba(255,255,255,.06)",
        rangeslider: { visible: !isMobile }
      },

      dragmode: "pan",
    };

    const config = {
      responsive: true,
      scrollZoom: true,
      displaylogo: false,
      displayModeBar: true
    };

    Plotly.newPlot(chartTarget, traces, layout, config);
  }

  // Resize
  window.addEventListener("resize", () => {
    try {
      const chartEls2 = document.querySelectorAll("#chart");
      if (chartEls2?.length) Plotly.Plots.resize(chartEls2[0]);
    } catch {}
    try { Plotly.Plots.resize("expoChart"); } catch {}
    try { Plotly.Plots.resize("strategyChart"); } catch {}
    try { Plotly.Plots.resize("distChart"); } catch {}
  });

  // Update Button
  const btn = document.getElementById("btnUpdate");
  const statusEl = document.getElementById("updateStatus");

  if (btn) {
    btn.addEventListener("click", async () => {
      try {
        btn.disabled = true;
        btn.classList.add("loading");
        if (statusEl) statusEl.textContent = "Starte Update…";

        let token = localStorage.getItem("btc_update_token");
        if (!token) {
          token = prompt("Update-Token eingeben:");
          if (!token) throw new Error("Abgebrochen.");
          localStorage.setItem("btc_update_token", token);
        }

        const r = await fetch("/api/update", { method: "POST", headers: { "X-Update-Token": token } });
        const j = await r.json().catch(() => ({}));

        if (!r.ok || !j.ok) {
          if (r.status === 401) localStorage.removeItem("btc_update_token");
          throw new Error(j.error || `Update fehlgeschlagen (HTTP ${r.status})`);
        }

        if (statusEl) statusEl.textContent = `Update ok (${j.seconds}s) – lade neu…`;
        setTimeout(() => location.reload(), 350);

      } catch (e) {
        if (statusEl) statusEl.textContent = `Fehler: ${e.message}`;
      } finally {
        btn.disabled = false;
        btn.classList.remove("loading");
      }
    });
  }
}

main().catch((e) => {
  console.error(e);
  const metaEl = document.getElementById("meta");
  if (metaEl) metaEl.textContent = `Fehler beim Laden: ${e?.message || e}`;
});
