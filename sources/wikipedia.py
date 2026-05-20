import re
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from constants import PHASE_CZ, TEAM_ALIAS_LOOKUP, TEAM_FLAGS, TZ
from models import Game, TournamentConfig
from sources.common import (
    extract_score_and_status,
    fetch_json,
    fetch_url,
    log,
    normalize_date_text,
    normalize_team,
    normalize_team_name,
)


def parse_wikipedia_schedule(cfg: TournamentConfig) -> List[Game]:
    if not cfg.wikipedia_url:
        return []

    if "cs.wikipedia.org" in cfg.wikipedia_url and cfg.category == "men":
        wt_games = parse_hokejbox2_from_wikitext(cfg)
        log(f"Hokejbox2 wikitext parser games for {cfg.key}: {len(wt_games)}")
        if wt_games:
            return wt_games

    html = fetch_url(cfg.wikipedia_url)
    if "cs.wikipedia.org" in cfg.wikipedia_url and cfg.category == "men":
        cz_games = parse_czech_wikipedia_mens_schedule(html, cfg)
        log(f"Czech Wikipedia men's parser games for {cfg.key}: {len(cz_games)}")
        if cz_games:
            return cz_games

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", class_=re.compile(r"wikitable"))
    games: List[Game] = []

    for table in tables:
        caption_text = ""
        caption = table.find("caption")
        if caption:
            caption_text = caption.get_text(" ", strip=True)

        header_cells = table.find_all("th")
        header_texts = [h.get_text(" ", strip=True).lower() for h in header_cells]
        date_idx = time_idx = venue_idx = None
        team1_idx = team2_idx = None
        for idx, header in enumerate(header_texts):
            if date_idx is None and "date" in header:
                date_idx = idx
            if time_idx is None and "time" in header:
                time_idx = idx
            if venue_idx is None and "venue" in header:
                venue_idx = idx
            if "home" in header or "team 1" in header:
                team1_idx = idx
            if "away" in header or "team 2" in header:
                team2_idx = idx

        current_date: Optional[datetime] = None
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]
            row_text = " ".join(texts)
            if not row_text or "schedule" in row_text.lower():
                continue

            raw_date = texts[date_idx] if date_idx is not None and date_idx < len(texts) else ""
            raw_time = texts[time_idx] if time_idx is not None and time_idx < len(texts) else ""

            if raw_date and raw_date.strip().lower() not in {"date", "datum"}:
                try:
                    dt = dateparser.parse(normalize_date_text(raw_date), dayfirst=True, fuzzy=True)
                except (ValueError, TypeError):
                    dt = None
                if dt:
                    if dt.year == 1900:
                        dt = dt.replace(year=2026)
                    current_date = dt

            time_match = re.search(r"\b(\d{1,2}:\d{2})\b", raw_time or row_text)
            if not time_match or not current_date:
                continue
            dt = dateparser.parse(f"{current_date.date()} {time_match.group(1)}", fuzzy=True)
            if not dt:
                continue
            start = TZ.localize(datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute))

            phase_key = infer_phase(f"{caption_text} {row_text}")
            group_label = infer_group(f"{caption_text} {row_text}")

            team1 = team2 = "TBD"
            if team1_idx is not None and team1_idx < len(texts):
                team1 = normalize_team_name(texts[team1_idx])
            if team2_idx is not None and team2_idx < len(texts):
                team2 = normalize_team_name(texts[team2_idx])
            if team1 == "TBD" or team2 == "TBD":
                found = []
                for cell_text in texts:
                    code = normalize_team_name(cell_text)
                    if code != "TBD" and code not in found:
                        found.append(code)
                if len(found) >= 2:
                    team1, team2 = found[0], found[1]

            venue = texts[venue_idx] if venue_idx is not None and venue_idx < len(texts) else None
            score1, score2, status = extract_score_and_status(row_text)
            games.append(
                Game(
                    tournament_key=cfg.key,
                    tournament_title=cfg.title,
                    category=cfg.category,
                    start=start,
                    team1=team1,
                    team2=team2,
                    phase_key=phase_key,
                    phase_label=PHASE_CZ.get(phase_key, "Skupina"),
                    group_label=group_label,
                    venue=venue,
                    score1=score1,
                    score2=score2,
                    status_suffix=status,
                )
            )

    log(f"Wikipedia tables parsed games for {cfg.key}: {len(games)}")
    if games:
        return games

    vevent_games = parse_wikipedia_vevents(html, cfg)
    log(f"Wikipedia vevent parsed games for {cfg.key}: {len(vevent_games)}")
    if vevent_games:
        return vevent_games

    fallback_games = parse_wikipedia_schedule_text(html, cfg)
    log(f"Wikipedia text fallback games for {cfg.key}: {len(fallback_games)}")
    if fallback_games:
        return fallback_games

    api_games = parse_wikipedia_wikitext(cfg)
    log(f"Wikipedia wikitext parsed games for {cfg.key}: {len(api_games)}")
    return api_games


def _extract_team_from_lh(text: str) -> str:
    """Extract 3-letter team code from {{Lh|CZE}} or {{Lh-rt|SWE}} wikitext, or 'TBD'."""
    m = re.search(r"\{\{Lh(?:-rt)?\|([A-Za-z]{2,3})\b", text, re.IGNORECASE)
    if m:
        code = m.group(1).upper()
        if code in TEAM_FLAGS:
            return code
    m = re.search(r"\b([A-Z]{3})\b", text)
    if m and m.group(1) in TEAM_FLAGS:
        return m.group(1)
    return "TBD"


def _parse_hokejbox2_block(block: str, cfg: TournamentConfig, phase_key: str, group_label: Optional[str]) -> Optional[Game]:
    """Parse a single {{Hokejbox2 ...}} wikitext block into a Game, or None if invalid."""
    params: dict = {}
    for line in block.splitlines():
        m = re.match(r"\s*\|\s*([^=|{}\n]+?)\s*=\s*(.*)", line)
        if m:
            params[m.group(1).strip()] = m.group(2).strip()

    datum = params.get("datum", "")
    cas = params.get("čas", params.get("cas", ""))
    muz1_raw = params.get("mužstvo1", params.get("muzstvo1", ""))
    muz2_raw = params.get("mužstvo2", params.get("muzstvo2", ""))
    skore_raw = params.get("skóre", params.get("skore", ""))
    tretiny_raw = params.get("třetiny", params.get("tretiny", ""))

    if not datum or not cas:
        return None

    try:
        date_dt = dateparser.parse(normalize_date_text(datum), dayfirst=True, fuzzy=True)
    except (ValueError, TypeError):
        return None
    if not date_dt:
        return None

    m = re.search(r"(\d{1,2}):(\d{2})", cas)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    start = TZ.localize(datetime(date_dt.year, date_dt.month, date_dt.day, hour, minute))

    team1 = _extract_team_from_lh(muz1_raw)
    team2 = _extract_team_from_lh(muz2_raw)

    score1 = score2 = None
    status_suffix = None
    if skore_raw:
        # Strip wiki links: [[Prodloužení|PP]] → PP, [[link]] → link
        clean = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", skore_raw)
        clean = re.sub(r"'{2,}", "", clean).strip()
        sm = re.match(r"^(\d+)\s*[:\-–]\s*(\d+)\s*(.*)?$", clean)
        if sm:
            score1 = int(sm.group(1))
            score2 = int(sm.group(2))
            suffix = (sm.group(3) or "").strip().lower()
            if "pp" in suffix or "ot" in suffix or "prodloužení" in suffix:
                status_suffix = "OT"
            elif "so" in suffix or "sn" in suffix or "nájezdy" in suffix:
                status_suffix = "SO"
            else:
                status_suffix = "FT"

    venue_raw = params.get("stadión", params.get("stadion", ""))
    venue: Optional[str] = None
    if venue_raw:
        v = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", venue_raw)
        v = re.sub(r"\{\{[^}]+\}\}", "", v).strip()
        if v:
            venue = v

    tretiny: Optional[str] = None
    if tretiny_raw:
        clean_t = re.sub(r"<br\s*/?>", ", ", tretiny_raw)
        clean_t = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", clean_t)
        clean_t = re.sub(r"\{\{[^}]+\}\}", "", clean_t).strip(" ,")
        if clean_t:
            tretiny = clean_t

    return Game(
        tournament_key=cfg.key,
        tournament_title=cfg.title,
        category=cfg.category,
        start=start,
        team1=team1,
        team2=team2,
        phase_key=phase_key,
        phase_label=PHASE_CZ.get(phase_key, "Skupina"),
        group_label=group_label,
        venue=venue,
        gamecenter=cfg.wikipedia_url,
        tretiny=tretiny,
        score1=score1,
        score2=score2,
        status_suffix=status_suffix,
    )


def parse_hokejbox2_from_wikitext(cfg: TournamentConfig) -> List[Game]:
    """Parse Czech Wikipedia MS page by reading Hokejbox2 templates directly from wikitext.

    This avoids all HTML-rendering ambiguities — the wikitext has score as a named
    parameter (| skóre =4 : 1) so there is no risk of it being lost in extraction.
    """
    if not cfg.wikipedia_url:
        return []
    match_url = re.search(r"/wiki/([^#?]+)", cfg.wikipedia_url)
    if not match_url:
        return []
    title = match_url.group(1)
    parsed = urlparse(cfg.wikipedia_url)
    api_host = parsed.netloc or "cs.wikipedia.org"
    api_url = f"https://{api_host}/w/api.php?action=parse&prop=wikitext&format=json&page={title}"

    try:
        data = fetch_json(api_url)
    except Exception as exc:
        log(f"Wikitext fetch failed for {cfg.key}: {exc}")
        return []

    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return []

    PLAYOFF_PHASE_MAP = {
        "Čtvrtfinále": "quarterfinals",
        "Semifinále": "semifinals",
        "Zápas o 3. místo": "bronze",
        "O 3. místo": "bronze",
        "O bronz": "bronze",
        "Finále": "gold",
    }

    games: List[Game] = []
    current_phase = "preliminary"
    current_group: Optional[str] = None
    in_scope = False  # inside Group B or Playoff

    lines = wikitext.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        heading = re.match(r"^(={2,4})\s*(.*?)\s*\1\s*$", line)
        if heading:
            text = heading.group(2)
            if "Skupina B" in text:
                in_scope = True
                current_phase = "preliminary"
                current_group = "Skupina B"
            elif text.strip() == "Play-off":
                in_scope = True
                current_phase = "quarterfinals"
                current_group = None
            elif in_scope:
                matched_phase = next((v for k, v in PLAYOFF_PHASE_MAP.items() if k in text), None)
                if matched_phase:
                    current_phase = matched_phase
                    current_group = None
                elif heading.group(1) == "==" and "Skupina B" not in text:
                    # Top-level (==) section change exits scope; sub-sections (===, ====) don't
                    in_scope = False
            i += 1
            continue

        if not in_scope:
            i += 1
            continue

        if "{{Hokejbox2" not in line:
            i += 1
            continue

        # Collect the full template block (balanced braces)
        block_lines = [line]
        depth = line.count("{{") - line.count("}}")
        i += 1
        while depth > 0 and i < len(lines):
            block_lines.append(lines[i])
            depth += lines[i].count("{{") - lines[i].count("}}")
            i += 1

        block = "\n".join(block_lines)
        game = _parse_hokejbox2_block(block, cfg, current_phase, current_group)
        if game:
            games.append(game)

    log(f"parse_hokejbox2_from_wikitext found {len(games)} games for {cfg.key}")
    return games


def parse_czech_wikipedia_mens_schedule(html: str, cfg: TournamentConfig) -> List[Game]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()

    lines = [re.sub(r"\s+", " ", line.replace("\xa0", " ").strip()) for line in soup.get_text("\n").splitlines() if line.strip()]
    games: List[Game] = []
    current_date: Optional[datetime] = None
    seen_times: set = set()
    skip_tokens = {"[", "]", "|", "editovat", "editovat zdroj", ","}
    group_b_indices = [idx for idx, line in enumerate(lines) if line == "Skupina B – Fribourg"]
    if not group_b_indices:
        return games

    PLAYOFF_PHASE_MAP = {
        "Čtvrtfinále": "quarterfinals",
        "Semifinále": "semifinals",
        "O bronz": "bronze",
        "O 3. místo": "bronze",
        "Finále": "gold",
    }

    score_re = re.compile(r"^(\d+)\s*[:\-–]\s*(\d+)\s*(.*)?$")
    date_re = re.compile(r"\d{1,2}\.\s+[A-Za-zÁ-ž]+\s+20\d{2}")

    start_index = group_b_indices[-1]
    in_group_b = False
    in_playoff = False
    in_matches = False
    current_phase_key = "preliminary"
    current_group_label: Optional[str] = None

    i = start_index
    while i < len(lines):
        line = lines[i]

        if line == "Skupina B – Fribourg":
            in_group_b = True
            in_playoff = False
            in_matches = False
            current_phase_key = "preliminary"
            current_group_label = "Skupina B"
            i += 1
            continue

        if not (in_group_b or in_playoff):
            i += 1
            continue

        if line == "Play-off":
            in_group_b = False
            in_playoff = True
            in_matches = True
            current_date = None
            i += 1
            continue

        if in_playoff:
            matched = False
            for label, phase_key in PLAYOFF_PHASE_MAP.items():
                if line == label:
                    current_phase_key = phase_key
                    current_group_label = None
                    matched = True
                    break
            if matched:
                i += 1
                continue

        if in_group_b:
            if line == "Tabulka":
                in_matches = False
                i += 1
                continue
            if line == "Zápasy":
                in_matches = True
                i += 1
                continue
            if not in_matches:
                i += 1
                continue

        date_match = re.fullmatch(r"(\d{1,2}\.\s+[A-Za-zÁ-ž]+\s+20\d{2})", line)
        if date_match:
            try:
                current_date = dateparser.parse(normalize_date_text(date_match.group(1)), dayfirst=True, fuzzy=True)
            except (ValueError, TypeError):
                current_date = None
            i += 1
            continue

        if not current_date:
            i += 1
            continue

        if not re.fullmatch(r"\d{1,2}:\d{2}", line):
            i += 1
            continue

        # Skip duplicate time lines — unplayed games repeat the start time in the
        # centre column (score position), which would otherwise generate a phantom game.
        time_key = (current_date.date(), line)
        if time_key in seen_times:
            i += 1
            continue
        seen_times.add(time_key)

        time_str = line

        # Window scan: find teams and score in any order within the next 12 lines.
        # The HTML template changes after a game is played (score/venue may appear
        # before team names), so strict sequential parsing is not reliable.
        found_teams: List[str] = []
        score1: Optional[int] = None
        score2: Optional[int] = None
        status_suffix: Optional[str] = None
        venue_line: Optional[str] = None

        for j in range(i + 1, min(i + 13, len(lines))):
            w = lines[j]
            if not w or w in skip_tokens or w == "* * *":
                continue
            if re.match(r"^\(\d", w):
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}", w):
                continue
            if date_re.search(w):
                continue
            team_code = normalize_team_name(w)
            if team_code != "TBD" and team_code in TEAM_FLAGS:
                if team_code not in found_teams:
                    found_teams.append(team_code)
                continue
            if score1 is None:
                sm = score_re.match(w)
                if sm:
                    score1 = int(sm.group(1))
                    score2 = int(sm.group(2))
                    suffix = (sm.group(3) or "").strip().lower()
                    if "pp" in suffix or "ot" in suffix:
                        status_suffix = "OT"
                    elif "so" in suffix or "sn" in suffix:
                        status_suffix = "SO"
                    else:
                        status_suffix = "FT"
                    continue
            if venue_line is None and len(w) > 5:
                skip_venue = {"Návštěvnost", "Report", "Brankář", "Rozhodčí", "Čároví", "Střely", "Tresty"}
                if not any(s in w for s in skip_venue):
                    venue_line = w

        if len(found_teams) < 2:
            i += 1
            continue

        team1_code, team2_code = found_teams[0], found_teams[1]
        start = TZ.localize(
            datetime(current_date.year, current_date.month, current_date.day, int(time_str[:2]), int(time_str[3:]))
        )

        games.append(
            Game(
                tournament_key=cfg.key,
                tournament_title=cfg.title,
                category=cfg.category,
                start=start,
                team1=team1_code,
                team2=team2_code,
                phase_key=current_phase_key,
                phase_label=PHASE_CZ.get(current_phase_key, "Skupina"),
                group_label=current_group_label,
                venue=venue_line,
                score1=score1,
                score2=score2,
                status_suffix=status_suffix,
            )
        )
        i += 1

    return games


def infer_phase(text: str) -> str:
    lower = text.lower()
    if "quarterfinal" in lower or "čtvrtfinále" in lower:
        return "quarterfinals"
    if "semifinal" in lower or "semifinále" in lower:
        return "semifinals"
    if "bronze" in lower or "o 3. místo" in lower or "o bronz" in lower:
        return "bronze"
    if "gold" in lower or "final" in lower or "finále" in lower:
        return "gold"
    return "preliminary"


def infer_group(text: str) -> Optional[str]:
    match = re.search(r"(?:Group|Skupina)\s+([A-Z])", text)
    if not match:
        return None
    return f"Skupina {match.group(1)}"


def parse_wikipedia_schedule_text(html: str, cfg: TournamentConfig) -> List[Game]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    lines = [re.sub(r"\s+", " ", line.strip()) for line in soup.get_text("\n").splitlines() if line.strip()]

    team_names = sorted(TEAM_ALIAS_LOOKUP.keys(), key=len, reverse=True)
    team_names += ["tbd"]

    games: List[Game] = []
    current_date: Optional[datetime] = None
    current_time: Optional[Tuple[int, int]] = None
    current_phase = "preliminary"
    current_group: Optional[str] = None

    i = 0
    while i < len(lines):
        line = lines[i]

        maybe_group = infer_group(line)
        if maybe_group:
            current_group = maybe_group
            current_phase = "preliminary"
            i += 1
            continue

        current_phase = infer_phase(line) if infer_phase(line) != "preliminary" else current_phase
        if current_phase != "preliminary" and infer_phase(line) != "preliminary":
            current_group = None
            i += 1
            continue

        m_date = re.search(r"\b(\d{1,2}(?:\.)?\s+[A-Za-zÁ-ž]+\s+20\d{2})\b", line)
        if m_date:
            try:
                current_date = dateparser.parse(normalize_date_text(m_date.group(1)), dayfirst=True, fuzzy=True)
            except (ValueError, TypeError):
                current_date = None
            i += 1
            continue

        if re.fullmatch(r"\d{1,2}:\d{2}", line):
            hour, minute = line.split(":")
            current_time = (int(hour), int(minute))
            i += 1
            continue

        if not current_date:
            i += 1
            continue

        lower = line.lower()
        if any(skip in lower for skip in {"attendance", "goalies", "referees", "linesmen"}):
            i += 1
            continue

        inline_time_match = re.match(r"^(\d{1,2}:\d{2})\b", line)
        inline_time: Optional[Tuple[int, int]] = None
        if inline_time_match:
            hour, minute = inline_time_match.group(1).split(":")
            inline_time = (int(hour), int(minute))

        effective_time = inline_time or current_time
        if not effective_time:
            i += 1
            continue

        positions = []
        for name in team_names:
            idx = lower.find(name)
            if idx != -1:
                positions.append((idx, name))
        if len(positions) < 2 and "tbd v tbd" not in lower:
            i += 1
            continue

        if "tbd v tbd" in lower:
            team1 = "TBD"
            team2 = "TBD"
        else:
            positions.sort(key=lambda item: item[0])
            deduped = []
            for _, name in positions:
                code = normalize_team_name(name)
                if code != "TBD" and code not in deduped:
                    deduped.append(code)
            if len(deduped) < 2:
                i += 1
                continue
            team1 = deduped[0]
            team2 = deduped[1]

        score1, score2, status = extract_score_and_status(line)
        start = TZ.localize(
            datetime(current_date.year, current_date.month, current_date.day, effective_time[0], effective_time[1])
        )
        games.append(
            Game(
                tournament_key=cfg.key,
                tournament_title=cfg.title,
                category=cfg.category,
                start=start,
                team1=team1,
                team2=team2,
                phase_key=current_phase,
                phase_label=PHASE_CZ.get(current_phase, "Skupina"),
                group_label=current_group,
                venue=None,
                score1=score1,
                score2=score2,
                status_suffix=status,
            )
        )

        # Inline Czech Wikipedia rows include the time in the same line as the matchup.
        # Clear the carried time so the next row has to provide its own time again.
        if inline_time:
            current_time = None
        i += 1

    return games


def parse_wikipedia_vevents(html: str, cfg: TournamentConfig) -> List[Game]:
    soup = BeautifulSoup(html, "lxml")
    games: List[Game] = []

    def infer_phase_from_heading(node) -> Tuple[str, Optional[str]]:
        heading = node.find_previous(["h2", "h3"])
        if not heading:
            return "preliminary", None
        return infer_phase(heading.get_text(" ", strip=True)), infer_group(heading.get_text(" ", strip=True))

    for summary in soup.select("table.vevent tr.summary"):
        cells = summary.find_all("td")
        if len(cells) < 4:
            continue

        left_text = " ".join(cells[0].stripped_strings)
        m_date = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+20\d{2})", left_text)
        m_time = re.search(r"\b(\d{1,2}:\d{2})\b", left_text)
        if not (m_date and m_time):
            continue
        try:
            dt = dateparser.parse(f"{normalize_date_text(m_date.group(1))} {m_time.group(1)}", dayfirst=True, fuzzy=True)
        except (ValueError, TypeError):
            continue
        start = TZ.localize(datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute))

        team1 = normalize_team_name(cells[1].get_text(" ", strip=True))
        team2 = normalize_team_name(cells[3].get_text(" ", strip=True))
        center_text = cells[2].get_text(" ", strip=True)
        score1, score2, status = extract_score_and_status(center_text)
        phase_key, group_label = infer_phase_from_heading(summary)
        venue = cells[4].get_text(" ", strip=True) if len(cells) > 4 else None

        games.append(
            Game(
                tournament_key=cfg.key,
                tournament_title=cfg.title,
                category=cfg.category,
                start=start,
                team1=team1,
                team2=team2,
                phase_key=phase_key,
                phase_label=PHASE_CZ.get(phase_key, "Skupina"),
                group_label=group_label,
                venue=venue,
                score1=score1,
                score2=score2,
                status_suffix=status,
            )
        )

    return games


def parse_wikipedia_wikitext(cfg: TournamentConfig) -> List[Game]:
    if not cfg.wikipedia_url:
        return []
    match = re.search(r"/wiki/([^#?]+)", cfg.wikipedia_url)
    if not match:
        return []
    title = match.group(1)
    parsed = urlparse(cfg.wikipedia_url)
    api_host = parsed.netloc or "en.wikipedia.org"
    api_url = f"https://{api_host}/w/api.php?action=parse&prop=wikitext&format=json&page={title}"
    try:
        data = fetch_json(api_url)
    except Exception:
        return []
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return []

    lines = wikitext.splitlines()
    games: List[Game] = []
    current_phase = "preliminary"
    current_group: Optional[str] = None
    current_date: Optional[datetime] = None

    for line in lines:
        maybe_phase = infer_phase(line)
        if line.startswith("==") and maybe_phase != "preliminary":
            current_phase = maybe_phase
            current_group = None
        maybe_group = infer_group(line)
        if line.startswith("===") and maybe_group:
            current_group = maybe_group
            current_phase = "preliminary"

        if not line.startswith("|-"):
            continue

        m_date = re.search(r"(\d{1,2}(?:\.)?\s+[A-Za-zÁ-ž]+\s+20\d{2})", line)
        if m_date:
            try:
                current_date = dateparser.parse(normalize_date_text(m_date.group(1)), dayfirst=True, fuzzy=True)
            except (ValueError, TypeError):
                current_date = None
        m_time = re.search(r"\b(\d{1,2}:\d{2})\b", line)
        if not (current_date and m_time):
            continue

        dt = dateparser.parse(f"{current_date.date()} {m_time.group(1)}", fuzzy=True)
        if not dt:
            continue
        start = TZ.localize(datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute))

        teams = [normalize_team_name(team) for team in re.findall(r"\{\{flag(?:icon|country)?\|([^}|]+)", line)]
        teams = [team for team in teams if team != "TBD"]
        if len(teams) < 2:
            teams = [normalize_team(code) for code in re.findall(r"\b([A-Z]{3})\b", line)]
        if len(teams) < 2:
            continue
        score1, score2, status = extract_score_and_status(line)

        games.append(
            Game(
                tournament_key=cfg.key,
                tournament_title=cfg.title,
                category=cfg.category,
                start=start,
                team1=teams[0],
                team2=teams[1],
                phase_key=current_phase,
                phase_label=PHASE_CZ.get(current_phase, "Skupina"),
                group_label=current_group,
                venue=None,
                score1=score1,
                score2=score2,
                status_suffix=status,
            )
        )

    return games
