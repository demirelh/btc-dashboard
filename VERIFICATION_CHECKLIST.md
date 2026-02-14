# Verification Checklist

Use this checklist to verify the Streamlit modernization is working correctly.

## Pre-Launch Checklist

### ✅ Installation
- [ ] Python 3.9+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] No import errors when running `python -c "import streamlit"`

### ✅ Data Preparation
- [ ] File exists: `web/data/btc.json`
- [ ] If not, run: `python update.py`
- [ ] File size ~1.1 MB
- [ ] JSON is valid (can be loaded)

### ✅ Configuration
- [ ] File exists: `config/config.toml`
- [ ] File exists: `.streamlit/config.toml`
- [ ] Optional: `.env` file if needed

## Launch Verification

### ✅ App Starts
```bash
streamlit run app.py
```
- [ ] App starts without errors
- [ ] Opens browser at http://localhost:8501
- [ ] No Python exceptions in console

### ✅ Home Page (app.py)
- [ ] Page loads
- [ ] Title displays: "₿ BTC Peak/Trough Channel Dashboard"
- [ ] Quick overview shows:
  - [ ] Last close price
  - [ ] Channel position
  - [ ] Data through date
- [ ] Channel range displays
- [ ] Last updated timestamp shows

## Page-by-Page Verification

### ✅ Page 1: Dashboard (01_📊_Dashboard.py)
- [ ] **KPI Cards** (4 cards)
  - [ ] Price (Close) card
  - [ ] Channel Position card
  - [ ] Data status card
  - [ ] Live status card
- [ ] **Main Channel Chart**
  - [ ] Price line (gray)
  - [ ] Fair value line (green, dotted)
  - [ ] Peak line (red, dashed)
  - [ ] Trough line (blue, dashed)
  - [ ] Extended to 2030
  - [ ] Log scale y-axis
  - [ ] Interactive (zoom, pan)
- [ ] **Ratio Indicator Chart**
  - [ ] Purple filled area
  - [ ] 0-100% range
  - [ ] 50% reference line
- [ ] **About section** (expandable)
  - [ ] Explanation text loads
- [ ] **Auto-refresh checkbox** works

### ✅ Page 2: Strategy (02_⚙️_Strategy.py)
- [ ] **Sidebar Controls**
  - [ ] Sell Ladder dropdown (g0/g1/g2)
  - [ ] Sell Start slider (0-100)
  - [ ] Buy Threshold slider (0-100)
  - [ ] Re-Entry Mode dropdown
  - [ ] Start Date picker
  - [ ] Start Weight slider
- [ ] **Strategy Config Display**
  - [ ] Current ladder shown
  - [ ] Current position shown
  - [ ] Target exposure shown
  - [ ] Action tag (BUY/SELL/HOLD)
- [ ] **Exposure Curve Chart**
  - [ ] Purple curve
  - [ ] Current position marker (green dot)
  - [ ] Sell start line (vertical dashed)
- [ ] **Ratio Distribution**
  - [ ] Histogram
  - [ ] Mean line
  - [ ] ±1σ lines
  - [ ] Current position line
  - [ ] Statistics in title
- [ ] **Next Triggers**
  - [ ] Next sell trigger info
  - [ ] Next buy trigger info
  - [ ] Price estimates

### ✅ Page 3: Backtest (03_📈_Backtest.py)
- [ ] **Sidebar Controls** (same as Strategy)
- [ ] **Performance Metrics** (4 cards)
  - [ ] Strategy return
  - [ ] HODL return
  - [ ] Strategy max DD
  - [ ] HODL max DD
- [ ] **Performance Comparison**
  - [ ] Success/warning message
  - [ ] Performance delta shown
- [ ] **Equity Curves Chart**
  - [ ] BTC weight (left y-axis, purple)
  - [ ] HODL equity (right y-axis, gray)
  - [ ] Strategy equity (right y-axis, green)
  - [ ] Dual y-axis labels
- [ ] **Last Strategy Change**
  - [ ] Date shown
  - [ ] Action shown
  - [ ] Ratio shown
  - [ ] New weight shown
- [ ] **Detailed Analysis** (expandable)
  - [ ] Methodology explanation
- [ ] **Configuration Summary**
  - [ ] Strategy params
  - [ ] Backtest settings

### ✅ Page 4: Explanation (04_📚_Explanation.py)
- [ ] **Title and intro** load
- [ ] **Step 1: Power Law**
  - [ ] Formula displayed
  - [ ] Explanation text
  - [ ] Metrics (B, C)
- [ ] **Step 2: Ratio**
  - [ ] Formula displayed
  - [ ] Current ratio metrics
- [ ] **Step 3: Peak Detection**
  - [ ] Parameters listed
  - [ ] Purpose explained
- [ ] **Step 4: Linear Regression**
  - [ ] Formulas shown
  - [ ] Warning about extrapolation
- [ ] **Step 5: Channel Position**
  - [ ] Formula displayed
  - [ ] Interpretation guide
  - [ ] Current position display
  - [ ] Progress bar
  - [ ] Zone indicator (accumulation/neutral/distribution)
- [ ] **Summary diagram** placeholder
- [ ] **References** (expandable)
- [ ] **Interactive Exploration**
  - [ ] Date slider works
  - [ ] Selected date metrics update
  - [ ] Interpretation changes

## Functional Testing

### ✅ Navigation
- [ ] Sidebar navigation works
- [ ] All 4 pages accessible
- [ ] Page state persists
- [ ] No errors when switching pages

### ✅ Interactivity
- [ ] Sliders update immediately
- [ ] Dropdowns work
- [ ] Date picker works
- [ ] Buttons respond
- [ ] Checkboxes work
- [ ] Charts are interactive (zoom, pan, hover)

### ✅ Live Price Feed
- [ ] Starts automatically
- [ ] Price updates (may take 5-10 seconds)
- [ ] Source shown (Binance or Coinbase)
- [ ] Status indicator correct
- [ ] Fallback works if WebSocket blocked

### ✅ Caching
- [ ] First load takes 2-5 seconds
- [ ] Subsequent page loads < 1 second
- [ ] Charts render quickly
- [ ] Data doesn't reload on every interaction

### ✅ Calculations
Compare with legacy dashboard if available:
- [ ] Channel position matches
- [ ] Exposure weights match
- [ ] Backtest returns match
- [ ] Max drawdown matches
- [ ] Distribution stats match

## UI/UX Testing

### ✅ Theme & Styling
- [ ] Dark background
- [ ] Glassmorphic cards
- [ ] Colors match design (purple, green, red, blue)
- [ ] Gradients visible
- [ ] Shadows/depth visible
- [ ] Typography clear and readable
- [ ] Consistent spacing

### ✅ Responsive Design
Test at different widths:
- [ ] **Desktop (>980px)**: 4-column KPI grid
- [ ] **Tablet (700-980px)**: 2-column KPI grid
- [ ] **Mobile (<700px)**: 1-column layout
- [ ] Charts resize properly
- [ ] No horizontal scrolling
- [ ] Text readable on small screens

### ✅ Accessibility
- [ ] Tab navigation works
- [ ] Labels are descriptive
- [ ] Error messages are clear
- [ ] Loading spinners show
- [ ] Empty states have helpful messages

## Error Handling

### ✅ Edge Cases
- [ ] No data file: Shows helpful error
- [ ] Invalid date range: Shows error message
- [ ] Network error: Fallback works
- [ ] Invalid inputs: Prevented or caught
- [ ] Missing dependencies: Clear error message

### ✅ Performance
- [ ] Large date ranges don't crash
- [ ] Multiple rapid interactions work
- [ ] Memory usage stable
- [ ] No memory leaks on long sessions

## Cross-Browser Testing (if deploying)
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)
- [ ] Mobile browsers

## Deployment Verification (if deployed)
- [ ] Public URL works
- [ ] All pages load
- [ ] No CORS errors
- [ ] Assets load (charts, fonts)
- [ ] Performance acceptable
- [ ] Logs show no errors

## Documentation Verification
- [ ] README_STREAMLIT.md accurate
- [ ] MIGRATION_GUIDE.md helpful
- [ ] IMPLEMENTATION_SUMMARY.md complete
- [ ] Code comments clear
- [ ] Docstrings present

## Final Sign-Off

### Critical Issues (Must Fix)
- [ ] No import errors
- [ ] No Python exceptions
- [ ] All pages load
- [ ] Charts render
- [ ] Calculations correct

### Nice-to-Have (Can Fix Later)
- [ ] Live price connects immediately
- [ ] All browsers tested
- [ ] Performance optimized
- [ ] Documentation refined

---

## Verification Complete?

**Date**: __________

**Verified By**: __________

**Status**: ✅ Ready for Production / ⚠️ Needs Fixes / ❌ Not Ready

**Notes**:
```
(Add any issues found or observations here)
```

---

## Quick Test Command Sequence

```bash
# 1. Install
pip install -r requirements.txt

# 2. Generate data (if needed)
python update.py

# 3. Run tests
python tests/test_strategy.py

# 4. Launch app
streamlit run app.py

# 5. Open browser to http://localhost:8501

# 6. Click through all 4 pages

# 7. Change some parameters and verify charts update

# 8. ✅ Done!
```

---

**Use this checklist before deploying to production!**
