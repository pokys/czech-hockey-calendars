import re

import pytz

TZ = pytz.timezone("Europe/Prague")
TEAM_CZ = "CZE"

TEAM_NAMES_CZ = {
    "CZE": "Česko",
    "FIN": "Finsko",
    "SWE": "Švédsko",
    "USA": "USA",
    "CAN": "Kanada",
    "SUI": "Švýcarsko",
    "GER": "Německo",
    "SVK": "Slovensko",
    "LAT": "Lotyšsko",
    "DEN": "Dánsko",
    "NOR": "Norsko",
    "AUT": "Rakousko",
    "FRA": "Francie",
    "ITA": "Itálie",
    "JPN": "Japonsko",
    "CHN": "Čína",
    "KOR": "Jižní Korea",
    "GBR": "Velká Británie",
    "HUN": "Maďarsko",
    "SLO": "Slovinsko",
}

TEAM_FLAGS = {
    "CZE": "🇨🇿",
    "FIN": "🇫🇮",
    "SWE": "🇸🇪",
    "USA": "🇺🇸",
    "CAN": "🇨🇦",
    "SUI": "🇨🇭",
    "GER": "🇩🇪",
    "SVK": "🇸🇰",
    "LAT": "🇱🇻",
    "DEN": "🇩🇰",
    "NOR": "🇳🇴",
    "AUT": "🇦🇹",
    "FRA": "🇫🇷",
    "ITA": "🇮🇹",
    "JPN": "🇯🇵",
    "CHN": "🇨🇳",
    "KOR": "🇰🇷",
    "GBR": "🇬🇧",
    "HUN": "🇭🇺",
    "SLO": "🇸🇮",
}

TEAM_CODE_ALIASES = {
    "Česko": "CZE",
    "Dánsko": "DEN",
    "Finsko": "FIN",
    "Francie": "FRA",
    "Itálie": "ITA",
    "Japonsko": "JPN",
    "Kanada": "CAN",
    "Lotyšsko": "LAT",
    "Maďarsko": "HUN",
    "Německo": "GER",
    "Norsko": "NOR",
    "Rakousko": "AUT",
    "Slovensko": "SVK",
    "Slovinsko": "SLO",
    "Spojené království": "GBR",
    "Velká Británie": "GBR",
    "Švédsko": "SWE",
    "Švýcarsko": "SUI",
    "USA": "USA",
    "Austria": "AUT",
    "Canada": "CAN",
    "China": "CHN",
    "Czech Republic": "CZE",
    "Czechia": "CZE",
    "Czech Republic (CZE)": "CZE",
    "Denmark": "DEN",
    "Finland": "FIN",
    "France": "FRA",
    "Germany": "GER",
    "Great Britain": "GBR",
    "Hungary": "HUN",
    "Italy": "ITA",
    "Japan": "JPN",
    "Latvia": "LAT",
    "Norway": "NOR",
    "Slovakia": "SVK",
    "Slovenia": "SLO",
    "South Korea": "KOR",
    "Sweden": "SWE",
    "Switzerland": "SUI",
    "United States": "USA",
    "United States of America": "USA",
}

TEAM_ALIAS_LOOKUP = {k.lower(): v for k, v in TEAM_CODE_ALIASES.items()}
TEAM_CODE_PATTERN = re.compile(r"\b([A-Z]{3}|TBD)\b")

PHASE_CZ = {
    "preliminary": "Skupina",
    "quarterfinals": "Čtvrtfinále",
    "semifinals": "Semifinále",
    "bronze": "O bronz",
    "gold": "Finále",
}

PLAYOFF_PHASES = {"quarterfinals", "semifinals", "bronze", "gold"}
GENDER_EMOJI = {"women": "👩", "men": "👨"}
MEDAL_EMOJI = {"bronze": "🥉", "gold": "🥇"}
