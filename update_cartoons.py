#!/usr/bin/env python3
from __future__ import annotations

import html as html_lib
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.thesportsdb.com"
API_KEY = "123"
SEARCH_PLAYER = BASE + f"/api/v1/json/{API_KEY}/searchplayers.php?p="
TEAM_PAGE = BASE + "/team/{team_id}?view=7#playerImages"

API_DELAY_SECONDS = 2.15
PAGE_DELAY_SECONDS = 0.35
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FootballMathTrainer-CartoonUpdater/2.0; +https://github.com/)"
}

PLAYER_FILE_CANDIDATES = (Path("players.json"), Path("data/players.json"))


def find_player_file():
    for path in PLAYER_FILE_CANDIDATES:
        if path.exists():
            return path
    print("FEHLER: Weder players.json noch data/players.json gefunden.", file=sys.stderr)
    raise SystemExit(2)


def normalize(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def absolute_url(value):
    if not value:
        return ""
    value = html_lib.unescape(str(value)).strip()
    if value.startswith("//"):
        return "https:" + value
    return urljoin(BASE + "/", value)


def choose_player_result(results, wanted_name):
    if not results:
        return None
    wanted = normalize(wanted_name)
    exact = [x for x in results if normalize(x.get("strPlayer")) == wanted]
    if exact:
        return exact[0]
    soccer = [x for x in results if normalize(x.get("strSport")) in ("soccer", "football")]
    return soccer[0] if soccer else results[0]


def search_player(session, player):
    query = player.get("search") or player.get("name") or ""
    if not query:
        return None
    try:
        r = session.get(SEARCH_PLAYER + quote(query), timeout=TIMEOUT)
        r.raise_for_status()
        return choose_player_result((r.json().get("player") or []), query)
    except Exception as exc:
        print(f"  API-FEHLER bei {player.get('name', query)}: {exc}")
        return None
    finally:
        time.sleep(API_DELAY_SECONDS)


def parse_team_cartoon_page(session, team_id):
    try:
        r = session.get(TEAM_PAGE.format(team_id=team_id), timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as exc:
        print(f"  TEAM-FEHLER {team_id}: {exc}")
        return {}, 0
    finally:
        time.sleep(PAGE_DELAY_SECONDS)

    soup = BeautifulSoup(r.text, "html.parser")
    found = {}
    player_links = 0

    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "")
        m = re.search(r"/player/(\d+)(?:-|/|$)", href)
        if not m:
            continue
        player_links += 1
        player_id = m.group(1)

        for img in a.find_all("img"):
            for raw in (img.get("src"), img.get("data-src"), img.get("data-original")):
                u = absolute_url(raw)
                if "/images/media/player/cartoon/" in u.lower():
                    found[player_id] = u
                    break
            if player_id in found:
                break

    return found, player_links


def main():
    path = find_player_file()
    players = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(players, list):
        raise SystemExit("FEHLER: players.json muss ein JSON-Array sein.")

    print("=== TheSportsDB Cartoon-Updater ===")
    print("Datei:", path)
    print("Spieler:", len(players))

    session = requests.Session()
    session.headers.update(HEADERS)

    changed = False
    team_to_indexes = defaultdict(list)

    print("\n=== 1. SPIELER- UND TEAM-IDs ERMITTELN ===")
    for i, p in enumerate(players, 1):
        name = p.get("name") or f"Spieler {i}"
        print(f"[{i}/{len(players)}] {name}")
        result = search_player(session, p)
        if not result:
            continue

        pid = str(result.get("idPlayer") or "").strip()
        tid = str(result.get("idTeam") or "").strip()

        if pid and str(p.get("sportsdbId") or "") != pid:
            p["sportsdbId"] = pid
            changed = True
        if tid and str(p.get("sportsdbTeamId") or "") != tid:
            p["sportsdbTeamId"] = tid
            changed = True
        if tid:
            team_to_indexes[tid].append(i - 1)

        print("  -> Player-ID:", pid or "-", "| Team-ID:", tid or "-", "| Team:", result.get("strTeam") or "-")

    print("\nEindeutige Teams:", len(team_to_indexes))
    print("\n=== 2. TEAM-CARTOON-SEITEN LADEN ===")

    team_maps = {}
    for n, tid in enumerate(sorted(team_to_indexes), 1):
        print(f"[Team {n}/{len(team_to_indexes)}] {tid}")
        cmap, link_count = parse_team_cartoon_page(session, tid)
        team_maps[tid] = cmap
        print(f"  -> Spieler-Links: {link_count}, Cartoons: {len(cmap)}")

    print("\n=== 3. CARTOONS ZUORDNEN ===")
    found_count = 0
    changed_count = 0

    for p in players:
        name = p.get("name") or "?"
        pid = str(p.get("sportsdbId") or "").strip()
        tid = str(p.get("sportsdbTeamId") or "").strip()
        cartoon = team_maps.get(tid, {}).get(pid, "") if pid and tid else ""

        if cartoon:
            found_count += 1
            if p.get("cartoon") != cartoon:
                p["cartoon"] = cartoon
                changed = True
                changed_count += 1
                print(f"✓ {name}: {cartoon}")
            else:
                print(f"= {name}: unverändert")
        else:
            if p.get("cartoon"):
                print(f"~ {name}: aktuell nicht gefunden; vorhandene URL bleibt erhalten")
            else:
                print(f"– {name}: kein Cartoon gefunden")

    if changed:
        path.write_text(json.dumps(players, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n=== ERGEBNIS ===")
    print("Spieler mit aktuell gefundenem Cartoon:", found_count)
    print("Cartoon-Felder neu/geändert:", changed_count)
    print("players.json geändert:", "JA" if changed else "NEIN")

    print("\n=== HAALAND-KONTROLLE ===")
    h = next((p for p in players if normalize(p.get("name")) == normalize("Erling Haaland")), None)
    if h:
        print("sportsdbId:", h.get("sportsdbId", "-"))
        print("sportsdbTeamId:", h.get("sportsdbTeamId", "-"))
        print("cartoon:", h.get("cartoon", "-"))
    else:
        print("Erling Haaland nicht gefunden.")


if __name__ == "__main__":
    main()
