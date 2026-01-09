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

export function startLiveBTC(intervalMs = 5000) {
  setLiveText("Live: lade…");
  const wsUrl = "wss://stream.binance.com:9443/ws/btcusdt@trade";

  function connectWS() {
    try { if (liveWS) liveWS.close(); } catch {}
    liveWS = null;

    let ws;
    try { ws = new WebSocket(wsUrl); }
    catch {
      setLiveText("Live: - (WebSocket nicht möglich)");
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
      setLiveText("Live: - (reconnect…)");
      setTimeout(connectWS, 1500);
    };
  }

  connectWS();

  // Watchdog
  setInterval(() => {
    if (lastTick && (Date.now() - lastTick > 20000)) {
      try { liveWS?.close(); } catch {}
    }
  }, 5000);

  // USD-Fallback
  setInterval(async () => {
    try {
      if (lastTick && (Date.now() - lastTick < 8000)) return;
      const px = await fetchLiveBTC_CoinbaseUSD();
      if (px != null) setLivePrice(px, "USD", "Coinbase");
    } catch {
      if (!lastTick || (Date.now() - lastTick > 8000)) {
        setLiveText("Live: - (nicht verfügbar)");
      }
    }
  }, Math.max(2000, intervalMs));
}
