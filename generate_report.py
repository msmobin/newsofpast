#!/usr/bin/env python3
"""
War Room Daily Intelligence Generator
Fetches live news via Anthropic API + web_search, renders daily HTML report,
and regenerates the calendar index. Running multiple times on the same day
overwrites that day's report with the latest data.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.resolve()
NEWS_DIR  = BASE / "news"
DATA_FILE = BASE / "data" / "reports.json"
INDEX_FILE = BASE / "index.html"

load_dotenv(BASE / ".env")
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

TODAY = date.today().isoformat()          # e.g. "2026-04-24"
NOW   = datetime.now().strftime("%I:%M %p %Z").strip()
RUN_TS = datetime.now().strftime("%B %d, %Y — %I:%M %p")

# ── Market & index URL map (for clickable strip items) ────────────────────
MARKET_URLS = {
    "S&P 500":    "https://finance.yahoo.com/quote/%5EGSPC",
    "Nasdaq":     "https://finance.yahoo.com/quote/%5EIXIC",
    "Brent":      "https://finance.yahoo.com/quote/BZ%3DF",
    "WTI":        "https://finance.yahoo.com/quote/CL%3DF",
    "Gold":       "https://finance.yahoo.com/quote/GC%3DF",
    "Nat. Gas":   "https://finance.yahoo.com/quote/NG%3DF",
    "VIX":        "https://finance.yahoo.com/quote/%5EVIX",
    "10-Yr UST":  "https://finance.yahoo.com/quote/%5ETNX",
    "USD Index":  "https://finance.yahoo.com/quote/DX-Y.NYB",
    "LMT":        "https://finance.yahoo.com/quote/LMT",
    "XOM":        "https://finance.yahoo.com/quote/XOM",
    "DAL":        "https://finance.yahoo.com/quote/DAL",
}

# ── Source URL map (for clickable badges) ─────────────────────────────────
SOURCE_URLS = {
    "src-cnn":      "https://www.cnn.com",
    "src-alj":      "https://www.aljazeera.com",
    "src-cnbc":     "https://www.cnbc.com",
    "src-bloomberg":"https://www.bloomberg.com",
    "src-reuters":  "https://www.reuters.com",
    "src-wapo":     "https://www.washingtonpost.com",
    "src-wsj":      "https://www.wsj.com",
    "src-ft":       "https://www.ft.com",
    "src-nyt":      "https://www.nytimes.com",
    "src-ms":       "https://www.morganstanley.com/ideas",
    "src-fool":     "https://www.fool.com",
    "src-nbcnews":  "https://www.nbcnews.com",
    "src-cbsnews":  "https://www.cbsnews.com",
    "src-bbc":      "https://www.bbc.com/news",
    "src-ap":       "https://apnews.com",
    "src-schwab":   "https://www.schwab.com/learn",
    "src-yahoo":    "https://finance.yahoo.com",
}

# ── Search helper ──────────────────────────────────────────────────────────
def search(client: anthropic.Anthropic, query: str) -> str:
    """Run a single web-search query via Claude and return the text result."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}],
    )
    # Collect all text blocks from the response
    parts = []
    for block in resp.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts).strip()


# ── Data gathering ─────────────────────────────────────────────────────────
def gather_news(client: anthropic.Anthropic) -> dict:
    print("  [1/4] Fetching war & conflict news …")
    war = search(client,
        f"Today {TODAY}: Latest US-Iran war news headlines, military updates, "
        "Strait of Hormuz, ceasefire status, diplomatic developments. "
        "Give 6-8 key stories with source names, times, and 2-3 sentence summaries.")

    print("  [2/4] Fetching business & economy impact …")
    biz = search(client,
        f"Today {TODAY}: US-Iran war economic and business impact — oil prices, "
        "fuel surcharges, supply chain, corporate earnings effects, "
        "Gulf GDP, energy market disruption, consumer impact. "
        "Give 5-6 stories with source names and summaries.")

    print("  [3/4] Fetching stock market news …")
    mkt = search(client,
        f"Today {TODAY}: US stock market reaction to Iran war — S&P 500, Nasdaq, "
        "energy sector performance, defense stocks, market sentiment, "
        "analyst outlooks. Key numbers and percentages. "
        "Give 5-6 stories with source names and summaries.")

    print("  [4/4] Fetching stock buy/sell recommendations …")
    stk = search(client,
        f"Today {TODAY}: Analyst stock recommendations in US-Iran war environment — "
        "defense stocks (LMT RTX NOC GD), energy stocks (XOM CVX OXY FANG BP), "
        "gold (GLD), stocks to avoid (airlines, consumer discretionary). "
        "Include price targets, upside %, and the specific news/evidence behind each call.")

    return {"war": war, "biz": biz, "mkt": mkt, "stk": stk}


# ── Ask Claude to structure the data into JSON ─────────────────────────────
def structure_data(client: anthropic.Anthropic, raw: dict) -> dict:
    print("  [5/5] Structuring data …")
    prompt = f"""
You are a financial and geopolitical analyst. Based on the raw research below,
produce a single JSON object (no markdown, no code fences) with this exact schema:

{{
  "headline_of_day": "one-sentence most important story of the day",
  "theme_emoji": "single emoji that best captures today's top story theme (e.g. ⚔️ 🚢 🕊️ 💥 🛢️ 📉 ☢️ 🤝 🚀 💣)",
  "market_strip": [
    {{"label": "S&P 500",  "value": "5,842", "change": "+0.43%", "dir": "up"}},
    {{"label": "Nasdaq",   "value": "18,921","change": "+0.67%", "dir": "up"}},
    {{"label": "Brent",    "value": "$101",  "change": "+2.1%",  "dir": "up"}},
    {{"label": "Gold",     "value": "$3,240","change": "+1.2%",  "dir": "up"}},
    {{"label": "Nat. Gas", "value": "$6.14", "change": "+3.4%",  "dir": "up"}},
    {{"label": "VIX",      "value": "21.3",  "change": "-1.4",   "dir": "down"}}
  ],
  "war_stories": [
    {{
      "source": "CNN", "source_class": "src-cnn", "time": "Today, 05:32 EDT",
      "headline": "...", "body": "...",
      "tags": ["Breaking", "Hormuz"],
      "featured": true
    }}
  ],
  "biz_stats": [
    {{"val": "$101", "label": "Brent Crude / Barrel", "sub": "↑ 30% since Feb 28", "color": "red"}}
  ],
  "biz_stories": [
    {{
      "source": "CNBC", "source_class": "src-cnbc", "time": "Today",
      "headline": "...", "body": "...", "tags": ["Macro", "Oil"]
    }}
  ],
  "mkt_stats": [
    {{"val": "+4%", "label": "S&P Since War Began", "sub": "Feb 28 → Today", "color": "green"}}
  ],
  "mkt_stories": [
    {{
      "source": "CNBC", "source_class": "src-cnbc", "time": "Today",
      "headline": "...", "body": "...", "tags": ["Records"]
    }}
  ],
  "stocks": [
    {{
      "ticker": "LMT", "company": "Lockheed Martin",
      "sector": "Defense", "sector_class": "sect-defense",
      "action": "BUY", "action_class": "action-buy", "action_arrow": "▲",
      "price_target": "$521", "upside": "+11.2%", "upside_positive": true,
      "evidence": [
        {{"text": "Trump proposes $1.5T Pentagon budget for FY2027", "source": "Motley Fool"}}
      ],
      "risk": "LOW", "risk_class": "risk-low"
    }}
  ]
}}

Source class mapping (use exact string):
CNN→src-cnn, Al Jazeera→src-alj, CNBC→src-cnbc, Bloomberg→src-bloomberg,
Reuters→src-reuters, Washington Post→src-wapo, NBC News→src-nbcnews,
CBS News→src-cbsnews, Morgan Stanley→src-ms, Motley Fool→src-fool,
WSJ→src-wsj, FT→src-ft, NYT→src-nyt, default→src-cnbc

Action class: BUY→action-buy, SELL→action-sell, HOLD→action-hold
Sector class: Defense→sect-defense, Energy→sect-energy, Gold→sect-metals,
              Airlines→sect-airline, Consumer→sect-consumer
Risk class: LOW→risk-low, MEDIUM→risk-med, HIGH→risk-high

Include at least: 5 war stories (1 featured), 4 biz stats, 4 biz stories,
4 mkt stats, 4 mkt stories, 8 stocks (mix of buy/sell/hold).
Keep body text under 60 words per story. Return ONLY the raw JSON object.

--- WAR DATA ---
{raw['war'][:2500]}

--- BUSINESS DATA ---
{raw['biz'][:2000]}

--- MARKET DATA ---
{raw['mkt'][:2000]}

--- STOCK DATA ---
{raw['stk'][:2500]}
"""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    # Attempt to repair truncated JSON by closing open structures
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Close any unclosed arrays/objects and retry once
        for closing in [']}', ']}]}', '"]}]}', '"]}]}]}']:
            try:
                return json.loads(text + closing)
            except json.JSONDecodeError:
                continue
        raise


# ── HTML rendering ─────────────────────────────────────────────────────────
def source_badge(source: str, cls: str) -> str:
    url = SOURCE_URLS.get(cls, "")
    if url:
        onclick = f"window.open('{url}','newsoutlet','width=1200,height=800,scrollbars=yes,resizable=yes'); return false;"
        return f'<a href="{url}" class="source-badge {cls}" onclick="{onclick}" title="Open {source}">{source}</a>'
    return f'<span class="source-badge {cls}">{source}</span>'

def render_tags(tags: list) -> str:
    if not tags:
        return ""
    parts = []
    for t in tags:
        cls = "tag tag-hot" if t.lower() in ("breaking","escalation","hot") else "tag"
        if t.lower() in ("new","latest"):
            cls = "tag tag-new"
        parts.append(f'<span class="{cls}">{t}</span>')
    return f'<div class="card-tags">{"".join(parts)}</div>'

def render_news_card(story: dict, accent: str, featured: bool = False) -> str:
    featured_cls = " featured" if featured else ""
    breaking = '<div class="breaking-label">⚡ Breaking Now</div>' if featured else ""
    return f"""
    <div class="news-card card-{accent}{featured_cls}">
      {breaking}
      <div class="card-source-row">
        {source_badge(story['source'], story.get('source_class','src-cnbc'))}
        <span class="card-time">{story.get('time','Today')}</span>
      </div>
      <div class="card-headline">{story['headline']}</div>
      <div class="card-body">{story['body']}</div>
      {render_tags(story.get('tags', []))}
    </div>"""

def render_stat_card(stat: dict) -> str:
    color_map = {"red": "var(--accent-red)", "green": "var(--accent-green)",
                 "amber": "var(--accent-amber)", "blue": "var(--accent-blue)",
                 "gold": "var(--accent-gold)"}
    color = color_map.get(stat.get("color","amber"), "var(--accent-amber)")
    return f"""
    <div class="stat-card">
      <div class="stat-val" style="color:{color}">{stat['val']}</div>
      <div class="stat-label">{stat['label']}</div>
      <div class="stat-sub" style="color:{'var(--accent-red)' if stat.get('color')=='red' else 'var(--text-muted)'}">{stat.get('sub','')}</div>
    </div>"""

def render_mkt_strip(items: list) -> str:
    parts = []
    for i, item in enumerate(items):
        dir_cls = item.get("dir", "up")
        arrow = "▲" if dir_cls == "up" else "▼"
        label = item['label']
        url = MARKET_URLS.get(label, "")
        onclick = f"window.open('{url}','market','width=1200,height=800,scrollbars=yes,resizable=yes'); return false;" if url else ""
        tag_open  = f'<a href="{url}" class="mkt-item mkt-link" onclick="{onclick}" title="Research {label} on Yahoo Finance">' if url else '<div class="mkt-item">'
        tag_close = "</a>" if url else "</div>"
        parts.append(f"""
      {tag_open}
        <div class="mkt-label">{label}</div>
        <div class="mkt-val {dir_cls}">{item['value']}</div>
        <div class="mkt-chg {dir_cls}">{arrow} {item['change']}</div>
      {tag_close}""")
        if i < len(items) - 1:
            parts.append('<div class="mkt-divider"></div>')
    return "".join(parts)

def render_stock_row(s: dict) -> str:
    evidence_html = "".join(
        f'<li>{e["text"]} — <span class="evidence-source">{e["source"]}</span></li>'
        for e in s.get("evidence", [])
    )
    upside_cls = "upside-pos" if s.get("upside_positive", True) else "upside-neg"
    risk_html = f"""
      <div class="risk-bar-wrap {s.get('risk_class','risk-med')}">
        <div class="risk-bar"><div class="risk-fill"></div></div>
        <span class="risk-label">{s.get('risk','MED')}</span>
      </div>"""
    ticker = s['ticker']
    yf_url = f"https://finance.yahoo.com/quote/{ticker.replace('/', '%2F')}"
    onclick_t = f"window.open('{yf_url}','stock','width=1200,height=800,scrollbars=yes,resizable=yes'); return false;"
    return f"""
        <tr>
          <td>
            <a href="{yf_url}" class="ticker-link" onclick="{onclick_t}" title="Research {ticker} on Yahoo Finance">
              <div class="ticker-cell">{ticker}</div>
              <div class="company-name">{s['company']} ↗</div>
            </a>
          </td>
          <td><span class="sector-pill {s.get('sector_class','sect-energy')}">{s['sector']}</span></td>
          <td><span class="action-badge {s.get('action_class','action-hold')}">{s.get('action_arrow','◆')} {s['action']}</span></td>
          <td>
            <div class="price-target">{s.get('price_target','—')}</div>
            <div class="price-upside {upside_cls}">{s.get('upside','')}</div>
          </td>
          <td><ul class="evidence-list">{evidence_html}</ul></td>
          <td>{risk_html}</td>
        </tr>"""

def render_daily_html(data: dict) -> str:
    war_cards = "\n".join(
        render_news_card(s, "war", featured=s.get("featured", False))
        for s in data.get("war_stories", [])
    )
    biz_stats  = "\n".join(render_stat_card(s) for s in data.get("biz_stats", []))
    biz_cards  = "\n".join(render_news_card(s, "biz") for s in data.get("biz_stories", []))
    mkt_stats  = "\n".join(render_stat_card(s) for s in data.get("mkt_stats", []))
    mkt_cards  = "\n".join(render_news_card(s, "market") for s in data.get("mkt_stories", []))
    stk_rows   = "\n".join(render_stock_row(s) for s in data.get("stocks", []))
    mkt_strip  = render_mkt_strip(data.get("market_strip", []))

    formatted_date = datetime.strptime(TODAY, "%Y-%m-%d").strftime("%A, %B %d, %Y")

    # Ticker items from war headlines
    ticker_items = " ".join(
        f'<span>{s["headline"]}</span>'
        for s in data.get("war_stories", [])[:6]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>War Room — {formatted_date}</title>
<style>
  :root {{
    --bg:#090c14;--surface:#0f1520;--surface2:#141c2e;--border:#1e2d47;
    --accent-red:#e63946;--accent-amber:#f4a261;--accent-gold:#ffd166;
    --accent-green:#06d6a0;--accent-blue:#4cc9f0;
    --text:#e2e8f0;--text-muted:#64748b;--text-dim:#94a3b8;
    --buy:#06d6a0;--sell:#e63946;--hold:#f4a261;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}}
  /* TICKER */
  .ticker-wrap{{background:var(--accent-red);padding:8px 0;overflow:hidden;white-space:nowrap;position:sticky;top:0;z-index:100;border-bottom:2px solid #c1121f}}
  .ticker-label{{display:inline-block;background:#900;color:#fff;font-weight:900;font-size:11px;letter-spacing:2px;padding:2px 14px;margin-right:16px;vertical-align:middle}}
  .ticker-inner{{display:inline-block;animation:ticker 60s linear infinite}}
  .ticker-inner span{{font-size:12px;font-weight:600;margin-right:60px;color:#fff}}
  .ticker-inner span::before{{content:"▸ ";opacity:.7}}
  @keyframes ticker{{from{{transform:translateX(100vw)}}to{{transform:translateX(-100%)}}}}
  /* BACK LINK */
  .back-bar{{background:var(--surface2);border-bottom:1px solid var(--border);padding:10px 40px;display:flex;align-items:center;gap:12px}}
  .back-bar a{{color:var(--accent-blue);font-size:13px;font-weight:600;text-decoration:none;display:flex;align-items:center;gap:6px}}
  .back-bar a:hover{{color:#fff}}
  .back-bar .date-pill{{background:rgba(230,57,70,.12);border:1px solid rgba(230,57,70,.3);border-radius:20px;padding:3px 14px;font-size:11px;color:var(--accent-red);font-weight:700;letter-spacing:1px}}
  /* HEADER */
  header{{background:linear-gradient(135deg,#060a14 0%,#0d1b2a 50%,#060a14 100%);border-bottom:1px solid var(--border);padding:28px 40px 24px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}}
  .logo-area h1{{font-size:32px;font-weight:900;letter-spacing:-1px;background:linear-gradient(90deg,#e63946,#f4a261,#ffd166);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;text-transform:uppercase;line-height:1}}
  .logo-area .sub{{font-size:11px;letter-spacing:4px;color:var(--text-muted);text-transform:uppercase;margin-top:6px}}
  .live-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(230,57,70,.15);border:1px solid var(--accent-red);border-radius:20px;padding:5px 14px;font-size:11px;font-weight:700;letter-spacing:2px;color:var(--accent-red);text-transform:uppercase;margin-bottom:8px}}
  .live-dot{{width:7px;height:7px;border-radius:50%;background:var(--accent-red);animation:pulse 1.2s ease-in-out infinite}}
  @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.4;transform:scale(.7)}}}}
  .timestamp{{font-size:12px;color:var(--text-muted)}}.war-day{{font-size:13px;color:var(--accent-amber);font-weight:700;letter-spacing:1px;margin-top:4px}}
  /* MARKET STRIP */
  .market-strip{{background:var(--surface);border-bottom:1px solid var(--border);padding:10px 40px;display:flex;gap:32px;overflow-x:auto;scrollbar-width:none;flex-wrap:wrap}}
  .mkt-item{{display:flex;flex-direction:column;align-items:center;min-width:90px}}
  .mkt-label{{font-size:10px;letter-spacing:1.5px;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px}}
  .mkt-val{{font-size:15px;font-weight:700}}.mkt-chg{{font-size:11px;font-weight:600;margin-top:2px}}
  .up{{color:var(--accent-green)}}.down{{color:var(--accent-red)}}
  .mkt-divider{{width:1px;background:var(--border);align-self:stretch}}
  /* MAIN */
  main{{max-width:1400px;margin:0 auto;padding:36px 28px 60px}}
  /* SECTION */
  .section-header{{display:flex;align-items:center;gap:14px;margin-bottom:24px;margin-top:48px}}
  .section-header:first-child{{margin-top:0}}
  .section-icon{{width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}}
  .icon-war{{background:rgba(230,57,70,.15);border:1px solid rgba(230,57,70,.4)}}
  .icon-biz{{background:rgba(244,162,97,.15);border:1px solid rgba(244,162,97,.4)}}
  .icon-market{{background:rgba(76,201,240,.15);border:1px solid rgba(76,201,240,.4)}}
  .icon-stocks{{background:rgba(6,214,160,.15);border:1px solid rgba(6,214,160,.4)}}
  .section-title h2{{font-size:22px;font-weight:800;letter-spacing:-.5px}}
  .section-title p{{font-size:12px;color:var(--text-muted);margin-top:2px;letter-spacing:.5px}}
  .war-title{{color:var(--accent-red)}}.biz-title{{color:var(--accent-amber)}}
  .mkt-title{{color:var(--accent-blue)}}.stk-title{{color:var(--accent-green)}}
  .section-count{{background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:4px 14px;font-size:11px;color:var(--text-dim);font-weight:600;letter-spacing:1px}}
  .divider{{height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent);margin:4px 0 28px}}
  /* CARDS */
  .card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:18px}}
  .card-grid.two-col{{grid-template-columns:repeat(auto-fill,minmax(420px,1fr))}}
  .news-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;transition:transform .2s,border-color .2s,box-shadow .2s;position:relative;overflow:hidden}}
  .news-card::before{{content:'';position:absolute;top:0;left:0;width:3px;height:100%;border-radius:3px 0 0 3px}}
  .card-war::before{{background:linear-gradient(180deg,#e63946,#9d0208)}}
  .card-biz::before{{background:linear-gradient(180deg,#f4a261,#e76f51)}}
  .card-market::before{{background:linear-gradient(180deg,#4cc9f0,#4361ee)}}
  .card-stocks::before{{background:linear-gradient(180deg,#06d6a0,#118ab2)}}
  .news-card:hover{{transform:translateY(-3px);border-color:#2a3a54;box-shadow:0 12px 40px rgba(0,0,0,.4)}}
  .card-source-row{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}}
  .source-badge{{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:3px 10px;border-radius:4px}}
  .src-cnn{{background:rgba(204,0,0,.2);color:#ff6b6b;border:1px solid rgba(204,0,0,.4)}}
  .src-alj{{background:rgba(230,126,34,.2);color:#f4a261;border:1px solid rgba(230,126,34,.4)}}
  .src-cnbc{{background:rgba(76,201,240,.15);color:#4cc9f0;border:1px solid rgba(76,201,240,.3)}}
  .src-bloomberg{{background:rgba(102,178,255,.15);color:#90e0ef;border:1px solid rgba(102,178,255,.3)}}
  .src-reuters{{background:rgba(255,140,0,.15);color:#fca311;border:1px solid rgba(255,140,0,.3)}}
  .src-wapo{{background:rgba(150,120,255,.15);color:#c8b6ff;border:1px solid rgba(150,120,255,.3)}}
  .src-wsj{{background:rgba(100,200,150,.15);color:#80ffb0;border:1px solid rgba(100,200,150,.3)}}
  .src-ft{{background:rgba(255,200,50,.15);color:#ffd166;border:1px solid rgba(255,200,50,.3)}}
  .src-nyt{{background:rgba(200,200,200,.1);color:#cbd5e1;border:1px solid rgba(200,200,200,.2)}}
  .src-ms{{background:rgba(0,150,136,.2);color:#4db6ac;border:1px solid rgba(0,150,136,.4)}}
  .src-fool{{background:rgba(100,200,100,.15);color:#a8e6a3;border:1px solid rgba(100,200,100,.3)}}
  .src-nbcnews{{background:rgba(100,130,255,.15);color:#b0c4ff;border:1px solid rgba(100,130,255,.3)}}
  .src-cbsnews{{background:rgba(50,150,255,.15);color:#90c8ff;border:1px solid rgba(50,150,255,.3)}}
  .card-time{{font-size:11px;color:var(--text-muted)}}
  .card-headline{{font-size:15px;font-weight:700;line-height:1.45;color:var(--text);margin-bottom:10px;letter-spacing:-.2px}}
  .card-body{{font-size:13px;color:var(--text-dim);line-height:1.65}}
  .card-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px}}
  .tag{{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;padding:3px 8px;border-radius:3px;background:var(--surface2);border:1px solid var(--border);color:var(--text-muted)}}
  .tag-hot{{background:rgba(230,57,70,.1);color:var(--accent-red);border-color:rgba(230,57,70,.3)}}
  .tag-new{{background:rgba(6,214,160,.1);color:var(--accent-green);border-color:rgba(6,214,160,.3)}}
  .news-card.featured{{grid-column:1/-1;background:linear-gradient(135deg,#0f1520 0%,#141c2e 100%);border-color:rgba(230,57,70,.3)}}
  .news-card.featured .card-headline{{font-size:20px;line-height:1.35}}
  .news-card.featured .card-body{{font-size:14px;max-width:900px}}
  .breaking-label{{display:inline-flex;align-items:center;gap:6px;background:var(--accent-red);color:#fff;font-size:10px;font-weight:900;letter-spacing:2.5px;text-transform:uppercase;padding:3px 12px;border-radius:4px;margin-bottom:12px}}
  /* STATS */
  .stats-row{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:30px}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 20px;text-align:center}}
  .stat-val{{font-size:28px;font-weight:900;letter-spacing:-1px;line-height:1;margin-bottom:6px}}
  .stat-label{{font-size:11px;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase}}
  .stat-sub{{font-size:11px;margin-top:4px;font-weight:600;color:var(--text-muted)}}
  /* TABLE */
  .stock-table-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-top:8px}}
  .table-header-bar{{background:var(--surface2);padding:16px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:12px}}
  .table-header-bar h3{{font-size:15px;font-weight:800;color:var(--text)}}
  .table-legend{{display:flex;gap:16px}}
  .legend-item{{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-muted);font-weight:600;letter-spacing:.5px}}
  .legend-dot{{width:8px;height:8px;border-radius:50%}}
  .dot-buy{{background:var(--buy)}}.dot-sell{{background:var(--sell)}}.dot-hold{{background:var(--hold)}}
  table{{width:100%;border-collapse:collapse}}
  thead th{{background:var(--surface2);padding:12px 16px;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted);text-align:left;border-bottom:1px solid var(--border)}}
  thead th:first-child{{padding-left:24px}}thead th:last-child{{padding-right:24px}}
  tbody tr{{border-bottom:1px solid rgba(30,45,71,.6);transition:background .15s}}
  tbody tr:last-child{{border-bottom:none}}
  tbody tr:hover{{background:rgba(255,255,255,.02)}}
  tbody td{{padding:14px 16px;font-size:13px;vertical-align:top}}
  tbody td:first-child{{padding-left:24px}}tbody td:last-child{{padding-right:24px}}
  .ticker-cell{{font-size:15px;font-weight:900;letter-spacing:.5px}}
  .company-name{{font-size:11px;color:var(--text-muted);margin-top:2px}}
  .sector-pill{{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;padding:3px 9px;border-radius:4px}}
  .sect-energy{{background:rgba(244,162,97,.15);color:var(--accent-amber);border:1px solid rgba(244,162,97,.3)}}
  .sect-defense{{background:rgba(76,201,240,.15);color:var(--accent-blue);border:1px solid rgba(76,201,240,.3)}}
  .sect-metals{{background:rgba(255,209,102,.15);color:var(--accent-gold);border:1px solid rgba(255,209,102,.3)}}
  .sect-airline{{background:rgba(230,57,70,.12);color:var(--accent-red);border:1px solid rgba(230,57,70,.25)}}
  .sect-consumer{{background:rgba(148,163,184,.12);color:var(--text-dim);border:1px solid rgba(148,163,184,.2)}}
  .action-badge{{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;padding:5px 14px;border-radius:6px}}
  .action-buy{{background:rgba(6,214,160,.15);color:var(--buy);border:1px solid rgba(6,214,160,.4)}}
  .action-sell{{background:rgba(230,57,70,.15);color:var(--sell);border:1px solid rgba(230,57,70,.4)}}
  .action-hold{{background:rgba(244,162,97,.15);color:var(--hold);border:1px solid rgba(244,162,97,.4)}}
  .evidence-list{{list-style:none;display:flex;flex-direction:column;gap:5px}}
  .evidence-list li{{font-size:12px;color:var(--text-dim);line-height:1.5;padding-left:14px;position:relative}}
  .evidence-list li::before{{content:'›';position:absolute;left:0;color:var(--text-muted);font-weight:700}}
  .evidence-source{{font-size:10px;font-weight:700;letter-spacing:.8px;color:var(--accent-blue);text-transform:uppercase;opacity:.8}}
  .price-target{{font-size:13px;font-weight:700}}
  .price-upside{{font-size:11px;font-weight:600;margin-top:3px}}
  .upside-pos{{color:var(--accent-green)}}.upside-neg{{color:var(--accent-red)}}
  .risk-bar-wrap{{display:flex;align-items:center;gap:8px;margin-top:4px}}
  .risk-bar{{flex:1;height:4px;background:var(--surface2);border-radius:2px;overflow:hidden}}
  .risk-fill{{height:100%;border-radius:2px}}
  .risk-low .risk-fill{{background:var(--accent-green);width:30%}}
  .risk-med .risk-fill{{background:var(--accent-amber);width:55%}}
  .risk-high .risk-fill{{background:var(--accent-red);width:85%}}
  .risk-label{{font-size:10px;color:var(--text-muted);font-weight:600;letter-spacing:.5px;white-space:nowrap}}
  .disclaimer{{margin-top:48px;background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent-amber);border-radius:8px;padding:16px 20px;font-size:12px;color:var(--text-muted);line-height:1.7}}
  .disclaimer strong{{color:var(--accent-amber)}}
  /* SOURCE BADGE LINKS */
  a.source-badge{{text-decoration:none;cursor:pointer;transition:opacity .15s,transform .15s}}
  a.source-badge:hover{{opacity:.75;transform:scale(1.05)}}
  /* MARKET STRIP LINKS */
  a.mkt-link{{text-decoration:none;border-radius:8px;padding:4px 6px;margin:-4px -6px;transition:background .15s,transform .15s}}
  a.mkt-link:hover{{background:rgba(76,201,240,.08);transform:translateY(-2px)}}
  /* TICKER LINKS */
  a.ticker-link{{text-decoration:none;display:block;border-radius:6px;padding:4px 6px;margin:-4px -6px;transition:background .15s}}
  a.ticker-link:hover{{background:rgba(76,201,240,.08)}}
  a.ticker-link:hover .ticker-cell{{color:var(--accent-blue)}}
  a.ticker-link .company-name{{color:var(--text-muted)}}
  /* COMMENTS */
  .comments-section{{max-width:1400px;margin:0 auto;padding:0 28px 60px}}
  .comments-header{{display:flex;align-items:center;gap:14px;margin-bottom:24px;padding-top:48px}}
  .comments-header .section-icon{{width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;background:rgba(114,9,183,.15);border:1px solid rgba(114,9,183,.4);flex-shrink:0}}
  .comments-header h2{{font-size:22px;font-weight:800;color:#c77dff;letter-spacing:-.5px}}
  .comments-header p{{font-size:12px;color:var(--text-muted);margin-top:2px}}
  .comments-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:32px;min-height:200px}}
  #disqus_thread a{{color:var(--accent-blue)}}
  footer{{background:var(--surface);border-top:1px solid var(--border);padding:20px 40px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-top:60px}}
  footer p{{font-size:12px;color:var(--text-muted)}}
  /* ── TABLET ── */
  @media(max-width:1024px){{
    .card-grid.two-col{{grid-template-columns:1fr}}
    .stats-row{{grid-template-columns:repeat(3,1fr)}}
  }}
  /* ── MOBILE ── */
  @media(max-width:768px){{
    /* Header */
    header{{flex-direction:column;align-items:flex-start;padding:16px;gap:12px}}
    .header-meta{{text-align:left!important;width:100%;display:flex;align-items:center;justify-content:space-between}}
    .logo-area>div>span{{font-size:36px!important}}
    .logo-area h1{{font-size:22px}}
    .logo-area .sub{{font-size:9px;letter-spacing:2px}}
    /* Back bar */
    .back-bar{{padding:8px 12px;flex-wrap:wrap}}
    .back-bar span:last-child{{display:none}}
    /* Market strip — horizontal scroll, no wrap */
    .market-strip{{flex-wrap:nowrap;padding:8px 12px;gap:0;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}}
    .mkt-item,a.mkt-link{{min-width:68px;flex-shrink:0;padding:4px 6px}}
    .mkt-label{{font-size:9px;letter-spacing:1px}}
    .mkt-val{{font-size:13px}}
    .mkt-chg{{font-size:10px}}
    .mkt-divider{{width:1px;flex-shrink:0}}
    /* Main & sections */
    main{{padding:20px 12px 40px}}
    .comments-section{{padding:0 12px 40px}}
    .section-header{{gap:10px;margin-top:32px}}
    .section-title h2{{font-size:17px}}
    .section-count{{display:none}}
    /* Cards */
    .card-grid,.card-grid.two-col{{grid-template-columns:1fr}}
    .news-card.featured .card-headline{{font-size:16px}}
    .news-card.featured .card-body{{font-size:13px}}
    /* Stats */
    .stats-row{{grid-template-columns:repeat(2,1fr);gap:10px}}
    .stat-val{{font-size:22px}}
    /* Stock table — horizontal scroll with fade hint */
    .stock-table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch;position:relative}}
    .stock-table-wrap::after{{content:'';position:absolute;top:0;right:0;width:36px;height:100%;background:linear-gradient(90deg,transparent,rgba(9,12,20,.85));pointer-events:none;border-radius:0 14px 14px 0}}
    table{{min-width:660px}}
    .table-header-bar{{flex-direction:column;align-items:flex-start;gap:8px}}
    /* Comments */
    .comments-wrap{{padding:16px}}
    .comments-header h2{{font-size:18px}}
    /* Footer */
    footer{{padding:14px 16px;flex-direction:column;gap:6px;text-align:center}}
    /* Ticker */
    .ticker-label{{font-size:10px;padding:2px 10px}}
    .ticker-inner span{{font-size:11px}}
  }}
  /* ── SMALL MOBILE ── */
  @media(max-width:400px){{
    .logo-area h1{{font-size:18px}}
    .section-title h2{{font-size:15px}}
    .stats-row{{grid-template-columns:1fr 1fr}}
    .stat-val{{font-size:20px}}
    .card-headline{{font-size:14px}}
    .mkt-item,a.mkt-link{{min-width:58px}}
  }}
</style>
</head>
<body>

<div class="ticker-wrap">
  <span class="ticker-label">BREAKING</span>
  <div class="ticker-inner">{ticker_items}</div>
</div>

<div class="back-bar">
  <a href="../index.html">← Calendar</a>
  <span class="date-pill">{formatted_date}</span>
  <span style="font-size:11px;color:var(--text-muted);margin-left:auto">Generated {RUN_TS}</span>
</div>

<header>
  <div class="logo-area">
    <div style="display:flex;align-items:center;gap:16px">
      <span style="font-size:52px;line-height:1;filter:drop-shadow(0 0 12px rgba(230,57,70,.5))">{data.get('theme_emoji','⚔️')}</span>
      <div>
        <h1>War Room</h1>
        <div class="sub">US–Iran Crisis Intelligence Dashboard</div>
      </div>
    </div>
  </div>
  <div class="header-meta" style="text-align:right">
    <div class="live-badge"><span class="live-dot"></span>Daily Intelligence</div>
    <div class="timestamp">{formatted_date}</div>
    <div class="war-day">Generated {NOW}</div>
  </div>
</header>

<div class="market-strip">{mkt_strip}</div>

<main>

  <div class="section-header">
    <div class="section-icon icon-war">⚔️</div>
    <div class="section-title">
      <h2 class="war-title">1 — War: Military &amp; Geopolitical Updates</h2>
      <p>Live conflict coverage aggregated from major news outlets</p>
    </div>
    <div class="section-count">{len(data.get('war_stories',[]))} STORIES</div>
  </div>
  <div class="divider"></div>
  <div class="card-grid">{war_cards}</div>

  <div class="section-header">
    <div class="section-icon icon-biz">🏭</div>
    <div class="section-title">
      <h2 class="biz-title">2 — Business Impact: Economy &amp; Industry</h2>
      <p>Energy markets, supply chains, corporate earnings, consumer impact</p>
    </div>
    <div class="section-count">{len(data.get('biz_stories',[]))} STORIES</div>
  </div>
  <div class="divider"></div>
  <div class="stats-row">{biz_stats}</div>
  <div class="card-grid two-col">{biz_cards}</div>

  <div class="section-header">
    <div class="section-icon icon-market">📈</div>
    <div class="section-title">
      <h2 class="mkt-title">3 — Stock Market: Wall Street Response</h2>
      <p>Index performance, sector rotation, analyst sentiment</p>
    </div>
    <div class="section-count">{len(data.get('mkt_stories',[]))} STORIES</div>
  </div>
  <div class="divider"></div>
  <div class="stats-row">{mkt_stats}</div>
  <div class="card-grid two-col">{mkt_cards}</div>

  <div class="section-header">
    <div class="section-icon icon-stocks">📊</div>
    <div class="section-title">
      <h2 class="stk-title">4 — Buy / Sell / Hold Intelligence Table</h2>
      <p>Analyst consensus with evidence — updated {RUN_TS}</p>
    </div>
    <div class="section-count">{len(data.get('stocks',[]))} EQUITIES</div>
  </div>
  <div class="divider"></div>

  <div class="stock-table-wrap">
    <div class="table-header-bar">
      <h3>War-Environment Stock Intelligence — {formatted_date}</h3>
      <div class="table-legend">
        <div class="legend-item"><div class="legend-dot dot-buy"></div>BUY</div>
        <div class="legend-item"><div class="legend-dot dot-hold"></div>HOLD</div>
        <div class="legend-item"><div class="legend-dot dot-sell"></div>SELL</div>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Ticker / Company</th><th>Sector</th><th>Action</th>
          <th>Price Target</th><th>News &amp; Evidence</th><th>Risk</th>
        </tr>
      </thead>
      <tbody>{stk_rows}</tbody>
    </table>
  </div>

  <div class="disclaimer">
    <strong>Investment Disclaimer:</strong> This dashboard aggregates publicly available
    news and analyst opinions for informational purposes only. It does not constitute
    financial advice. All investment decisions carry risk. Always consult a qualified
    financial advisor before making investment decisions.
  </div>

</main>

<!-- ── COMMENTS ── -->
<div class="comments-section">
  <div class="comments-header">
    <div class="section-icon">💬</div>
    <div class="section-title">
      <h2>Comments &amp; Discussion</h2>
      <p>Share your analysis, questions, or perspective on today's intelligence report</p>
    </div>
  </div>
  <div style="height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent);margin-bottom:28px"></div>
  <div class="comments-wrap">
    <div id="disqus_thread"></div>
  </div>
</div>

<footer>
  <p>War Room · {formatted_date} · Auto-generated by War Room Intelligence System</p>
</footer>

<script>
  var disqus_config = function () {{
    this.page.url = 'https://www.newsofpast.com/news/{TODAY}.html';
    this.page.identifier = 'warroom-{TODAY}';
    this.page.title = '{formatted_date} — War Room Intelligence Report';
  }};
  (function() {{
    var d = document, s = d.createElement('script');
    s.src = 'https://news-of-past.disqus.com/embed.js';
    s.setAttribute('data-timestamp', +new Date());
    (d.head || d.body).appendChild(s);
  }})();
</script>

</body>
</html>"""


# ── Calendar index ─────────────────────────────────────────────────────────
def load_reports() -> list:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []

def save_reports(reports: list):
    DATA_FILE.write_text(json.dumps(reports, indent=2))

def upsert_report(reports: list, headline: str) -> list:
    entry = {"date": TODAY, "headline": headline, "path": f"news/{TODAY}.html"}
    existing = [r for r in reports if r["date"] != TODAY]
    return sorted(existing + [entry], key=lambda r: r["date"], reverse=True)

def build_calendar_cells(reports: list, year: int, month: int) -> str:
    import calendar as cal_mod
    report_map = {r["date"]: r for r in reports}
    cal = cal_mod.monthcalendar(year, month)
    today_str = date.today().isoformat()
    html = ""
    for week in cal:
        for day in week:
            if day == 0:
                html += '<div class="cal-cell empty"></div>'
            else:
                d = date(year, month, day).isoformat()
                if d in report_map:
                    cls = "cal-cell has-report"
                    if d == today_str:
                        cls += " today"
                    html += f'<a class="{cls}" href="{report_map[d]["path"]}" title="{report_map[d]["headline"]}">{day}<span class="dot"></span></a>'
                elif d == today_str:
                    html += f'<div class="cal-cell today">{day}</div>'
                else:
                    html += f'<div class="cal-cell">{day}</div>'
    return html

def build_recent_list(reports: list) -> str:
    items = ""
    for r in reports[:30]:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        label = d.strftime("%b %d, %Y")
        items += f"""
      <a class="recent-item" href="{r['path']}">
        <span class="recent-date">{label}</span>
        <span class="recent-headline">{r['headline']}</span>
        <span class="recent-arrow">→</span>
      </a>"""
    return items

def render_index(reports: list):
    today = date.today()
    yr, mo = today.year, today.month
    import calendar as cal_mod
    month_name = cal_mod.month_name[mo]
    day_headers = "".join(f'<div class="cal-header">{d}</div>' for d in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"])
    cells = build_calendar_cells(reports, yr, mo)
    recent = build_recent_list(reports)
    total = len(reports)
    latest = reports[0] if reports else None
    latest_html = ""
    if latest:
        ld = datetime.strptime(latest["date"], "%Y-%m-%d").strftime("%B %d, %Y")
        latest_html = f"""
      <a class="latest-card" href="{latest['path']}">
        <div class="latest-label">Latest Report</div>
        <div class="latest-date">{ld}</div>
        <div class="latest-headline">{latest['headline']}</div>
        <div class="latest-cta">Open Report →</div>
      </a>"""

    INDEX_FILE.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>War Room — Intelligence Archive</title>
<style>
  :root{{--bg:#090c14;--surface:#0f1520;--surface2:#141c2e;--border:#1e2d47;
    --accent-red:#e63946;--accent-amber:#f4a261;--accent-gold:#ffd166;
    --accent-green:#06d6a0;--accent-blue:#4cc9f0;
    --text:#e2e8f0;--text-muted:#64748b;--text-dim:#94a3b8}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
  /* HEADER */
  header{{background:linear-gradient(135deg,#060a14,#0d1b2a,#060a14);border-bottom:1px solid var(--border);padding:32px 48px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}}
  .logo h1{{font-size:36px;font-weight:900;letter-spacing:-1px;background:linear-gradient(90deg,#e63946,#f4a261,#ffd166);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;text-transform:uppercase}}
  .logo p{{font-size:11px;letter-spacing:4px;color:var(--text-muted);text-transform:uppercase;margin-top:6px}}
  .header-stats{{display:flex;gap:24px}}
  .hstat{{text-align:center}}
  .hstat-val{{font-size:28px;font-weight:900;color:var(--accent-amber)}}
  .hstat-label{{font-size:11px;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase}}
  /* LAYOUT */
  .layout{{max-width:1300px;margin:0 auto;padding:40px 28px 80px;display:grid;grid-template-columns:1fr 360px;gap:32px}}
  /* ── TABLET ── */
  @media(max-width:900px){{
    .layout{{grid-template-columns:1fr;padding:24px 16px 60px}}
    header{{padding:20px;flex-wrap:wrap;gap:12px}}
    .logo h1{{font-size:28px}}
  }}
  /* ── MOBILE ── */
  @media(max-width:600px){{
    header{{padding:16px;flex-direction:column;align-items:flex-start}}
    .logo h1{{font-size:22px}}
    .logo p{{font-size:9px;letter-spacing:2px}}
    .header-stats{{gap:16px}}
    .hstat-val{{font-size:22px}}
    .layout{{padding:16px 12px 40px;gap:20px}}
    .cal-nav{{padding:12px 16px;flex-direction:column;align-items:flex-start;gap:8px}}
    .cal-nav h2{{font-size:17px}}
    .cal-legend{{font-size:10px;gap:10px}}
    .cal-grid{{padding:10px;gap:2px}}
    .cal-header{{font-size:9px;padding:4px 0}}
    .cal-cell{{font-size:12px;border-radius:6px}}
    .recent-item{{flex-direction:column;gap:3px;padding:12px 16px}}
    .recent-date{{min-width:auto}}
    .latest-card{{padding:16px}}
    .latest-headline{{font-size:14px}}
  }}
  /* CALENDAR */
  .cal-section{{background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden}}
  .cal-nav{{background:var(--surface2);padding:18px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}}
  .cal-nav h2{{font-size:20px;font-weight:800;color:var(--text)}}
  .cal-nav .year{{font-size:14px;color:var(--accent-amber);font-weight:700;margin-left:10px}}
  .cal-legend{{display:flex;gap:16px;font-size:11px;color:var(--text-muted)}}
  .cal-legend span{{display:flex;align-items:center;gap:6px}}
  .cal-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;padding:20px}}
  .cal-header{{text-align:center;font-size:11px;font-weight:700;letter-spacing:1px;color:var(--text-muted);text-transform:uppercase;padding:6px 0;margin-bottom:4px}}
  .cal-cell{{aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:8px;font-size:14px;font-weight:600;color:var(--text-dim);position:relative;transition:background .15s}}
  .cal-cell.empty{{opacity:0}}
  .cal-cell.today{{background:rgba(230,57,70,.12);border:1px solid rgba(230,57,70,.3);color:var(--accent-red);font-weight:800}}
  a.cal-cell{{text-decoration:none;cursor:pointer;color:var(--text);background:var(--surface2);border:1px solid var(--border)}}
  a.cal-cell:hover{{background:rgba(76,201,240,.12);border-color:rgba(76,201,240,.4);color:var(--accent-blue);transform:scale(1.05)}}
  a.cal-cell.today{{background:rgba(230,57,70,.15);border-color:rgba(230,57,70,.5);color:#fff}}
  .dot{{position:absolute;bottom:5px;left:50%;transform:translateX(-50%);width:5px;height:5px;border-radius:50%;background:var(--accent-green)}}
  /* SIDEBAR */
  .sidebar{{display:flex;flex-direction:column;gap:20px}}
  .latest-card{{display:flex;flex-direction:column;gap:8px;background:var(--surface);border:1px solid rgba(230,57,70,.3);border-radius:14px;padding:22px;text-decoration:none;transition:border-color .2s,box-shadow .2s}}
  .latest-card:hover{{border-color:rgba(230,57,70,.6);box-shadow:0 8px 32px rgba(230,57,70,.1)}}
  .latest-label{{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--accent-red)}}
  .latest-date{{font-size:13px;color:var(--text-muted)}}
  .latest-headline{{font-size:15px;font-weight:700;color:var(--text);line-height:1.45}}
  .latest-cta{{font-size:13px;font-weight:700;color:var(--accent-blue);margin-top:4px}}
  .recent-section{{background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden}}
  .recent-title{{background:var(--surface2);padding:14px 20px;font-size:13px;font-weight:800;color:var(--text);border-bottom:1px solid var(--border);letter-spacing:.3px}}
  .recent-item{{display:flex;align-items:flex-start;gap:10px;padding:14px 20px;border-bottom:1px solid rgba(30,45,71,.5);text-decoration:none;transition:background .15s}}
  .recent-item:last-child{{border-bottom:none}}
  .recent-item:hover{{background:rgba(255,255,255,.02)}}
  .recent-date{{font-size:11px;font-weight:700;color:var(--accent-amber);white-space:nowrap;min-width:80px;margin-top:2px}}
  .recent-headline{{font-size:12px;color:var(--text-dim);line-height:1.5;flex:1}}
  .recent-arrow{{color:var(--text-muted);font-size:14px;margin-top:1px}}
  /* EMPTY STATE */
  .empty-state{{padding:60px 24px;text-align:center;color:var(--text-muted)}}
  .empty-state p{{font-size:14px;margin-top:8px}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <h1>War Room</h1>
    <p>US–Iran Crisis · Daily Intelligence Archive</p>
  </div>
  <div class="header-stats">
    <div class="hstat">
      <div class="hstat-val">{total}</div>
      <div class="hstat-label">Reports</div>
    </div>
  </div>
</header>

<div class="layout">
  <div class="cal-section">
    <div class="cal-nav">
      <div><h2>{month_name}<span class="year">{yr}</span></h2></div>
      <div class="cal-legend">
        <span><svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#06d6a0"/></svg> Report available</span>
        <span style="color:var(--accent-red)">■ Today</span>
      </div>
    </div>
    <div class="cal-grid">
      {day_headers}
      {cells}
    </div>
    {'<div class="empty-state"><div style="font-size:32px">📅</div><p>No reports yet. Run generate_report.py to create your first report.</p></div>' if not reports else ''}
  </div>

  <div class="sidebar">
    {latest_html}
    <div class="recent-section">
      <div class="recent-title">📋 All Reports</div>
      {recent if recent else '<div class="empty-state"><p>No reports yet.</p></div>'}
    </div>
  </div>
</div>
</body>
</html>""")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example → .env and add your key.")
        sys.exit(1)

    print(f"\n🗞  War Room Generator — {TODAY}")
    print("=" * 50)

    # Ensure calendar always exists even if this run fails mid-way
    if not INDEX_FILE.exists():
        print("\n📅 Writing empty calendar …")
        render_index(load_reports())

    client = anthropic.Anthropic(api_key=API_KEY)

    print("\n📡 Gathering live news (4 searches) …")
    raw = gather_news(client)

    print("\n🧠 Structuring data with Claude …")
    try:
        data = structure_data(client, raw)
    except json.JSONDecodeError as e:
        print(f"ERROR parsing Claude JSON response: {e}")
        sys.exit(1)

    print("\n🖊  Rendering daily report …")
    html = render_daily_html(data)
    out_path = NEWS_DIR / f"{TODAY}.html"
    out_path.write_text(html)
    print(f"   ✓ Saved: {out_path}")

    print("\n📅 Updating calendar …")
    reports = load_reports()
    reports = upsert_report(reports, data.get("headline_of_day", "Daily Intelligence Report"))
    save_reports(reports)
    render_index(reports)
    print(f"   ✓ Saved: {INDEX_FILE}")

    print(f"\n✅ Done. Open: {INDEX_FILE}\n")


if __name__ == "__main__":
    main()
