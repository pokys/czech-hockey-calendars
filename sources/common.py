import json
import re
import sys
from datetime import datetime
from typing import Optional, Tuple

import requests
from dateutil import parser as dateparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from constants import TEAM_ALIAS_LOOKUP, TEAM_CODE_PATTERN

CS_MONTH_REPLACEMENTS = {
    "ledna": "January",
    "února": "February",
    "března": "March",
    "dubna": "April",
    "května": "May",
    "června": "June",
    "července": "July",
    "srpna": "August",
    "září": "September",
    "října": "October",
    "listopadu": "November",
    "prosince": "December",
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=1.0,
        status_forcelist=[403, 408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = build_session()


def fetch_url(url: str, timeout: int = 30) -> str:
    log(f"Fetching {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    resp = SESSION.get(url, timeout=timeout, headers=headers)
    log(f"HTTP {resp.status_code} for {url}")
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str, timeout: int = 30) -> dict:
    text = fetch_url(url, timeout=timeout)
    return json.loads(text)


def normalize_team(code: str) -> str:
    if not code:
        return "TBD"
    return code.strip().upper()


def normalize_team_name(name: str) -> str:
    if not name:
        return "TBD"
    cleaned = re.sub(r"\s+", " ", re.sub(r"\[.*?\]", "", name)).strip()
    if not cleaned:
        return "TBD"
    alias = TEAM_ALIAS_LOOKUP.get(cleaned.lower())
    if alias:
        return alias
    match = TEAM_CODE_PATTERN.search(cleaned)
    if match:
        return match.group(1)
    return "TBD"


def normalize_date_text(text: str) -> str:
    normalized = text
    for cs_name, en_name in CS_MONTH_REPLACEMENTS.items():
        normalized = re.sub(cs_name, en_name, normalized, flags=re.IGNORECASE)
    return normalized


def extract_score_and_status(text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    match = re.search(r"(\d+)\s*[–-]\s*(\d+)", text)
    if not match:
        return None, None, None
    score1 = int(match.group(1))
    score2 = int(match.group(2))
    if re.search(r"\b(GWS|SO)\b", text, re.IGNORECASE):
        status = "SO"
    elif re.search(r"\bOT\b", text, re.IGNORECASE):
        status = "OT"
    else:
        status = "FT"
    return score1, score2, status


def parse_dt(date_text: str, time_text: str, year: Optional[int] = None) -> Optional[datetime]:
    try:
        dt = dateparser.parse(f"{normalize_date_text(date_text)} {time_text}", dayfirst=True, fuzzy=True)
    except (ValueError, TypeError):
        return None
    if not dt:
        return None
    if year and dt.year == 1900:
        dt = dt.replace(year=year)
    return dt
