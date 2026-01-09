import {
  clamp,
  fmtNumber,
  fmtUSD,
  fmtPct,
  priceForRatioPct,
  maxDrawdown,
  meanStd
} from "./utils.js";

/** Sell ladder as function of ratio (g0/g1/g2) */
function sellWeight(r, sellStart, ladder) {
  if (!isFinite(r)) return 1.0;
  if (r <= sellStart) return 1.0;
  if (r >= 100) return 0.0;

  const width = 100 - sellStart;
  if (width <= 0) return 0.0;

  const x = clamp((r - sellStart) / width, 0, 1); // 0..1 im Sell-Bereich

  if (ladder === "g0") return clamp(1 - x * x, 0, 1); // soft: 1 - x²
  if (ladder === "g2") {
    const base = clamp(1 - x, 0, 1);
    return base * base; // aggressiv: (1-x)²
  }
  return clamp(1 - x, 0, 1); // g1: linear
}

/**
 * Target weight with *sell-only hysteresis* + re-entry logic:
 *
 * SELL-REGIME (r >= sellStart):
 *  - Zielquote folgt der Leiter, ABER: niemals hochkaufen innerhalb des Sell-Regimes
 *    => w = min(prevW, ladderWeight)
 *
 * BELOW sellStart:
 *  - instant: sofort 100%
 *  - wait: nur 100% wenn r <= buyTh, sonst HOLD (kein Buying)
 *  - gradual: unter sellStart schrittweise hoch (buyTh ungenutzt)
 */
function targetWeight(prevW, r, buyTh, sellStart, ladder, reentryMode) {
  if (!isFinite(r)) return prevW;

  // ✅ SELL-REGIME: nur runter, niemals hoch (Hysterese)
  if (r >= sellStart) {
    const wL = sellWeight(r, sellStart, ladder);
    return Math.min(prevW, wL);
  }

  // Below sellStart => re-entry zone
  if (reentryMode === "instant") return 1.0;

  if (reentryMode === "wait") {
    return (r <= buyTh) ? 1.0 : prevW; // no buying until buyTh
  }

  // gradual (buyTh unused): increase smoothly as ratio falls below sellStart
  // f: 0 at sellStart, 1 at 0
  const denom = Math.max(sellStart, 1e-9);
  const f = clamp((sellStart - r) / denom, 0, 1);
  const eased = f * f; // smooth
  return clamp(prevW + (1 - prevW) * eased, 0, 1);
}

function stepWeight(prevW, r, buyTh, sellStart, ladder, reentryMode) {
  const wT = targetWeight(prevW, r, buyTh, sellStart, ladder, reentryMode);
  const delta = wT - prevW;

  if (Math.abs(delta) <= 1e-12) return { w: prevW, action: "HOLD", tag: "hold" };
  if (delta > 0) return { w: wT, action: "BUY / REBALANCE UP", tag: "buy" };
  return { w: wT, action: "SELL / REBALANCE DOWN", tag: "sell" };
}

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
      annotations: [{ text: "Zu wenig Daten für Verteilung", xref: "paper", yref: "paper", x: 0.5, y: 0.5, showarrow: false }]
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
    { type: "line", xref: "x", yref: "paper", x0: p1, x1: p1, y0: 0, y1: 1, line: { color: "rgba(255,255,255,.28)", width: 1, dash: "dot" } }
  ];

  const annotations = [
    { x: mean, y: 1.05, xref: "x", yref: "paper", text: `μ ${fmtNumber(mean)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.85)" } },
    { x: m1, y: 1.05, xref: "x", yref: "paper", text: `-1σ ${fmtNumber(m1)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.75)" } },
    { x: p1, y: 1.05, xref: "x", yref: "paper", text: `+1σ ${fmtNumber(p1)}`, showarrow: false, font: { size: 11, color: "rgba(255,255,255,.75)" } }
  ];

  if (cur != null) {
    shapes.push({ type: "line", xref: "x", yref: "paper", x0: cur, x1: cur, y0: 0, y1: 1, line: { color: COLORS.strat, width: 2, dash: "dash" } });
    annotations.push({ x: cur, y: 1.05, xref: "x", yref: "paper", text: `Jetzt ${fmtNumber(cur)}`, showarrow: false, font: { size: 11, color: COLORS.strat } });
  }

  Plotly.react("distChart", traces, {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 48, r: 18, t: 22, b: 38 },
    font: { size: 11, color: "rgba(255,255,255,.85)" },
    bargap: 0.05,
    xaxis: { title: "Kanal-Position (%)", range: [0, 100], dtick: 10, showgrid: true, gridcolor: "rgba(255,255,255,.06)",
      tickfont: { color: "rgba(255,255,255,.70)" } },
    yaxis: { title: "Häufigkeit", showgrid: true, gridcolor: "rgba(255,255,255,.08)", zerolinecolor: "rgba(255,255,255,.10)",
      tickfont: { color: "rgba(255,255,255,.70)" } },
    shapes, annotations
  }, { responsive: true, displayModeBar: false, displaylogo: false });
}

function renderExposureVsRatioChart({ sellStart, ladder, rNow, wNow, reentryMode, COLORS }) {
  const hintEl = document.getElementById("expoHint");
  const ladderLabel =
    ladder === "g0" ? "g0 (1-x²)" :
    ladder === "g2" ? "g2 ((1-x)²)" : "g1 (1-x)";

  if (hintEl) {
    hintEl.textContent = `Sell ≥ ${sellStart} → Leiter ${ladderLabel} (sell-only) | Re-Entry: ${reentryMode}`;
  }

  const xs = [];
  const ys = [];
  for (let r = 0; r <= 100; r += 1) {
    xs.push(r);
    let wTarget = 1.0;
    if (r >= sellStart) wTarget = sellWeight(r, sellStart, ladder);
    ys.push(wTarget * 100);
  }

  const traces = [
    { x: xs, y: ys, name: "Leiter (theoretisch)", mode: "lines", line: { color: COLORS.ratio, width: 2.2 } },
    { x: [rNow], y: [wNow * 100], name: "Jetzt", mode: "markers", marker: { size: 9, color: COLORS.strat } }
  ];

  Plotly.react("expoChart", traces, {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 48, r: 18, t: 10, b: 35 },
    font: { size: 11, color: "rgba(255,255,255,.85)" },
    legend: { orientation: "h", x: 0, y: 1.18, xanchor: "left", yanchor: "top", bgcolor: "rgba(0,0,0,0)",
      font: { size: 10, color: "rgba(255,255,255,.78)" } },
    xaxis: { title: "Kanal-Position / Ratio (%)", range: [0, 100], showgrid: true, gridcolor: "rgba(255,255,255,.06)",
      tickfont: { color: "rgba(255,255,255,.70)" } },
    yaxis: { title: "BTC-Exposure (%)", range: [0, 100], showgrid: true, gridcolor: "rgba(255,255,255,.08)",
      zerolinecolor: "rgba(255,255,255,.10)", tickfont: { color: "rgba(255,255,255,.70)" } },
    shapes: [
      { type: "line", x0: sellStart, x1: sellStart, y0: 0, y1: 100, line: { color: "rgba(255,255,255,.22)", width: 1, dash: "dash" } }
    ]
  }, { responsive: true, displayModeBar: false, displaylogo: false });
}

function renderTag(tagEl, tag) {
  tagEl.classList.remove("buy","sell","hold");
  tagEl.classList.add(tag);
  tagEl.textContent = tag.toUpperCase();
}

export function initStrategyUI({ data, COLORS, lastPeak, lastTrough }) {
  const d = data.series.date;
  const price = data.series.price;
  const ratio = data.series.ratio;

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

  function setBuyThEnabled(reentryMode) {
    const enabled = (reentryMode === "wait");
    buyThEl.disabled = !enabled;
    if (buyHintEl) buyHintEl.textContent = enabled
      ? "Wird genutzt im Re-Entry Modus „Wait“."
      : "Nicht genutzt (nur im Modus „Wait“).";
  }

  function resetMiniTiles() {
    nextTriggerSellEl.textContent = "-";
    nextTriggerSellSubEl.textContent = "-";
    nextTriggerBuyEl.textContent = "-";
    nextTriggerBuySubEl.textContent = "-";
    lastTradeEl.textContent = "-";
    lastTradeSubEl.textContent = "-";
    perfDiffEl.textContent = "-";
    perfSubEl.textContent = "-";
    perfTinyEl.textContent = "-";
    ladderHintEl.textContent = "-";
  }

  function computeStrategyAndRender() {
    const ladder = String(strategySelect.value || "g1");
    const sellStart = Number(sellStartEl.value);
    const reentryMode = String(reentryModeEl.value || "instant");
    const buyTh = Number(buyThEl.value);
    const startDate = String(startDateEl.value || "2018-01-01");
    const startW = clamp(Number(startWeightEl.value) / 100, 0, 1);

    setBuyThEnabled(reentryMode);

    if (pillLabelEl) {
      const buyPart = (reentryMode === "wait") ? `buy${buyTh} | ` : "";
      pillLabelEl.textContent = `${buyPart}sell${sellStart} | reentry: ${reentryMode}`;
    }

    // Distribution since start
    const rNowForDist = Number(ratio[ratio.length - 1]);
    const startIdxForDist = d.findIndex(x => x >= startDate);
    renderRatioDistributionSinceStart({
      ratioSeries: startIdxForDist < 0 ? [] : ratio.slice(startIdxForDist),
      currentRatio: rNowForDist,
      startDateLabel: startDate,
      COLORS
    });

    if (!(sellStart > 0 && sellStart < 100)) {
      recWeightEl.textContent = "-";
      recActionEl.textContent = "Fehler: Sell Start muss > 0 und < 100 sein.";
      renderTag(recTagEl, "hold");
      resetMiniTiles();
      return;
    }

    if (reentryMode === "wait" && !(buyTh >= 0 && buyTh < sellStart)) {
      recWeightEl.textContent = "-";
      recActionEl.textContent = "Fehler: Im Modus „Wait“ muss BuyTh < SellStart sein.";
      renderTag(recTagEl, "hold");
      resetMiniTiles();
      return;
    }

    const startIdx = d.findIndex(x => x >= startDate);
    if (startIdx < 0) {
      recWeightEl.textContent = "-";
      recActionEl.textContent = "Startdatum liegt nach dem letzten Datenpunkt.";
      renderTag(recTagEl, "hold");
      resetMiniTiles();
      return;
    }

    if (startIdx >= d.length - 1) {
      const rNowFallback = Number(ratio[ratio.length - 1]);
      recWeightEl.textContent = `${fmtNumber(startW*100)}% BTC`;
      recActionEl.textContent = "Zu wenig Daten nach dem Startdatum für Performance.";
      renderTag(recTagEl, "hold");
      resetMiniTiles();
      renderExposureVsRatioChart({ sellStart, ladder, rNow: rNowFallback, wNow: startW, reentryMode, COLORS });
      return;
    }

    // Build weight series
    const wArr = new Array(d.length).fill(null);
    let w = startW;
    let lastTrade = null;

    for (let i = startIdx; i < d.length; i++) {
      const r = Number(ratio[i]);
      const step = stepWeight(w, r, buyTh, sellStart, ladder, reentryMode);
      const changed = Math.abs(step.w - w) > 1e-12;
      if (changed) lastTrade = { date: d[i], action: step.action, ratio: r, w: step.w, tag: step.tag };
      w = step.w;
      wArr[i] = w;
    }

    // current day action
    const rNow = Number(ratio[ratio.length - 1]);
    let wBefore = startW;
    for (let i = startIdx; i < d.length - 1; i++) {
      wBefore = stepWeight(wBefore, Number(ratio[i]), buyTh, sellStart, ladder, reentryMode).w;
    }
    const nowStep = stepWeight(wBefore, rNow, buyTh, sellStart, ladder, reentryMode);
    const wNow = wArr[d.length - 1];

    recWeightEl.textContent = `${fmtNumber(wNow*100)}% BTC`;
    recActionEl.textContent = `Jetzt (${d[d.length-1]} | Ratio ${fmtNumber(rNow)}): ${nowStep.action}`;
    renderTag(recTagEl, nowStep.tag);

    renderExposureVsRatioChart({ sellStart, ladder, rNow, wNow, reentryMode, COLORS });

    // ladder hint (for sell regime)
    const w50 = sellWeight(50, sellStart, ladder) * 100;
    const w70 = sellWeight(70, sellStart, ladder) * 100;
    const w90 = sellWeight(90, sellStart, ladder) * 100;
    ladderHintEl.textContent = `${fmtNumber(w50)}% / ${fmtNumber(w70)}% / ${fmtNumber(w90)}%`;

    // Next triggers
    const sellPrice0 = priceForRatioPct(sellStart, lastTrough, lastPeak);
    if (rNow < sellStart) {
      nextTriggerSellEl.textContent = `SELL: beginnt @ Ratio ${fmtNumber(sellStart)}`;
      nextTriggerSellSubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${sellPrice0 == null ? "-" : fmtUSD(sellPrice0)} — ab hier wird reduziert.`;

      if (reentryMode === "wait") {
        const buyPrice0 = priceForRatioPct(buyTh, lastTrough, lastPeak);
        nextTriggerBuyEl.textContent = `RE-ENTRY: 100% @ Ratio ${fmtNumber(buyTh)}`;
        nextTriggerBuySubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${buyPrice0 == null ? "-" : fmtUSD(buyPrice0)} — erst bei BuyTh wieder voll.`;
      } else if (reentryMode === "gradual") {
        const rDown = clamp(Math.floor(rNow - 1e-9), 0, 100);
        const buyPrice = priceForRatioPct(rDown, lastTrough, lastPeak);
        nextTriggerBuyEl.textContent = `UP: höhere BTC-Quote @ Ratio ${fmtNumber(rDown)}`;
        nextTriggerBuySubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${buyPrice == null ? "-" : fmtUSD(buyPrice)} — bei fallender Ratio wird schrittweise hochgekauft.`;
      } else {
        nextTriggerBuyEl.textContent = "BUY: unter SellStart = 100%";
        nextTriggerBuySubEl.textContent = "Instant Re-Entry: unter SellStart bleibt die Zielquote 100%.";
      }
    } else {
      const rUp = clamp(Math.ceil(rNow + 1e-9), sellStart, 100);
      const sellPrice = priceForRatioPct(rUp, lastTrough, lastPeak);
      nextTriggerSellEl.textContent = `DOWN: niedrigere BTC-Quote @ Ratio ${fmtNumber(rUp)}`;
      nextTriggerSellSubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${sellPrice == null ? "-" : fmtUSD(sellPrice)} — bei steigender Ratio weiter reduzieren.`;

      if (reentryMode === "wait") {
        const buyPrice0 = priceForRatioPct(buyTh, lastTrough, lastPeak);
        nextTriggerBuyEl.textContent = `RE-ENTRY: 100% erst @ Ratio ${fmtNumber(buyTh)}`;
        nextTriggerBuySubEl.textContent = `Preis-Schätzung (heutiger Kanal): ${buyPrice0 == null ? "-" : fmtUSD(buyPrice0)} — unter SellStart wird nicht gekauft bis BuyTh.`;
      } else if (reentryMode === "gradual") {
        nextTriggerBuyEl.textContent = `UP: unter SellStart schrittweise hoch`;
        nextTriggerBuySubEl.textContent = `Wenn Ratio unter ${fmtNumber(sellStart)} fällt, wird in Stufen hochgekauft (Gradual).`;
      } else {
        nextTriggerBuyEl.textContent = `BUY: unter SellStart sofort 100%`;
        nextTriggerBuySubEl.textContent = `Wenn Ratio unter ${fmtNumber(sellStart)} fällt, springt die Quote direkt auf 100% (Instant).`;
      }
    }

    if (lastTrade) {
      lastTradeEl.textContent = `${lastTrade.action.split(" ")[0]} → ${fmtNumber(lastTrade.w*100)}%`;
      lastTradeSubEl.textContent = `${lastTrade.date} | Ratio ${fmtNumber(lastTrade.ratio)}`;
    } else {
      lastTradeEl.textContent = "-";
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
      perfDiffEl.textContent = "-";
      perfSubEl.textContent = "Nicht genug Daten für Vergleich.";
      perfTinyEl.textContent = "-";
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
      legend: { orientation: "h", x: 0, y: 1.12, xanchor: "left", yanchor: "top", bgcolor: "rgba(0,0,0,0)",
        font: { size: 10, color: "rgba(255,255,255,.78)" } },
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

  btnApply.addEventListener("click", computeStrategyAndRender);
  [strategySelect, startDateEl, startWeightEl, buyThEl, sellStartEl, reentryModeEl].forEach(el => {
    el.addEventListener("change", computeStrategyAndRender);
  });

  computeStrategyAndRender();
}
