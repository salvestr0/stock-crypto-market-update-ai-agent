import os
from openai import OpenAI
from config import GROK_MODEL, CRYPTO_WATCHLIST

XAI_BASE_URL = "https://api.x.ai/v1"


def _setup_client() -> OpenAI:
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY is not set in your .env file")
    return OpenAI(api_key=api_key, base_url=XAI_BASE_URL)


def get_x_social_pulse() -> str:
    client = _setup_client()

    symbols = ", ".join(c["symbol"] for c in CRYPTO_WATCHLIST)
    prompt = f"""You have real-time access to X (Twitter). Search X right now and give me a sharp crypto social pulse report.

Focus on: {symbols}, plus any other crypto narratives gaining traction on X today.

Structure your response exactly like this:

🐦 X/SOCIAL PULSE
One sentence on the overall crypto mood on X right now — bullish, bearish, euphoric, fearful?

📣 WHAT CT IS TALKING ABOUT
3-4 bullet points on the dominant topics, memes, or debates on Crypto Twitter right now. Be specific — name coins, projects, or people if relevant.

💬 SENTIMENT BREAKDOWN
- BTC: [one line — bullish/bearish/neutral + what's being said]
- SOL: [one line]
- HYPE: [one line]

🔊 NOTABLE TAKES
1-2 standout posts or narratives from influential accounts (KOLs, founders, analysts) that are getting traction. Summarize the take and why it matters.

⚠️ NOISE TO IGNORE
What's being hyped on X right now that looks like low-signal noise or manipulation?

Rules:
- Pull from real posts on X, not from memory. Only report what is actually circulating today.
- Be specific. No generic filler.
- Keep total length under 300 words.
"""

    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
