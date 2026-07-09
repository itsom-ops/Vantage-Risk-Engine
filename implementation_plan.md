# Vantage Risk Engine — Phase 2: Professional Financial Platform

Transform the prototype into a practical financial intelligence platform with Export Reports, Dedicated Stock Pages, In-App News Reading, and News Impact Predictions.

---

## User Review Required

> [!IMPORTANT]
> **New Dependencies Required**: This plan adds `jspdf`, `html2canvas`, and `date-fns` to the frontend. The backend gains `yfinance` for live stock price/OHLC data and `newspaper3k`/`beautifulsoup4` for article extraction. These will be installed via `npm install` and `pip install`.

> [!WARNING]
> **Backend API Changes**: 4 new endpoints will be added. No existing endpoints are modified or removed. The frontend gains 2 new route pages (`/stock/:ticker` and `/news/:id`). The existing Dashboard remains fully intact.

---

## Open Questions

> [!IMPORTANT]
> 1. **PDF Branding**: Should the exported PDF include a UBS logo or custom header image? Currently planned with text-only "Vantage Risk Engine" branding.
> 2. **Stock Data Source**: yfinance is free but rate-limited. Is this acceptable for the stock detail page, or do you have a paid data provider (Alpha Vantage, Polygon.io)?
> 3. **Article Extraction Limits**: Some news sites block scraping. The plan includes a graceful fallback to display the article summary + "Read on original site" link when extraction fails.

---

## Proposed Changes

### Component 1: Backend — New API Endpoints

New endpoints added to support stock market data, article extraction, and report generation. **No existing endpoints are modified.**

---

#### [NEW] [routes/stock_data.py](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-api/routes/stock_data.py)

New FastAPI router providing live stock market data via yfinance:

- `GET /stock/{ticker}/price-history?range=1d|1w|1m|3m|6m|1y|5y|max` — Returns OHLCV time series data
- `GET /stock/{ticker}/quote` — Returns current price, market cap, P/E, dividend yield, 52-week high/low, beta, average volume, daily change, percentage change

**Schema additions** in [schemas.py](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-api/models/schemas.py):
- `StockQuote` — current quote data (price, market_cap, pe_ratio, dividend_yield, week52_high, week52_low, beta, avg_volume, day_change, day_change_pct, open, high, low, close, volume)
- `PricePoint` — individual OHLCV candle (timestamp, open, high, low, close, volume)
- `PriceHistoryResponse` — list of PricePoints + metadata

---

#### [NEW] [routes/articles.py](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-api/routes/articles.py)

New FastAPI router for full article extraction:

- `POST /articles/extract` — Accepts `{ url: string }`, uses `newspaper3k` + `beautifulsoup4` to extract:
  - `title`, `author`, `publish_date`, `top_image`, `text` (full body), `source_domain`
  - Falls back to summary from DB if extraction fails

**Schema additions**:
- `ArticleContent` — extracted article fields
- `ArticleExtractionRequest` — input schema

---

#### [MODIFY] [main.py](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-api/main.py)

Register two new routers:
```python
from routes import stock_data, articles
app.include_router(stock_data.router)
app.include_router(articles.router)
```

#### [MODIFY] [requirements.txt](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-api/requirements.txt)

Add:
```
yfinance==0.2.38
newspaper3k==0.2.8
beautifulsoup4==4.12.3
lxml==5.2.2
```

---

### Component 2: Frontend — New Pages & Routes

---

#### [NEW] [src/pages/StockDetail.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/pages/StockDetail.tsx)

Full-page dedicated stock view (similar to Yahoo Finance / Bloomberg Terminal):

**Layout sections:**
1. **Header Bar**: Ticker, company name, current price, daily change (green/red), percentage change
2. **Time Range Selector**: Pill buttons for 1D, 1W, 1M, 3M, 6M, 1Y, 5Y, MAX
3. **Interactive Price Chart**: Recharts `AreaChart` with gradient fill, crosshair tooltip showing OHLCV
4. **Volume Chart**: Bar chart below price chart (synced x-axis)
5. **Key Statistics Grid**: 2-column grid with Open, High, Low, Close, Market Cap, P/E, Dividend Yield, 52W High, 52W Low, Avg Volume, Beta
6. **Risk Analysis Section**: Embeds existing `CompanyRiskGauge`, `RiskRadarChart`, `RiskMatrixGrid` components
7. **AI Summary**: Uses existing `/insight` endpoint for AI-generated stock overview
8. **News Feed**: Displays company news cards (clicking opens in-app article reader)
9. **Export Report Button**: Triggers PDF generation

**Navigation**: Back to Dashboard button in header. Accessible via `/stock/:ticker` route.

---

#### [NEW] [src/pages/ArticleReader.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/pages/ArticleReader.tsx)

In-app article reading experience:

**Layout:**
1. **Back Navigation**: ← Back to [TICKER] Stock Page
2. **Hero Section**: Featured image (full-width, max-height 400px), headline overlay
3. **Article Meta**: Publisher name, author, publication date
4. **Article Body**: Rendered with proper typography (serif font, 18px, 1.8 line-height, max-width 720px centered)
5. **Sentiment Badge**: Bullish/Bearish/Neutral tag with score
6. **Predicted Market Impact Section** (below article):
   - Historical price chart up to article publication time (solid line)
   - Predicted future movement (dotted line) based on sentiment score
   - Metrics: Sentiment Score, Confidence, Expected Impact (Low/Med/High), Estimated Movement (e.g., +2.4%)

---

#### [NEW] [src/components/PriceChart.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/components/PriceChart.tsx)

Reusable interactive stock price chart component using Recharts:
- `AreaChart` with gradient fill (green for up, red for down vs open)
- Crosshair tooltip with OHLCV data
- Volume bars overlay
- Responsive container

---

#### [NEW] [src/components/ExportReport.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/components/ExportReport.tsx)

PDF report generation component using `jspdf` + `html2canvas`:
- Renders a hidden report div with all metrics, charts, and analysis
- Captures it as canvas, converts to PDF
- Includes: Company header, executive summary, risk score gauge, all Altman Z ratios, SHAP drivers, risk matrix, news sentiment summary, generation timestamp
- Downloads as `{TICKER}_Risk_Report_{date}.pdf`

---

#### [NEW] [src/components/ImpactPredictor.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/components/ImpactPredictor.tsx)

News impact prediction visualization:
- Fetches 30-day price history up to article date
- Extends chart with 5-day dotted prediction line
- Direction and magnitude based on sentiment score:
  - Score > 0.8 → +3-5% predicted movement
  - Score 0.6-0.8 → +1-3%
  - Score 0.4-0.6 → ±0.5%
  - Score 0.2-0.4 → -1-3%
  - Score < 0.2 → -3-5%
- Displays sentiment score, confidence, impact level, estimated % movement

---

#### [MODIFY] [src/main.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/main.tsx)

Add routes:
```tsx
<Route path="/stock/:ticker" element={<StockDetail />} />
<Route path="/news/:ticker/:articleIndex" element={<ArticleReader />} />
```

#### [MODIFY] [src/api/api.ts](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/api/api.ts)

Add new API call functions and TypeScript interfaces:
- `getStockQuote(ticker)`, `getStockPriceHistory(ticker, range)`
- `extractArticle(url)`
- New interfaces: `StockQuote`, `PricePoint`, `PriceHistoryResponse`, `ArticleContent`

#### [MODIFY] [src/pages/Dashboard.tsx](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/pages/Dashboard.tsx)

Minimal changes:
- Company list items become `<Link to={/stock/${ticker}}>` navigation instead of inline detail panel
- News article headlines link to `/news/:ticker/:idx` instead of external URLs

#### [MODIFY] [package.json](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/package.json)

Add dependencies:
```json
"jspdf": "^2.5.1",
"html2canvas": "^1.4.1",
"date-fns": "^3.6.0"
```

---

### Component 3: Styling

#### [MODIFY] [src/index.css](file:///c:/Users/Om/OneDrive/Desktop/UBS_Project/vantage-risk-ui/src/index.css)

Add article reader typography:
```css
.article-body {
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: 18px;
  line-height: 1.8;
  max-width: 720px;
  margin: 0 auto;
  color: #1C1C1C;
}
```

---

## Execution Order

1. **Backend first**: `stock_data.py` + `articles.py` + schema updates + `main.py` router registration
2. **Frontend API layer**: New interfaces and API calls in `api.ts`
3. **Reusable components**: `PriceChart.tsx`, `ExportReport.tsx`, `ImpactPredictor.tsx`
4. **New pages**: `StockDetail.tsx`, `ArticleReader.tsx`
5. **Routing**: Update `main.tsx` with new routes
6. **Dashboard integration**: Update company list and news links to navigate to new pages
7. **Styling**: Article reader typography in `index.css`

---

## Verification Plan

### Automated Tests
```powershell
# Backend syntax check
python -m py_compile routes/stock_data.py routes/articles.py

# Frontend build
npm run build
```

### Manual Verification
- Click a company in the sidebar → navigates to `/stock/AAPL` with full stock detail page
- Time range buttons switch chart data (1D through MAX)
- Key statistics grid shows live market data
- "Export Report" button downloads a formatted PDF
- Click a news headline → opens in-app article reader with full text
- Below article, predicted market impact chart shows solid + dotted line
- Back navigation works cleanly between all pages
