#!/usr/bin/env python3
"""
Ermittelt TheSportsDB-Player-Cartoon-Bilder serverseitig.

Eingabe/Ausgabe: players.json
Ergänzt gefundene Spieler um:
  "sportsdbId": "...",
  "cartoon": "https://..."

Ein cartoon-Feld wird nur geschrieben, wenn im von TheSportsDB
gelieferten HTML eine passende Bildadresse gefunden wurde.
"""

from pathlib import Path
from urllib.parse import quote, urljoin
import html as html_lib
import json
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.thesportsdb.com"
API = BASE + "/api/v1/json/123/searchplayers.php?p="
ARCHIVE = BASE + "/player_art.php?art=cartoon&p={id}"
FILE = Path("players.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FootballMathTrainer/1.0; +GitHub-Actions)"
}

TEST_NAMES = {
    "Erling Haaland",
    "Kylian Mbappé",
    "Lionel Messi",
    "Harry Kane",
    "Jamal Musiala",
    "Lamine Yamal",
    "Cristiano Ronaldo",
}

def get_json(session, url):
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def get_text(session, url):
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def normalize_url(value):
    if not value:
        return ""
    value = html_lib.unescape(value).strip()
    if value.startswith("//"):
        return "https:" + value
    return urljoin(BASE + "/", value)

def extract_cartoon_url(page_html):
    patterns = [
        r'https?://[^"\']+/images/media/player/cartoon/[^"\'<>\s]+',
        r'//[^"\']+/images/media/player/cartoon/[^"\'<>\s]+',
        r'/images/media/player/cartoon/[^"\'<>\s]+',
    ]
    for pat in patterns:
        m = re.search(pat, page_html, flags=re.I)
        if m:
            return normalize_url(m.group(0))

    soup = BeautifulSoup(page_html, "html.parser")
    candidates = []

    for tag in soup.find_all(["img", "source", "a"]):
        for attr in ("src", "data-src", "data-original", "href", "srcset"):
            value = tag.get(attr)
            if not value:
                continue
            for part in str(value).split(","):
                u = part.strip().split(" ")[0]
                if u:
                    candidates.append(normalize_url(u))

    for u in candidates:
        if re.search(r'/player/cartoon/', u, re.I):
            return u

    for u in candidates:
        if "cartoon" in u.lower() and "/images/media/player/" in u.lower():
            return u

    return ""

def find_player(session, search):
    data = get_json(session, API + quote(search))
    arr = data.get("player") or []
    return arr[0] if arr else None

def write_players(players):
    with FILE.open("w", encoding="utf-8") as f:
        f.write("[\n")
        for i, p in enumerate(players):
            f.write("  " + json.dumps(p, ensure_ascii=False, separators=(",", ":")))
            if i < len(players) - 1:
                f.write(",")
            f.write("\n")
        f.write("]\n")

def main():
    if not FILE.exists():
        print("FEHLER: players.json wurde im Hauptverzeichnis nicht gefunden.")
        print("Lege players.json neben update_cartoons.py ab.")
        sys.exit(2)

    players = json.loads(FILE.read_text(encoding="utf-8"))
    session = requests.Session()

    found = 0
    missing = 0
    errors = 0
    test_results = []

    for n, p in enumerate(players, start=1):
        name = p.get("name", "")
        search = p.get("search") or name

        try:
            api_player = find_player(session, search)
            if not api_player:
                missing += 1
                if name in TEST_NAMES:
                    test_results.append((name, "Spieler nicht gefunden", ""))
                continue

            pid = str(api_player.get("idPlayer") or "")
            if pid:
                p["sportsdbId"] = pid

            if not pid:
                missing += 1
                if name in TEST_NAMES:
                    test_results.append((name, "Keine idPlayer", ""))
                continue

            archive_html = get_text(session, ARCHIVE.format(id=pid))
            cartoon = extract_cartoon_url(archive_html)

            if cartoon:
                p["cartoon"] = cartoon
                found += 1
                if name in TEST_NAMES:
                    test_results.append((name, "OK", cartoon))
            else:
                p.pop("cartoon", None)
                missing += 1
                if name in TEST_NAMES:
                    test_results.append((name, "Kein Cartoon im Archiv gefunden", ""))

        except Exception as e:
            errors += 1
            if name in TEST_NAMES:
                test_results.append((name, f"FEHLER: {type(e).__name__}: {e}", ""))

        time.sleep(2.1)

        if n % 25 == 0:
            print(f"{n}/{len(players)} verarbeitet ...")

    write_players(players)

    print("\n=== 7 TESTSPIELER ===")
    for name, status, url in test_results:
        print(f"{name}: {status}")
        if url:
            print(f"  {url}")

    print("\n=== GESAMT ===")
    print(f"Cartoons gefunden: {found}")
    print(f"Ohne Cartoon/Treffer: {missing}")
    print(f"Fehler: {errors}")
    print(f"Gesamt: {len(players)}")

if __name__ == "__main__":
    main()
