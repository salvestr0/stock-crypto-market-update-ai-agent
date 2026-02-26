"""GitHub developer activity — auto-selected based on trending narrative names.
Uses public API (60 req/hr unauthenticated). Set GITHUB_TOKEN in .env for 5000/hr.
"""
import os
import requests
from datetime import datetime, timedelta, timezone

GITHUB_API = "https://api.github.com"

# Protocol name → GitHub owner/repo
PROTOCOL_REPOS: dict[str, str] = {
    # Layer 1
    "bitcoin":        "bitcoin/bitcoin",
    "ethereum":       "ethereum/go-ethereum",
    "solana":         "solana-labs/solana",
    "avalanche":      "ava-labs/avalanchego",
    "bnb chain":      "bnb-chain/bsc",
    "cardano":        "input-output-hk/cardano-node",
    "polkadot":       "paritytech/polkadot-sdk",
    # Layer 2 / Scaling
    "arbitrum":       "OffchainLabs/nitro",
    "optimism":       "ethereum-optimism/optimism",
    "base":           "base-org/node",
    "zksync":         "matter-labs/zksync-era",
    "starknet":       "starkware-co/cairo-lang",
    "polygon":        "maticnetwork/bor",
    # DeFi
    "uniswap":        "Uniswap/v4-core",
    "aave":           "aave/aave-v3-core",
    "compound":       "compound-finance/compound-protocol",
    "morpho":         "morpho-org/morpho-blue",
    "curve":          "curvefi/curve-contract",
    "maker":          "makerdao/dss",
    "lido":           "lidofinance/lido-dao",
    "eigenlayer":     "Layr-Labs/eigenlayer-contracts",
    "pendle":         "pendle-finance/pendle-core-v2",
    # GameFi
    "axie":           "axieinfinity/ronin-client",
    "immutable":      "immutable/immutable-zkevm",
    # AI
    "fetch.ai":       "fetchai/uAgents",
    "ocean":          "oceanprotocol/ocean.py",
    "bittensor":      "opentensor-ai/bittensor",
    # Other
    "hyperliquid":    "hyperliquid-xyz/node",
    "sui":            "MystenLabs/sui",
    "aptos":          "aptos-labs/aptos-core",
    "near":           "near/nearcore",
    "cosmos":         "cosmos/cosmos-sdk",
    "celestia":       "celestiaorg/celestia-node",
    "sei":            "sei-protocol/sei-chain",
    "injective":      "InjectiveLabs/injective-core",
    "pyth":           "pyth-network/pyth-sdk-solidity",
    "chainlink":      "smartcontractkit/chainlink",
    "the graph":      "graphprotocol/graph-node",
}

# Narrative category keywords → protocol keys to include
_NARRATIVE_KEYWORDS: dict[str, list[str]] = {
    "defi":            ["uniswap", "aave", "compound", "morpho", "curve", "maker"],
    "lending":         ["aave", "compound", "morpho"],
    "dex":             ["uniswap", "curve"],
    "layer 2":         ["arbitrum", "optimism", "base", "zksync", "starknet", "polygon"],
    "layer 0":         ["cosmos", "polkadot", "celestia"],
    "data availab":    ["celestia", "near"],
    "gaming":          ["axie", "immutable"],
    "gamefi":          ["axie", "immutable"],
    "game studio":     ["axie", "immutable"],
    "ai":              ["fetch.ai", "ocean", "bittensor"],
    "nft":             ["immutable", "ethereum"],
    "restaking":       ["eigenlayer", "lido"],
    "liquid staking":  ["lido"],
    "morpho":          ["morpho"],
    "oracle":          ["chainlink", "pyth"],
    "yield":           ["pendle", "aave", "curve"],
}

# Always include these regardless of narratives
_BASE_REPOS = ["ethereum/go-ethereum", "solana-labs/solana"]


def _select_repos(narrative_names: list[str]) -> list[str]:
    """Return repo slugs relevant to the given narrative category names."""
    selected: set[str] = set(_BASE_REPOS)

    for name in narrative_names:
        nl = name.lower()
        # Direct protocol name match
        for proto, repo in PROTOCOL_REPOS.items():
            if proto in nl or nl in proto:
                selected.add(repo)
        # Keyword-based match
        for keyword, protos in _NARRATIVE_KEYWORDS.items():
            if keyword in nl:
                for p in protos:
                    if p in PROTOCOL_REPOS:
                        selected.add(PROTOCOL_REPOS[p])

    return list(selected)[:12]  # cap to stay well within rate limits


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    h = {"Accept": "application/vnd.github.v3+json"}
    if token:
        h["Authorization"] = f"token {token}"
    return h


def _repo_stats(repo: str) -> dict | None:
    h = _headers()

    info_r = requests.get(f"{GITHUB_API}/repos/{repo}", headers=h, timeout=10)
    if not info_r.ok:
        return None
    info = info_r.json()

    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    commits_r = requests.get(
        f"{GITHUB_API}/repos/{repo}/commits",
        headers=h,
        params={"since": since, "per_page": 100},
        timeout=10,
    )
    commits_7d = len(commits_r.json()) if commits_r.ok and isinstance(commits_r.json(), list) else 0

    return {
        "repo":        repo,
        "stars":       info.get("stargazers_count"),
        "forks":       info.get("forks_count"),
        "commits_7d":  commits_7d,
        "last_push":   (info.get("pushed_at") or "")[:10],
        "language":    info.get("language"),
    }


def get_developer_activity(narrative_names: list[str]) -> list[dict]:
    """Fetch GitHub commit activity for repos Sarah selects based on trending narratives."""
    repos   = _select_repos(narrative_names)
    results = []

    for repo in repos:
        try:
            stats = _repo_stats(repo)
            if stats:
                results.append(stats)
        except Exception:
            pass

    # Most active repos first
    results.sort(key=lambda x: x.get("commits_7d", 0), reverse=True)
    return results
