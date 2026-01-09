export function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

export function fmtNumber(n) {
  try { return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 }); }
  catch { return String(n); }
}
export function fmtUSD(x){ return `${fmtNumber(x)} USD`; }
export function fmtPct(x){ return `${x>=0?"+":""}${fmtNumber(x*100)}%`; }

export function fmtDateTimeLocal(d) {
  return d.toLocaleString(undefined, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}

export function priceForRatioPct(ratioPct, lastTrough, lastPeak) {
  const w = lastPeak - lastTrough;
  if (!isFinite(w) || w <= 0) return null;
  return lastTrough + (ratioPct / 100) * w;
}

export function maxDrawdown(values){
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

export function meanStd(values){
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
