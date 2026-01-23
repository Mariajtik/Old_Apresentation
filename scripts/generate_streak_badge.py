#!/usr/bin/env python3
# Gera docs/longest-streak.svg com o maior streak (longest) e o streak atual (current)
# Usa: GITHUB_TOKEN (obrigatório) e opcional GITHUB_USER (padrão: Mariajtik)

import os
import sys
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Erro: variável de ambiente GITHUB_TOKEN não definida", file=sys.stderr)
    sys.exit(2)

USER = os.environ.get("GITHUB_USER", "Mariajtik")
OUT_PATH = "docs/longest-streak.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Accept": "application/json"
}

def fetch_calendar(user):
    resp = requests.post("https://api.github.com/graphql",
                         json={"query": QUERY, "variables": {"login": user}},
                         headers=HEADERS,
                         timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

def flatten_days(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append({"date": d["date"], "count": d["contributionCount"]})
    # ordenar por data (asc)
    days.sort(key=lambda x: x["date"])
    return days

def compute_streaks(days):
    longest = 0
    current = 0
    prev_date = None
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        if d["count"] > 0:
            if prev_date is None or dt == prev_date + timedelta(days=1):
                current += 1
            else:
                current = 1
            if current > longest:
                longest = current
        else:
            current = 0
        prev_date = dt

    # calcular streak atual (contar regressivamente a partir do dia mais recente)
    last_date = datetime.strptime(days[-1]["date"], "%Y-%m-%d").date()
    cur_streak = 0
    day_lookup = {datetime.strptime(d["date"], "%Y-%m-%d").date(): d["count"] for d in days}
    d = last_date
    while True:
        count = day_lookup.get(d, 0)
        if count and count > 0:
            cur_streak += 1
            d = d - timedelta(days=1)
        else:
            break

    return longest, cur_streak, last_date

def svg_for(longest, current):
    title = "Maior streak"
    subtitle = f"{longest} dia" + ("s" if longest != 1 else "")
    extra = f"Atual: {current}d"
    text = f"{title}: {subtitle} — {extra}"
    width = max(220, 10 + len(text) * 8)
    height = 40
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect rx="8" width="{width}" height="{height}" fill="#0b1226"/>
  <text x="16" y="25" fill="#ffffff" font-family="Verdana,Arial" font-size="13">{title}: <tspan font-weight="700">{subtitle}</tspan> — {extra}</text>
</svg>'''
    return svg

def main():
    try:
        weeks = fetch_calendar(USER)
    except Exception as e:
        print(f"Erro ao consultar GraphQL: {e}", file=sys.stderr)
        sys.exit(2)

    days = flatten_days(weeks)
    if not days:
        print("Nenhum dia retornado do calendário de contribuições.", file=sys.stderr)
        sys.exit(2)

    longest, current, last_date = compute_streaks(days)
    svg = svg_for(longest, current)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {OUT_PATH} (longest={longest}, current={current}, last_date={last_date})")

if __name__ == "__main__":
    main()
