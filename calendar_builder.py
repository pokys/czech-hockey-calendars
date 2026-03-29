import hashlib
from datetime import timedelta
from typing import Dict, Iterable, List

from icalendar import Calendar, Event

from constants import GENDER_EMOJI, MEDAL_EMOJI, PHASE_CZ, PLAYOFF_PHASES, TEAM_CZ, TEAM_FLAGS, TEAM_NAMES_CZ
from models import CalendarSpec, Game


def team_display_with_flag(code: str) -> str:
    if code == "TBD":
        return "TBD"
    flag = TEAM_FLAGS.get(code)
    name = TEAM_NAMES_CZ.get(code, code)
    return f"{flag} {name}" if flag else name


def build_uid(game: Game) -> str:
    base = f"{game.tournament_key}|{game.category}|{game.start.strftime('%Y-%m-%d %H:%M')}|{game.team1}|{game.team2}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest() + "@iihf-calendar"


def assign_playoff_indices(games: List[Game]) -> None:
    counters: Dict[str, int] = {key: 0 for key in PLAYOFF_PHASES}
    for game in sorted(games, key=lambda item: item.start):
        if game.phase_key in PLAYOFF_PHASES:
            counters[game.phase_key] += 1
            game.playoff_index = counters[game.phase_key]


def game_matches_spec(game: Game, spec: CalendarSpec) -> bool:
    if spec.include_all_games:
        return True
    is_czech_game = TEAM_CZ in (game.team1, game.team2)
    is_playoff = game.phase_key in PLAYOFF_PHASES
    return (spec.include_team_cze and is_czech_game) or (spec.include_playoff and is_playoff)


def select_games(games: Iterable[Game], spec: CalendarSpec) -> List[Game]:
    selected = [game for game in games if game_matches_spec(game, spec)]
    return sorted(selected, key=lambda game: game.start)


def build_summary(game: Game) -> str:
    prefix_parts = [part for part in [GENDER_EMOJI.get(game.category), MEDAL_EMOJI.get(game.phase_key)] if part]
    prefix = f"{' '.join(prefix_parts)} " if prefix_parts else ""
    if game.phase_key in PLAYOFF_PHASES and (game.team1 == "TBD" or game.team2 == "TBD"):
        return f"{prefix}{PHASE_CZ[game.phase_key]} {game.playoff_index or 1}"

    summary = f"{prefix}{team_display_with_flag(game.team1)} - {team_display_with_flag(game.team2)}"
    if game.score1 is not None and game.score2 is not None and game.status_suffix:
        summary += f" {game.score1}:{game.score2} ({game.status_suffix})"
    return summary


def build_description(game: Game) -> str:
    parts = [game.phase_label]
    if game.group_label:
        parts.append(game.group_label)
    if game.venue:
        parts.append(game.venue)
    if game.gamecenter:
        parts.append(game.gamecenter)
    return "\n".join(parts)


def games_to_calendar(games: List[Game], cal_name: str) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//czech-hockey-calendars//CZ")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", cal_name)
    cal.add("x-wr-timezone", "Europe/Prague")

    for game in games:
        event = Event()
        event.add("summary", build_summary(game))
        event.add("dtstart", game.start)
        event.add("dtend", game.start + timedelta(hours=3))
        event.add("uid", build_uid(game))
        description = build_description(game)
        if description:
            event.add("description", description)
        cal.add_component(event)

    return cal
