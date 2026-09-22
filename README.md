# Equities Lens

A 6-factor equity screener adapted from an altcoin screening framework
(narrative fit → tokenomics → real usage → volume legitimacy → team/backers
→ valuation vs peers), applied to public equities.

## How it works

- `screener.py` pulls data per ticker from Yahoo Finance (via `yfinance`)
  and scores 5 of the 6 factors automatically (0–2 scale). Narrative fit is
  a manual field in `data/watchlist.json` since it can't be automated.
- A GitHub Action (`.github/workflows/update-data.yml`) runs the screener
  weekly and commits the refreshed `data/results.json`.
- `index.html` / `style.css` / `app.js` are a static, no-build-step
  dashboard that reads `data/results.json` and renders it.

## Running it yourself

```bash
pip install -r requirements.txt
python screener.py          # writes data/results.json
python -m http.server 8000  # then open http://localhost:8000
```

## Editing the watchlist

Add/remove tickers and their narrative in `data/watchlist.json`:

```json
{
  "ticker": "AAPL",
  "sector_peers": ["MSFT", "GOOGL"],
  "narrative": "One-sentence thesis for why this is on the watchlist."
}
```

## Deploying

1. Push this repo to GitHub (public, so it's verifiable portfolio evidence).
2. Enable **GitHub Pages** in repo Settings → Pages → deploy from the `main`
   branch, root folder. No build step needed — it's static files.
3. Enable **Actions** if not already on, so the weekly data-refresh job runs.
4. First run: trigger the Action manually once (Actions tab → Update
   screener data → Run workflow) so `data/results.json` has real data
   before anyone visits the page.

## Framework mapping

| Crypto (original) | Equities (this tool) |
|---|---|
| Narrative fit | One-sentence thesis, manual |
| Tokenomics / unlocks | Share dilution vs buybacks |
| Real usage (TVL/revenue) | Revenue + earnings growth |
| Volume legitimacy | Short interest % of float |
| Team / backers | Institutional ownership % |
| Valuation vs peers | P/E vs sector-peer median |

Not investment advice — a research-note input tool, same as its crypto
counterpart.
