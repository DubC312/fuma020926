#!/usr/bin/env python3
"""
DEBUG-TEST nur für Erling Haaland.

Ziel:
- Haaland über TheSportsDB suchen
- seine Player-ID anzeigen
- Cartoon-Archivseite laden
- Statuscode und Seitengröße anzeigen
- alle interessanten Bild-/Link-URLs ausgeben
- HTML-Ausschnitte mit "cartoon" ausgeben

Es wird KEINE players.json verändert.
"""

from urllib.parse import quote, urljoin
import html as html_lib
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.thesportsdb.com"
API = BASE + "/api/v1/json/123/searchplayers.php?p="
ARCHIVE = BASE + "/player_art.php?art=cartoon&p={id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FootballMathTrainer-Debug/1.0; +GitHub-Actions)"
}

def norm(u):
    if not u:
        return ""
    u = html_lib.unescape(str(u)).strip()
    if u.startswith("//"):
        return "https:" + u
    return urljoin(BASE + "/", u)

print("=== 1. HAALAND ÜBER API SUCHEN ===")
r = requests.get(API + quote("Erling Haaland"), headers=HEADERS, timeout=30)
print("API Status:", r.status_code)
r.raise_for_status()

data = r.json()
players = data.get("player") or []
if not players:
    raise SystemExit("FEHLER: Haaland wurde nicht gefunden.")

p = players[0]
pid = str(p.get("idPlayer") or "")
print("Name:", p.get("strPlayer"))
print("idPlayer:", pid)

if not pid:
    raise SystemExit("FEHLER: Keine idPlayer erhalten.")

url = ARCHIVE.format(id=pid)

print("\n=== 2. CARTOON-ARCHIV LADEN ===")
print("URL:", url)

r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
print("HTTP Status:", r.status_code)
print("Finale URL:", r.url)
print("Content-Type:", r.headers.get("content-type"))
print("HTML-Zeichen:", len(r.text))
r.raise_for_status()

html = r.text

print("\n=== 3. ZEILEN/AUSSCHNITTE MIT 'cartoon' ===")
matches = list(re.finditer(r"cartoon", html, flags=re.I))
print("Anzahl 'cartoon'-Treffer:", len(matches))

for i, m in enumerate(matches[:30], start=1):
    a = max(0, m.start() - 180)
    b = min(len(html), m.end() + 300)
    snippet = re.sub(r"\s+", " ", html[a:b])
    print(f"\n--- Cartoon-Treffer {i} ---")
    print(snippet)

print("\n=== 4. ALLE MÖGLICHEN URLS AUS IMG/SOURCE/A ===")
soup = BeautifulSoup(html, "html.parser")
urls = []

for tag in soup.find_all(["img", "source", "a"]):
    for attr in ("src", "data-src", "data-original", "href", "srcset"):
        value = tag.get(attr)
        if not value:
            continue
        for part in str(value).split(","):
            candidate = part.strip().split(" ")[0]
            if candidate:
                candidate = norm(candidate)
                if candidate not in urls:
                    urls.append(candidate)

interesting = [
    u for u in urls
    if any(x in u.lower() for x in [
        "player", "cartoon", "media", "image", "thumb", "render", "cutout"
    ])
]

print("Alle eindeutigen URLs:", len(urls))
print("Interessante URLs:", len(interesting))

for i, u in enumerate(interesting[:200], start=1):
    print(f"{i:03d}: {u}")

print("\n=== 5. DIREKTE REGEX-TREFFER FÜR BILDDATEIEN ===")
patterns = [
    r'https?://[^"\']+\.(?:png|jpg|jpeg|webp)(?:\?[^"\']*)?',
    r'//[^"\']+\.(?:png|jpg|jpeg|webp)(?:\?[^"\']*)?',
    r'/[^"\']+\.(?:png|jpg|jpeg|webp)(?:\?[^"\']*)?',
]

found = []
for pat in patterns:
    for m in re.findall(pat, html, flags=re.I):
        u = norm(m)
        if u not in found:
            found.append(u)

for i, u in enumerate(found[:300], start=1):
    marker = "  <== CARTOON?" if "cartoon" in u.lower() else ""
    print(f"{i:03d}: {u}{marker}")

print("\n=== FERTIG ===")
print("Bitte kopiere mir aus dem GitHub-Log den Bereich")
print("'3. ZEILEN/AUSSCHNITTE MIT cartoon' und")
print("'4. ALLE MÖGLICHEN URLS' hier in den Chat.")
