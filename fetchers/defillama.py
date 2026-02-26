"""DeFiLlama — protocol TVL, chain activity, stablecoin supply.
All endpoints are public and require no API keys.
"""
import requests

LLAMA_BASE   = "https://api.llama.fi"
STABLE_BASE  = "https://stablecoins.llama.fi"


def get_protocol_tvl() -> list[dict]:
    """Top 20 DeFi protocols by TVL with 1d/7d change (>$100M TVL only)."""
    resp = requests.get(f"{LLAMA_BASE}/protocols", timeout=20)
    resp.raise_for_status()

    result = []
    for p in sorted(resp.json(), key=lambda x: x.get("tvl") or 0, reverse=True):
        tvl = p.get("tvl") or 0
        if tvl < 100_000_000:
            break
        if len(result) >= 20:
            break
        result.append({
            "name":          p.get("name"),
            "category":      p.get("category"),
            "tvl_usd":       round(tvl),
            "change_1d_pct": p.get("change_1d"),
            "change_7d_pct": p.get("change_7d"),
            "chains":        (p.get("chains") or [])[:3],
        })
    return result


def get_chain_tvl() -> list[dict]:
    """Top 10 blockchains by TVL with 1d/7d change."""
    resp = requests.get(f"{LLAMA_BASE}/v2/chains", timeout=15)
    resp.raise_for_status()

    result = []
    for c in sorted(resp.json(), key=lambda x: x.get("tvl") or 0, reverse=True)[:10]:
        tvl = c.get("tvl") or 0
        if tvl < 100_000_000:
            continue
        result.append({
            "name":          c.get("name"),
            "tvl_usd":       round(tvl),
            "change_1d_pct": c.get("change_1d"),
            "change_7d_pct": c.get("change_7d"),
        })
    return result


def get_stablecoin_supply() -> dict:
    """Total stablecoin market cap + top 5 by size. Rising supply = capital entering crypto."""
    resp = requests.get(f"{STABLE_BASE}/stablecoins?includePrices=true", timeout=15)
    resp.raise_for_status()
    assets = resp.json().get("peggedAssets", [])

    total = 0.0
    top   = []
    for s in sorted(assets, key=lambda x: (x.get("circulating") or {}).get("peggedUSD") or 0, reverse=True)[:5]:
        circ = (s.get("circulating") or {}).get("peggedUSD") or 0
        total += circ
        top.append({
            "symbol":          s.get("symbol"),
            "circulating_usd": round(circ),
        })

    return {
        "total_stablecoin_mcap_usd": round(total),
        "top_stablecoins":           top,
    }
