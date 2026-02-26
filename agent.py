import os
import re
import json
from datetime import datetime, timezone
from google import genai
from config import GEMINI_MODEL


def _setup_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file")
    return genai.Client(api_key=api_key)


def generate_market_update(crypto_data: dict, stock_data: dict) -> tuple[str, str]:
    """Returns (crypto_message, stock_message) as two separate strings."""
    client = _setup_client()

    prompt = f"""You are a sharp, no-fluff financial analyst writing a daily market briefing for an active retail investor.

Below is today's raw market data. Analyze it and produce a concise, high-signal update.

--- RAW DATA ---
{json.dumps({"crypto": crypto_data, "stocks": stock_data}, indent=2, default=str)}
--- END DATA ---

Structure your response in EXACTLY two parts separated by the line ===STOCKS=== and nothing else.

PART 1 — Crypto (before ===STOCKS===):

📊 MARKET SNAPSHOT
2-3 sentences on overall market mood. Factor in DXY trend and yield curve status from the data.

🪙 CRYPTO WATCHLIST
For BTC, SOL, and HYPE — one line each: price, 24h change %, and one key insight.

🔮 DERIVATIVES SIGNALS
- BTC funding rate + basis: [leverage direction and contango/backwardation read]
- BTC put/call ratio: [> 1.0 = hedging/bearish, < 0.7 = bullish]
- BTC OI distribution: ATM vs OTM calls vs OTM puts — where is positioning concentrated?
- Taker volume bias: [BTC + ETH — BUYERS/SELLERS/NEUTRAL, confirms or contradicts price direction]
- ETH funding rate context
One concise line on what the full derivatives picture signals about near-term direction.

🔥 CRYPTO NARRATIVES — WHAT'S TRENDING
2-3 narratives seeing capital inflow. Use lifecycle_phase — flag EARLY (opportunity) vs PEAK (crowded) vs COOLING (exit watch).
Cross-reference: does DeFiLlama TVL or chain_tvl data confirm the narrative has real on-chain backing, or is it price-only speculation?

👨‍💻 DEVELOPER ACTIVITY
Which protocols show the most GitHub commits in the last 7 days? Flag any that are building hard while the market ignores them — divergence between dev activity and price is a setup signal.

💤 CRYPTO — WHAT'S BEING OVERLOOKED
Narratives/coins with EMERGING or NEUTRAL lifecycle phase. Cross-check: is stablecoin supply rising (capital ready to deploy) or falling (exiting)?

===STOCKS===

PART 2 — Stocks (after ===STOCKS===):

🌐 MACRO CONTEXT
- DXY: [level + trend + intraday move if significant_intraday=true → flag as post-release reaction]
- Yield curve: [spread, status, risk appetite implication]
- Stablecoin supply: [total + trend — rising = dry powder building, falling = capital exiting]

📈 STOCKS — SECTOR ROTATION
Top 3 and bottom 3 sectors by today's performance. Where is institutional money flowing?

🔍 STOCKS — TRENDS & HIDDEN MOVES
Trending themes. Overlooked setups.

📅 UPCOMING CATALYSTS
List the next 3-5 high-impact economic events from the calendar data (date, name, why it matters). Skip if no events in data.

⚡ TODAY'S ACTION ITEMS
3-5 specific, actionable bullet points across crypto and stocks.

Rules:
- Output the separator line ===STOCKS=== exactly as shown — nothing before or after it on that line.
- Be direct and specific. No generic filler.
- If a data field is missing or null, skip that line cleanly.
- Use plain text with section headers exactly as shown. No markdown tables.
- Keep each part under 350 words.
- Formatting: use *word* for bold (single asterisk). Use - for bullet points. NEVER use * as a bullet character.
"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = response.text

    if "===STOCKS===" in text:
        parts = text.split("===STOCKS===", 1)
        return parts[0].strip(), parts[1].strip()

    # Fallback: split at first stocks section header if delimiter missing
    for marker in ["📈 STOCKS", "STOCKS —", "STOCKS-"]:
        idx = text.find(marker)
        if idx != -1:
            return text[:idx].strip(), text[idx:].strip()

    # Last resort: return full text as crypto, empty stocks
    return text.strip(), ""


def generate_auto_correction(old_brain: str, crypto_data: dict, stock_data: dict) -> list[dict]:
    """Compare previous BRAIN.md hypotheses against fresh market data.

    Returns a list of dicts (one per invalidated hypothesis), each with keys:
        title, what_i_said, what_happened, root_cause, rule_update, category
    Returns an empty list if nothing was clearly wrong or if there is no prior brain.
    """
    if not old_brain or len(old_brain) < 100:
        return []

    # Quick check — skip if no active hypotheses were recorded
    if "No prior run" in old_brain or "Active Hypotheses" not in old_brain:
        return []

    client = _setup_client()

    prompt = f"""You are Sarah, a self-auditing market intelligence agent.

Below is your PREVIOUS BRAIN.md (from the last run) followed by TODAY'S fresh market data.

Your job: compare your previous active hypotheses (H1, H2, H3) and any specific price/regime calls
against what the market actually did. Identify only hypotheses that are CLEARLY WRONG or CLEARLY INVALIDATED
by the new data — not just uncertain or unresolved.

Be conservative. Only log a correction if the data clearly contradicts a specific, testable prediction.
If a hypothesis is still open, inconclusive, or directionally correct but off on timing — do NOT log it.

--- PREVIOUS BRAIN.md ---
{old_brain}
--- END PREVIOUS BRAIN ---

--- TODAY'S FRESH MARKET DATA ---
{json.dumps({"crypto": crypto_data, "stocks": stock_data}, indent=2, default=str)}
--- END FRESH DATA ---

Output a JSON array of corrections. Each correction must have exactly these fields:
  "title"        — short description, format: "[DATE] — [what was wrong]" where DATE is {datetime.now().strftime("%Y-%m-%d")}
  "what_i_said"  — the exact hypothesis or call from the previous brain
  "what_happened" — what the market actually did (be specific with prices/percentages)
  "root_cause"   — why the call was wrong (anchoring? wrong macro read? narrative timing? data quality?)
  "rule_update"  — one concrete rule Sarah should follow differently going forward
  "category"     — one of: narrative timing / price structure / social signal / macro / data quality

If there are no clearly invalidated hypotheses, output exactly: []

Output only the JSON array, nothing else. No prose before or after it.
"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = response.text.strip()

    # Strip markdown code fences if model wrapped output
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    return []


def generate_brain_update(crypto_data: dict, stock_data: dict, analysis: str) -> str:
    """Generate a fully populated BRAIN.md based on current run data. Returns entire file content."""
    client = _setup_client()

    prompt = f"""You are a market intelligence agent updating your live working memory file after a market analysis run.

Today's date/time: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Below is the raw market data and the analysis you just produced. Your job is to output a fully populated BRAIN.md file.
Replace every placeholder in brackets with real, specific content based on the data. Be precise — no generic filler.

--- RAW DATA ---
{json.dumps({"crypto": crypto_data, "stocks": stock_data}, indent=2, default=str)}
--- END DATA ---

--- TODAY'S ANALYSIS ---
{analysis}
--- END ANALYSIS ---

Output the complete BRAIN.md file content using exactly this structure. Fill in every field with real data:

# BRAIN.md — Live Working Memory

## Purpose

This is the agent's active mental state. It is overwritten on every run.
It represents what the agent currently believes, what it is tracking, and what it is watching for.

---

## Last Updated
`{datetime.now().strftime("%Y-%m-%d %H:%M")}`

---

## Current Market Regime

```
Risk Appetite:     [ RISK-ON / RISK-OFF / NEUTRAL — pick one and state why in 3-5 words ]
BTC Trend:         [ UPTREND / DOWNTREND / RANGING — pick one ]
BTC Dominance:     [ RISING / FALLING / FLAT ] → [ one-line implication for alts ]
Alt Season:        [ EARLY / ACTIVE / LATE / NONE ]
Macro Backdrop:    [ one sentence on the dominant macro force today ]
VIX Level:         [ number + one-word interpretation: low/elevated/spiking ]
DXY Trend:         [ direction + one-line crypto implication ]
```

---

## Active Hypotheses

```
H1: [specific, testable hypothesis about price or narrative] — Confidence: [LOW/MEDIUM/HIGH] — Status: [FORMING/ACTIVE/INVALIDATED]
H2: [specific, testable hypothesis] — Confidence: [LOW/MEDIUM/HIGH] — Status: [FORMING/ACTIVE/INVALIDATED]
H3: [specific, testable hypothesis] — Confidence: [LOW/MEDIUM/HIGH] — Status: [FORMING/ACTIVE/INVALIDATED]
```

---

## Watchlist — High Priority

| Asset / Sector | Why I'm Watching | Trigger to Act |
|----------------|-----------------|----------------|
| BTC | [specific reason from today's data] | [specific price level or event] |
| SOL | [specific reason] | [specific trigger] |
| HYPE | [specific reason] | [specific trigger] |
| [top sector from today] | [reason] | [trigger] |

---

## Narrative Tracker

```
HEATING UP (early, not crowded):
- [specific narrative with brief evidence]

PEAK ATTENTION (crowded, watch for exit):
- [specific narrative]

COOLING DOWN (fading, any reversal?):
- [specific narrative]

OVERLOOKED (no CT attention, but data is interesting):
- [specific narrative]
```

---

## Open Questions

1. [specific question the data raised but didn't answer]
2. [specific question]
3. [specific question]

---

## What I Was Wrong About Last Run

`[If this is the first run: "No prior run to review." Otherwise: brief summary of last error.]`

---

## What I Am Most Confident About Right Now

`[One or two sentences — the single clearest, highest-conviction signal in today's data. Be specific.]`
"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


def generate_self_review(brain_content: str) -> str:
    """Review current brain state and produce a log entry to prepend to SELF-REVIEW.md."""
    client = _setup_client()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    prompt = f"""You are a self-auditing market agent running a 4-hour accountability review.

Current timestamp: {timestamp}

Below is your current BRAIN.md — your live working memory from the last market update run.
Review it critically. Reflect on whether the hypotheses and regime calls hold up.
Flag what may have played out, what looks shaky, and what you'd change in your framing.

--- BRAIN.md ---
{brain_content}
--- END BRAIN.md ---

Produce a single review log entry in exactly this format (no extra commentary before or after):

---

**TIMESTAMP: {timestamp}**

**1. WHAT DID I CALL?**
- [list the specific hypotheses, regime calls, and watchlist triggers from the brain above]

**2. WHAT DO I NEED TO WATCH NEXT?**
- [what specific data or price moves would confirm or invalidate H1/H2/H3]

**3. WHAT LOOKS SHAKY?**
- [which calls feel weakest or most likely to be wrong — be honest]

**4. WHY MIGHT I BE WRONG?**
- [root cause: anchoring? missing data? narrative bias? recency effect?]

**5. WHAT CHANGES IN THE NEXT UPDATE?**
- [one concrete adjustment to weighting, framing, or focus]

---
"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


def answer_question(question: str, soul: str, brain: str, learnings: str,
                    history: list[dict] | None = None) -> str:
    """Answer a freeform question using agent persona, current memory, and conversation history."""
    client = _setup_client()

    rules_start = learnings.find("## Active Rules")
    rules_end   = learnings.find("## Mistake Log")
    if rules_start != -1 and rules_end != -1:
        active_rules = learnings[rules_start:rules_end].strip()
    elif rules_start != -1:
        active_rules = learnings[rules_start:rules_start + 2000].strip()
    else:
        active_rules = learnings[:2000]

    # Format recent conversation so Sarah remembers context
    history_block = ""
    if history:
        lines = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Sarah"
            lines.append(f"{role}: {msg['content']}")
        history_block = "\n--- RECENT CONVERSATION ---\n" + "\n".join(lines) + "\n--- END CONVERSATION ---\n"

    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    prompt = f"""You are Sarah, a market intelligence agent answering a question from your operator.
Answer in your own voice, grounded in your current market state and operating rules.
Be direct, specific, and useful. No filler. No hedging.
Use the conversation history to maintain context across follow-up messages.
Use single *bold* for emphasis (Telegram markdown format — single asterisk only, never double).

CURRENT TIME: {current_utc}
(Use this for any time-related questions. Do NOT use the Last Updated field in BRAIN.md as a proxy for the current time.)

--- WHO YOU ARE (SOUL.md) ---
{soul}
--- END SOUL ---

--- YOUR CURRENT BRAIN STATE (BRAIN.md) ---
{brain}
--- END BRAIN ---

--- YOUR ACTIVE RULES (from LEARNINGS.md) ---
{active_rules}
--- END RULES ---
{history_block}
CURRENT QUESTION: {question}

Answer:"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text
