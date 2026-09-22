"""
Equities Lens — 6-factor screener.

Adapts Reagan's crypto altcoin screening framework (narrative fit, tokenomics,
real usage, volume legitimacy, team/backers, valuation vs peers) to equities.

Runs via GitHub Actions (which has full internet access) on a schedule,
pulls data from Yahoo Finance via yfinance, scores each ticker on 5 of the
6 factors automatically, and writes results to data/results.json for the
static frontend to render. Narrative fit is the one factor that can't be
automated — it's a manual field editors fill in via watchlist.json.
"""
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

DATA_DIR = Path(__file__).parent / "data"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
RESULTS_PATH = DATA_DIR / "results.json"


def load_watchlist() -> list[dict]:
    """Each entry: {"ticker": "AAPL", "sector_peers": ["MSFT","GOOGL"], "narrative": "..."}"""
    with open(WATCHLIST_PATH) as f:
        return json.load(f)


def score_dilution(info: dict, shares_history) -> dict:
    """Tokenomics equivalent: is share count growing (dilution) or shrinking (buybacks)?"""
    try:
        if shares_history is None or len(shares_history) < 2:
            return {"score": None, "detail": "Insufficient share history", "raw": None}
        first, last = shares_history[0], shares_history[-1]
        pct_change = (last - first) / first * 100
        if pct_change <= -2:
            score, label = 2, "Buying back shares (shrinking float)"
        elif pct_change <= 2:
            score, label = 1, "Roughly flat"
        else:
            score, label = 0, "Diluting shareholders"
        return {"score": score, "detail": label, "raw": round(pct_change, 2)}
    except Exception as e:
        return {"score": None, "detail": f"Error: {e}", "raw": None}


def score_usage(info: dict) -> dict:
    """Real usage equivalent: revenue growth + earnings growth (is the business actually growing?)."""
    try:
        rev_growth = info.get("revenueGrowth")
        earn_growth = info.get("earningsGrowth")
        if rev_growth is None and earn_growth is None:
            return {"score": None, "detail": "No growth data available", "raw": None}
        vals = [v for v in [rev_growth, earn_growth] if v is not None]
        avg = statistics.mean(vals)
        if avg >= 0.15:
            score, label = 2, "Strong growth"
        elif avg >= 0:
            score, label = 1, "Modest/flat growth"
        else:
            score, label = 0, "Shrinking"
        return {
            "score": score,
            "detail": label,
            "raw": {"revenue_growth": rev_growth, "earnings_growth": earn_growth},
        }
    except Exception as e:
        return {"score": None, "detail": f"Error: {e}", "raw": None}


def score_volume(info: dict) -> dict:
    """Volume legitimacy equivalent: short interest as % of float (crowded/legit trading vs quiet)."""
    try:
        short_pct = info.get("shortPercentOfFloat")
        if short_pct is None:
            return {"score": None, "detail": "No short-interest data available", "raw": None}
        pct = short_pct * 100
        if pct > 20:
            score, label = 0, "Very high short interest — crowded/contested trade"
        elif pct > 8:
            score, label = 1, "Elevated short interest — worth watching"
        else:
            score, label = 2, "Normal short interest"
        return {"score": score, "detail": label, "raw": round(pct, 2)}
    except Exception as e:
        return {"score": None, "detail": f"Error: {e}", "raw": None}


def score_team(info: dict) -> dict:
    """Team/backers equivalent: institutional ownership % (smart money doing due diligence)."""
    try:
        inst_pct = info.get("heldPercentInstitutions")
        if inst_pct is None:
            return {"score": None, "detail": "No institutional ownership data", "raw": None}
        pct = inst_pct * 100
        if pct >= 60:
            score, label = 2, "Heavy institutional backing"
        elif pct >= 25:
            score, label = 1, "Some institutional backing"
        else:
            score, label = 0, "Low institutional backing"
        return {"score": score, "detail": label, "raw": round(pct, 2)}
    except Exception as e:
        return {"score": None, "detail": f"Error: {e}", "raw": None}


def score_valuation(info: dict, peer_infos: list[dict]) -> dict:
    """Valuation vs peers equivalent: P/E relative to sector peers' median P/E."""
    try:
        pe = info.get("trailingPE")
        peer_pes = [p.get("trailingPE") for p in peer_infos if p.get("trailingPE")]
        if pe is None or not peer_pes:
            return {"score": None, "detail": "Insufficient P/E data", "raw": None}
        peer_median = statistics.median(peer_pes)
        ratio = pe / peer_median if peer_median else None
        if ratio is None:
            return {"score": None, "detail": "Could not compute", "raw": None}
        if ratio <= 0.85:
            score, label = 2, "Cheap vs peers"
        elif ratio <= 1.15:
            score, label = 1, "In line with peers"
        else:
            score, label = 0, "Expensive vs peers"
        return {
            "score": score,
            "detail": label,
            "raw": {"pe": pe, "peer_median_pe": round(peer_median, 2)},
        }
    except Exception as e:
        return {"score": None, "detail": f"Error: {e}", "raw": None}


def screen_ticker(entry: dict) -> dict:
    ticker = entry["ticker"]
    t = yf.Ticker(ticker)
    info = t.info

    # Share history for dilution check (last ~2 years of quarterly data)
    try:
        shares_df = t.get_shares_full(start=None)
        shares_history = shares_df.tolist() if shares_df is not None else None
    except Exception:
        shares_history = None

    peer_infos = []
    for peer_ticker in entry.get("sector_peers", []):
        try:
            peer_infos.append(yf.Ticker(peer_ticker).info)
        except Exception:
            continue

    factors = {
        "narrative_fit": {
            "score": None,
            "detail": entry.get("narrative", "Not filled in yet — manual field."),
            "raw": None,
            "manual": True,
        },
        "dilution": score_dilution(info, shares_history),
        "usage": score_usage(info),
        "volume_legitimacy": score_volume(info),
        "team_backers": score_team(info),
        "valuation": score_valuation(info, peer_infos),
    }

    numeric_scores = [f["score"] for f in factors.values() if f["score"] is not None]
    overall = round(statistics.mean(numeric_scores), 2) if numeric_scores else None

    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "sector": info.get("sector"),
        "price": info.get("currentPrice"),
        "overall_score": overall,
        "overall_max": 2,
        "factors": factors,
    }


def main():
    watchlist = load_watchlist()
    results = []
    for entry in watchlist:
        try:
            results.append(screen_ticker(entry))
        except Exception as e:
            results.append({"ticker": entry["ticker"], "error": str(e)})

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework": [
            "narrative_fit", "dilution", "usage", "volume_legitimacy",
            "team_backers", "valuation",
        ],
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(results)} results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
