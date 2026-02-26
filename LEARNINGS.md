# LEARNINGS.md — Mistake Log & Self-Updated Rules

## Purpose

Every time this agent makes a mistake — wrong call, missed signal, bad framing — it logs it here.
Then it updates its own rules. This file is a living document.
It is consulted before every run. It is updated after every correction.

---

## How to Log a Mistake

```
## [DATE] — [SHORT TITLE]

**What I said:** [the actual call or output]
**What happened:** [the real outcome]
**Root cause:** [why I was wrong]
**Rule update:** [what I will do differently now]
**Category:** [narrative timing / price structure / social signal / macro / data quality]
```

---

## Active Rules (Current Best Version)

These rules are updated every time a learning contradicts or refines them.

### On Narratives
- R1: A narrative is early when price hasn't moved. It is late when CT is posting threads about it.
- R2: Don't chase a narrative that is already in the "trending" section — it's priced in by the time it's visible.
- R3: The best narratives are ones where the tech has shipped but the market hasn't noticed yet.

### On Price Structure
- R4: Never call a bullish breakout unless volume is expanding. Low volume = trap.
- R5: When price is near ATH with declining volume — that is distribution, not consolidation.
- R6: A 10% green candle after days of red is not a trend reversal until confirmed with follow-through.

### On Social Signal (X/Grok)
- R7: Euphoric X sentiment with flat or declining price = be cautious. Distribution into retail.
- R8: Negative X sentiment with accumulating on-chain = be interested. Smart money vs. retail.
- R9: KOL posts are marketing until proven otherwise. Weight on-chain above influencer takes.

### On Macro
- R10: When DXY is rising and BTC is also rising — something is wrong. One of them is lying.
- R11: Risk-on in stocks does not automatically mean risk-on in crypto. Watch BTC.D first.
- R12: Fed language matters more than Fed action. Position before the meeting, not after.

### On Data Quality
- R13: CoinGecko categories with <$50M market cap are noise. Ignore for macro narrative reads.
- R14: 24h % change on low-cap tokens is not signal. Look at 7d and 30d with volume.
- R15: If a data fetch fails, do not hallucinate a fallback. State the gap clearly.

---

## Mistake Log

<!-- Most recent first -->

### [No mistakes logged yet — log begins after first correction]

---

## Graduated Rules (Retired)

<!-- Rules that got superseded or were found to be wrong -->
<!-- Move here with explanation of why they were retired -->
