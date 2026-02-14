# Migration Guide: Legacy to Streamlit

This guide helps you migrate from the legacy HTML/JS dashboard to the new Streamlit version.

## Overview of Changes

### Architecture
- **Before**: Single-page HTML/JS app with vanilla JavaScript
- **After**: Multi-page Streamlit app with Python backend

### Data Flow
- **Before**: Client-side computation in JavaScript
- **After**: Server-side computation in Python with caching

### File Structure
```
Legacy (web/):              Modern (Streamlit):
├── index.html          →   ├── app.py (entry point)
├── js/                 →   ├── app/pages/ (multipage)
│   ├── app.js          →   │   ├── 01_Dashboard.py
│   ├── strategy.js     →   │   ├── 02_Strategy.py
│   └── utils.js        →   │   ├── 03_Backtest.py
├── css/                →   │   └── 04_Explanation.py
│   └── styles.css      →   ├── core/ (business logic)
└── data/               →   │   ├── strategy.py
    └── btc.json        →   │   ├── backtest.py
                        →   │   ├── data_store.py
                        →   │   └── price_feed.py
                        →   └── ui/ (components)
                        →       ├── theme.py
                        →       └── components.py
```

## Feature Parity Matrix

| Feature | Legacy | Streamlit | Notes |
|---------|--------|-----------|-------|
| Live Price (Binance WS) | ✅ | ✅ | Maintained |
| Live Price (Coinbase Fallback) | ✅ | ✅ | Maintained |
| Channel Chart | ✅ | ✅ | Enhanced with Plotly |
| Ratio Indicator | ✅ | ✅ | Separate chart |
| Sell Ladders (g0/g1/g2) | ✅ | ✅ | Same formulas |
| Re-entry Modes | ✅ | ✅ | instant/wait/gradual |
| Backtest vs HODL | ✅ | ✅ | Same algorithm |
| Ratio Distribution | ✅ | ✅ | Enhanced histogram |
| Exposure Curve | ✅ | ✅ | Interactive |
| Strategy Controls | ✅ | ✅ | In sidebar |
| Explanation Section | ✅ | ✅ | Dedicated page |
| Next Triggers | ✅ | ✅ | Calculated same way |
| Last Trade Info | ✅ | ✅ | Maintained |
| Dark Theme | ✅ | ✅ | Glassmorphic preserved |
| Responsive Design | ✅ | ✅ | Mobile-friendly |
| Update API | ✅ | ➖ | Use Python directly |

## Running Both Versions

You can run both the legacy and Streamlit versions simultaneously:

### Legacy Dashboard (Port 8080)
```bash
cd web
python -m http.server 8080
# Open http://localhost:8080
```

### Streamlit Dashboard (Port 8501)
```bash
streamlit run app.py
# Open http://localhost:8501
```

Both versions read from the same `web/data/btc.json` file.

## Key Differences

### 1. Live Price Updates

**Legacy**: JavaScript WebSocket with auto-reconnect
```javascript
const ws = new WebSocket("wss://stream.binance.com:9443/ws/btcusdt@trade");
ws.onmessage = (ev) => { ... };
```

**Streamlit**: Python WebSocket in background thread
```python
from core.price_feed import get_price_feed
price_feed = get_price_feed()
live_price = price_feed.get_latest_price()
```

### 2. Strategy Calculation

**Legacy**: Client-side JavaScript
```javascript
function sellWeight(r, sellStart, ladder) {
  const x = (r - sellStart) / (100 - sellStart);
  if (ladder === "g0") return 1 - x*x;
  // ...
}
```

**Streamlit**: Server-side Python
```python
class StrategyEngine:
    @staticmethod
    def sell_weight(ratio, sell_start, ladder):
        x = (ratio - sell_start) / (100 - sell_start)
        if ladder == "g0": return 1 - x*x
        # ...
```

### 3. Charts

**Legacy**: Plotly.js in browser
```javascript
Plotly.newPlot("chart", traces, layout, config);
```

**Streamlit**: Plotly Python
```python
import plotly.graph_objects as go
fig = go.Figure(data=traces)
st.plotly_chart(fig, use_container_width=True)
```

### 4. State Management

**Legacy**: JavaScript variables + localStorage
```javascript
let currentRatio = 65.2;
localStorage.setItem("token", token);
```

**Streamlit**: Session state + caching
```python
@st.cache_data(ttl=3600)
def load_data():
    return load_channel_data()
```

## Migration Steps for Users

### For End Users (Just Want to Use)
1. Install Python 3.9+
2. Clone repository
3. Run `pip install -r requirements.txt`
4. Run `python update.py` (first time only)
5. Run `streamlit run app.py`

### For Developers (Want to Customize)
1. **Keep Legacy**: Legacy code in `web/` is preserved
2. **Learn Streamlit**: Read [Streamlit docs](https://docs.streamlit.io)
3. **Modify Core**: Business logic in `core/` is UI-independent
4. **Customize UI**: Components in `ui/`, pages in `app/pages/`

## Configuration Changes

### Legacy (Environment Variables)
```bash
export BTC_UPDATE_TOKEN="your-token"
```

### Streamlit (config.toml)
```toml
# .env file
BTC_UPDATE_TOKEN=your-token

# config/config.toml
[strategy]
DEFAULT_LADDER = "g1"
DEFAULT_SELL_START = 46.0
```

## Deployment Changes

### Legacy Deployment
- Static web server (nginx, Apache, GitHub Pages)
- Optional Flask API for updates
- Client-side execution

### Streamlit Deployment
- Streamlit Cloud, Heroku, Railway, or Docker
- Server-side execution (needs Python runtime)
- Auto-scaling supported

## Performance Comparison

| Aspect | Legacy | Streamlit |
|--------|--------|-----------|
| Initial Load | Fast (static HTML) | Slower (Python startup) |
| Chart Rendering | Client-side (fast) | Server-side (network latency) |
| Computation | Client CPU | Server CPU |
| Caching | Browser cache | Server-side cache |
| Scalability | High (CDN) | Medium (server resources) |
| Maintenance | JS complexity | Python simplicity |

## When to Use Which

### Use Legacy Dashboard If:
- Need ultra-fast load times
- Want to host on static hosting (GitHub Pages, S3)
- Prefer client-side computation
- Have complex JavaScript requirements

### Use Streamlit Dashboard If:
- Want rapid development/iteration
- Prefer Python over JavaScript
- Need server-side data processing
- Want built-in state management
- Plan to add ML/data science features

## Troubleshooting Migration

### "Import errors"
```bash
pip install -r requirements.txt
```

### "No channel data"
Both versions need `web/data/btc.json`:
```bash
python update.py
```

### "Port already in use"
Change Streamlit port:
```bash
streamlit run app.py --server.port 8502
```

### "Legacy still needed"
Legacy code is preserved in `web/` directory. You can use both!

## Next Steps

1. **Test Streamlit locally**: `streamlit run app.py`
2. **Compare outputs**: Check that calculations match legacy
3. **Customize as needed**: Modify `config/config.toml`
4. **Deploy**: Choose deployment platform
5. **Monitor**: Check logs for errors

## Support

- **Legacy issues**: Check `web/README.md` (German)
- **Streamlit issues**: Check `README_STREAMLIT.md`
- **GitHub Issues**: Report bugs or request features

---

**Both versions are fully functional!** Choose based on your needs.
