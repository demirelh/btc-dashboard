# BTC Peak/Trough Channel Dashboard

A modern **Streamlit dashboard** for Bitcoin rebalancing strategy based on Peak/Trough channel analysis. This project provides:

- **Real-time price tracking** (Binance WebSocket + Coinbase fallback)
- **Power-law fair value model** with peak/trough detection
- **Configurable rebalancing strategies** (g0/g1/g2 ladders + re-entry modes)
- **Backtesting vs HODL** with performance metrics
- **Clean, modern UI** with dark glassmorphic theme

> ⚠️ **Disclaimer**: This tool is for educational and analytical purposes only. **Not financial advice**.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip or conda

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/demirelh/btc-dashboard.git
   cd btc-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate channel data** (first time only)
   ```bash
   python update.py
   ```

   This fetches historical BTC data from CoinCodex and computes the channel. Generates `web/data/btc.json` (~1.1 MB).

4. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**
   ```
   http://localhost:8501
   ```

---

## 📁 Project Structure

```
btc-dashboard/
├── app.py                      # Main Streamlit entry point
├── app/pages/                  # Streamlit multipage structure
│   ├── 01_📊_Dashboard.py     # Live KPIs & channel chart
│   ├── 02_⚙️_Strategy.py      # Strategy configuration & exposure curve
│   ├── 03_📈_Backtest.py      # Backtest results vs HODL
│   └── 04_📚_Explanation.py   # Channel derivation walkthrough
├── core/                       # Business logic (UI-independent)
│   ├── models.py              # Pydantic data models
│   ├── data_store.py          # Channel calculation & data loading
│   ├── price_feed.py          # Live price feed (WebSocket + REST)
│   ├── strategy.py            # Rebalancing strategy logic
│   ├── backtest.py            # Backtest engine
│   └── utils.py               # Helper functions
├── ui/                         # UI components & styling
│   ├── theme.py               # Streamlit theme & CSS injection
│   └── components.py          # Reusable UI components (charts, KPIs)
├── config/
│   └── config.toml            # Application configuration
├── web/                        # Legacy HTML/JS dashboard (preserved)
│   ├── index.html
│   ├── js/
│   └── data/
│       └── btc.json           # Channel data (generated)
├── update.py                   # Data update script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🎨 Features

### 1. Dashboard (Main Page)
- **Live Price**: Real-time BTC price from Binance WebSocket (USDT) with Coinbase fallback (USD)
- **KPI Cards**: Price, channel position, data status, live feed status
- **Main Chart**: Historical price with fair value, peak line, trough line, and projections to 2030
- **Ratio Indicator**: Channel position (0-100%) over time

### 2. Strategy Configuration
- **Sell Ladders**: Choose between g0 (soft), g1 (linear), g2 (aggressive)
- **Thresholds**: Configure sell start and buy threshold
- **Re-Entry Modes**: Instant, wait, or gradual
- **Exposure Curve**: Visual representation of target BTC % vs channel position
- **Ratio Distribution**: Histogram of historical channel positions

### 3. Backtest Engine
- **Performance Comparison**: Strategy vs HODL
- **Equity Curves**: Dual y-axis chart (weights + relative performance)
- **Metrics**: Total return, max drawdown, performance delta
- **Configuration**: Date range, initial weight, strategy parameters

### 4. Explanation & Education
- **Step-by-step derivation**: Power law → Ratio → Peak detection → Channel → Indicator
- **Mathematical formulas**: Clear explanations with examples
- **Interactive exploration**: Slider to explore historical dates
- **References**: Academic papers, technical docs, data sources

---

## 📊 Channel Model

### Power Law Fair Value
```
Fair Price = C × (days from genesis)^5.93
```

- **Genesis**: 2009-01-03 (Bitcoin's first block)
- **Exponent**: 5.93 (empirically fitted)

### Peak/Trough Detection
- **Algorithm**: scipy.signal.find_peaks
- **Parameters**: Prominence 0.28, Distance 600 days, Width 5 days
- **Linear Regression**: Fitted to peaks and troughs in log space

### Channel Position (Ratio)
```
Position (%) = ((Price - Trough) / (Peak - Trough)) × 100
```

- **0%**: At trough line (accumulation zone)
- **100%**: At peak line (distribution zone)

---

## 🔧 Configuration

### Strategy Parameters (config/config.toml)
```toml
[strategy]
DEFAULT_LADDER = "g1"           # g0, g1, g2
DEFAULT_SELL_START = 46.0       # Ratio % to start selling
DEFAULT_BUY_THRESHOLD = 14.0    # Ratio % for re-entry (wait mode)
DEFAULT_REENTRY_MODE = "instant" # instant, wait, gradual
DEFAULT_START_WEIGHT = 100.0    # Initial BTC %
DEFAULT_START_DATE = "2018-01-01"
```

### Channel Calculation (config/config.toml)
```toml
[channel]
B_EXP = 5.93                    # Power law exponent
GENESIS_DATE = "2009-01-03"
DATA_START = "2013-01-01"

[peak_detection]
PROMINENCE = 0.28
DISTANCE = 600
WIDTH = 5
```

---

## 🔄 Updating Data

### Manual Update
```bash
python update.py
```

This fetches the latest data from CoinCodex and regenerates `web/data/btc.json`.

### Programmatic Update
```python
from core.data_store import update_channel_data

# Update and save
update_channel_data(
    start="2013-01-01",
    output_path="web/data/btc.json"
)
```

### Scheduled Updates (Optional)
Set up a cron job or scheduled task:
```bash
# Daily at 2 AM
0 2 * * * cd /path/to/btc-dashboard && python update.py
```

---

## 🎯 Strategy Logic

### Sell Ladders (g0/g1/g2)
When `ratio >= sell_start`, calculate target weight:

- **g0 (Soft)**: `weight = 1 - x²` — Concave, maintains higher exposure longer
- **g1 (Linear)**: `weight = 1 - x` — Proportional reduction
- **g2 (Aggressive)**: `weight = (1 - x)²` — Convex, rapid exposure drop

Where `x = (ratio - sell_start) / (100 - sell_start)` (normalized 0-1)

### Re-Entry Modes
When `ratio < sell_start`:

- **Instant**: Immediately return to 100% BTC
- **Wait**: Only return to 100% when `ratio <= buy_threshold`
- **Gradual**: Smooth increase as ratio falls (quadratic easing)

### Sell-Only Hysteresis
Within the sell regime (`ratio >= sell_start`), the strategy **only reduces** exposure, never increases it. This prevents buying at peaks during volatility.

---

## 📈 Backtest Methodology

1. **Daily Rebalancing**: Portfolio adjusted at each day's close
2. **Two Assets**: BTC and cash/stablecoins (0% return assumed)
3. **No Fees**: Conservative assumption (add ~0.1-0.5% per trade in reality)
4. **No Slippage**: Trades at closing price
5. **Perfect Execution**: No implementation lag

### Metrics
- **Total Return**: Cumulative % gain/loss
- **Max Drawdown**: Largest peak-to-trough decline
- **Performance Delta**: Strategy return - HODL return

---

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
- **Separation of Concerns**: UI (Streamlit) is completely separate from business logic (core/)
- **Type Hints**: All functions use type annotations
- **Caching**: Streamlit `@cache_data` and `@cache_resource` for performance
- **Modularity**: Each page is a standalone module

---

## 🚨 Important Disclaimers

- **Not Financial Advice**: This tool is for educational purposes only
- **Past Performance ≠ Future Results**: Historical patterns may not repeat
- **Model Limitations**: Power law extrapolation is a simplification
- **Transaction Costs**: Real trading involves fees, slippage, taxes
- **Psychological Factors**: Execution requires discipline (fear/greed)
- **Highly Volatile Asset**: Bitcoin can experience significant drawdowns

**Use at your own risk. Do your own research. Never invest more than you can afford to lose.**

---

## 📝 License

MIT License

---

## 🙏 Acknowledgments

- **CoinCodex** for historical price data API
- **Binance** and **Coinbase** for live price feeds
- **Streamlit** for the amazing web framework
- **Plotly** for interactive charts
- **Bitcoin community** for power law research

---

## 🚀 Deployment

### Streamlit Cloud
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Set main file: `app.py`
5. Deploy

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

Build and run:
```bash
docker build -t btc-dashboard .
docker run -p 8501:8501 btc-dashboard
```

---

## 🐛 Troubleshooting

### "No channel data found"
- Run `python update.py` to generate `web/data/btc.json`
- Check file permissions on `web/data/` directory

### "WebSocket connection failed"
- Check internet connectivity
- Firewall may block WebSocket (port 9443)
- Fallback to Coinbase REST should activate automatically

### "Module not found"
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version: 3.9+ required

---

**Happy Trading! 🚀₿**
