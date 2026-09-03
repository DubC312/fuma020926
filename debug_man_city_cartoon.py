#!/usr/bin/env python3
"""
DEBUG-TEST: Manchester City Team-Seite im Cartoon-View (view=7).

Ziel:
- Team-Seite laden
- nach Haaland suchen
- alle player/cartoon/media URLs ausgeben
- HTML-Ausschnitt rund um "Haaland" ausgeben
- KEINE Dateien verändern
"""

from urllib.parse import urljoin
import html as html_lib
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.thesportsdb.com"
TEAM_URL = BASE + "/team/133613-manchester-city?view=7#playerImages"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FootballMathTrainer-TeamCartoon-Debug/1.0; +GitHub-Actions)"
}

def norm(u):
    if not u:
        return ""
    u = html_lib.unescape(str(u)).strip()
    if u.startswith("//"):
        return "https:" + u
    return urljoin(BASE + "/", u)

print("=== 1. MANCHESTER CITY CARTOON-VIEW LADEN ===")
print("URL:", TEAM_URL)

r = requests.get(TEAM_URL, headers=HEADERS, timeout=30, allow_redirects=True)
print("HTTP Status:", r.status_code)
print("Finale URL:", r.url)
print("Content-Type:", r.headers.get("content-type"))
print("HTML-Zeichen:", len(r.text))
r.raise_for_status()

html = r.text

print("\n=== 2. TREFFER FÜR 'HAALAND' ===")
matches = list(re.finditer(r"haaland", html, flags=re.I))
print("Anzahl Haaland-Treffer:", len(matches))

for i, m in enumerate(matches[:20], start=1):
    a = max(0, m.start() - 700)
    b = min(len(html), m.end() + 1400)
    snippet = re.sub(r"\s+", " ", html[a:b])
    print(f"\n--- Haaland-Treffer {i} ---")
    print(snippet)

print("\n=== 3. TREFFER FÜR 'cartoon' ===")
cmatches = list(re.finditer(r"cartoon", html, flags=re.I))
print("Anzahl cartoon-Treffer:", len(cmatches))

for i, m in enumerate(cmatches[:30], start=1):
    a = max(0, m.start() - 300)
    b = min(len(html), m.end() + 650)
    snippet = re.sub(r"\s+", " ", html[a:b])
    print(f"\n--- Cartoon-Treffer {i} ---")
    print(snippet)

print("\n=== 4. ALLE INTERESSANTEN URLS AUS IMG/SOURCE/A ===")
soup = BeautifulSoup(html, "html.parser")
urls = []

for tag in soup.find_all(["img", "source", "a"]):
    for attr in ("src", "data-src", "data-original", "href", "srcset"):
        value = tag.get(attr)
        if not value:
            continue
        for part in str(value).split(","):
            u = part.strip().split(" ")[0]
            if not u:
                continue
            u = norm(u)
            if u and u not in urls:
                urls.append(u)

interesting = [
    u for u in urls
    if any(k in u.lower() for k in [
        "/player/", "cartoon", "/media/player/", "thumb", "render", "cutout"
    ])
]

print("Alle eindeutigen URLs:", len(urls))
print("Interessante URLs:", len(interesting))

for i, u in enumerate(interesting[:400], start=1):
    marker = ""
    lu = u.lower()
    if "cartoon" in lu:
        marker += "  <== CARTOON"
    if "34169116" in lu or "haaland" in lu:
        marker += "  <== HAALAND"
    print(f"{i:03d}: {u}{marker}")

print("\n=== 5. DIREKTE MEDIEN-URLS IM HTML ===")
patterns = [
    r'https?://[^"\']+/images/media/player/[^"\'<>\s]+',
    r'//[^"\']+/images/media/player/[^"\'<>\s]+',
    r'/images/media/player/[^"\'<>\s]+',
]
media = []
for pat in patterns:
    for m in re.findall(pat, html, flags=re.I):
        u = norm(m)
        if u not in media:
            media.append(u)

for i, u in enumerate(media[:500], start=1):
    marker = "  <== CARTOON?" if "cartoon" in u.lower() else ""
    print(f"{i:03d}: {u}{marker}")

print("\n=== 6. HAALAND-BLOCK MIT ALLEN TAG-ATTRIBUTEN ===")
haaland_node = None
for text_node in soup.find_all(string=re.compile("Haaland", re.I)):
    haaland_node = text_node.parent
    break

if not haaland_node:
    print("Kein Haaland-Textknoten gefunden.")
else:
    node = haaland_node
    for _ in range(5):
        if not node:
            break
        block = str(node)
        if len(block) > 300:
            print(block[:12000])
            break
        node = node.parent

print("\n=== FERTIG ===")
print("Bitte schicke mir aus dem Log besonders die Bereiche 2, 4, 5 und 6.")
