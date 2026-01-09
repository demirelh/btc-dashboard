# btc-dashboard

Ein schlankes BTC-Dashboard, das den Bitcoin-Preis in einen **Peak/Trough-Kanal** einordnet und daraus eine **Kanal-Position (Ratio 0–100%)** ableitet. Auf Basis dieser Ratio liefert das Dashboard eine **Rebalancing-/Exposure-Empfehlung** (Sell-Leiter + Re-Entry-Modus) inkl. Charts, KPIs und Backtest-Vergleich vs. HODL.

> ⚠️ Hinweis: Das Projekt ist ein persönliches Analyse-/Dashboard-Tool und **keine Finanzberatung**.

---

## Features

- **Live-Preis Anzeige**
  - WebSocket (Binance BTCUSDT) + Fallback (Coinbase Spot)
- **Kanal-Logik**
  - Peak/Trough-Kanal (aus `data/btc.json`)
  - Ratio: Position im Kanal (0% = Trough, 100% = Peak)
- **Strategie: BTC-Exposure / Rebalancing**
  - Sell-Leiter: `g0`, `g1`, `g2`
    - `g0`: soft (1 − x²)
    - `g1`: linear (1 − x)
    - `g2`: aggressiv ((1 − x)²)
  - Re-Entry Modus:
    - `instant`: unter SellStart → direkt 100%
    - `wait`: erst bei BuyTh wieder 100%
    - `gradual`: unter SellStart schrittweise hoch
- **Backtest / Vergleich**
  - Strategie-Equity vs. HODL (seit Startdatum)
  - Max Drawdown (Strategie & HODL)
- **Charts**
  - Hauptchart (Preis + Kanal + Ratio)
  - Exposure-vs-Ratio Kurve
  - Exposure & Performance
  - Ratio-Verteilung (Histogramm)
- **Erklärbereich („Herleitung“)**
  - Preis → Kanal → Ratio → Zielquote (für Dritte nachvollziehbar)

---

## Projektstruktur

Typischer Aufbau:

btc-dashboard/
├─ web/
│  ├─ index.html
│  ├─ css/
│  │  └─ styles.css
│  ├─ js/
│  │  ├─ app.js
│  │  ├─ strategies.js        # (optional) Strategie-Logik ausgelagert
│  │  └─ ui.js                # (optional) UI/Render Helfer
│  └─ data/
│     └─ btc.json
├─ update.py                  # erzeugt/aktualisiert data/btc.json
├─ api_server.py              # stellt /api/update bereit (mit Token-Header)
└─ README.md

> Wenn du die Strategie-Logik oft änderst: empfehle `web/js/strategies.js`.
> Wenn UI-Charts stabil sind: `web/js/ui.js`.
> `app.js` bleibt dann hauptsächlich „Wiring“ (Daten laden, Events, orchestrieren).

---

## Voraussetzungen

- Python 3.x (für `update.py` und ggf. `api_server.py`)
- Ein Webserver oder Python-Server zum Ausliefern von `web/`
- Internetzugang (für Live-Preis / Datenupdate)

---

## Quickstart (lokal)

### 1) Frontend starten (einfacher static server)
Im Repo:

```bash
cd web
python3 -m http.server 8080
