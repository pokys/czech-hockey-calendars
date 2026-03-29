#!/usr/bin/env python3
import os
import sys
from typing import Dict, List, Set

from calendar_builder import assign_playoff_indices, games_to_calendar, select_games
from config.tournaments import TOURNAMENTS
from models import Game, TournamentConfig
from sources.common import log
from sources.wikipedia import parse_wikipedia_schedule

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")


def write_calendar_bytes(content: bytes, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as handle:
        handle.write(content)


def managed_output_paths() -> Set[str]:
    paths: Set[str] = set()
    for cfg in TOURNAMENTS:
        for spec in cfg.calendars:
            paths.add(os.path.join(DIST_DIR, spec.out_file))
            for alias_file in spec.alias_files:
                paths.add(os.path.join(DIST_DIR, alias_file))
    return paths


def remove_stale_outputs() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)
    keep_paths = managed_output_paths()
    for name in os.listdir(DIST_DIR):
        if not name.endswith(".ics"):
            continue
        path = os.path.join(DIST_DIR, name)
        if path in keep_paths:
            continue
        os.remove(path)
        log(f"Removed stale output {path}")


def load_games(cfg: TournamentConfig) -> List[Game]:
    if cfg.category == "combined":
        return []

    try:
        games = parse_wikipedia_schedule(cfg)
        if games:
            return games
    except Exception as exc:
        log(f"Wikipedia source failed for {cfg.key} ({exc})")

    return []


def write_tournament_calendars(cfg: TournamentConfig, games: List[Game]) -> None:
    assign_playoff_indices(games)
    for spec in cfg.calendars:
        selected = select_games(games, spec)
        if not selected:
            log(f"No games selected for {cfg.key}/{spec.key}, writing empty calendar")
        calendar = games_to_calendar(selected, spec.name)
        calendar_bytes = calendar.to_ical()

        out_path = os.path.join(DIST_DIR, spec.out_file)
        write_calendar_bytes(calendar_bytes, out_path)
        log(f"Wrote {out_path}")

        for alias_file in spec.alias_files:
            alias_path = os.path.join(DIST_DIR, alias_file)
            write_calendar_bytes(calendar_bytes, alias_path)
            log(f"Wrote {alias_path}")


def main() -> int:
    all_games: Dict[str, List[Game]] = {}
    remove_stale_outputs()

    for cfg in TOURNAMENTS:
        if cfg.category == "combined":
            continue
        games = load_games(cfg)
        if not games:
            log(f"No games for {cfg.key}, writing fallback empty calendars")
            all_games[cfg.key] = []
            write_tournament_calendars(cfg, all_games[cfg.key])
            continue
        all_games[cfg.key] = sorted(games, key=lambda game: game.start)
        write_tournament_calendars(cfg, all_games[cfg.key])

    combined_cfg = next((cfg for cfg in TOURNAMENTS if cfg.category == "combined"), None)
    if combined_cfg:
        combined_games: List[Game] = []
        for games in all_games.values():
            combined_games.extend(games)
        write_tournament_calendars(combined_cfg, sorted(combined_games, key=lambda game: game.start))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
