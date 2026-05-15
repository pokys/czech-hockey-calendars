#!/usr/bin/env python3
"""
Dynamically updates the GitHub Actions workflow schedule based on upcoming games.
Run after generate.py — reads generated .ics files and schedules a refresh
roughly 1 hour after each game ends.
"""
import os
import re
from datetime import datetime, timedelta
from typing import List

import pytz
from icalendar import Calendar

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
WORKFLOW_PATH = os.path.join(BASE_DIR, ".github/workflows/build.yml")

GAME_DURATION = timedelta(hours=2, minutes=30)
REFRESH_DELAY = timedelta(hours=1)
DAYS_AHEAD = 7
FALLBACK_CRON = "0 6 * * *"


def collect_game_starts() -> List[datetime]:
    now = datetime.now(pytz.UTC)
    cutoff = now + timedelta(days=DAYS_AHEAD)
    starts: set = set()

    for root, _, files in os.walk(DIST_DIR):
        for name in files:
            if not name.endswith(".ics"):
                continue
            path = os.path.join(root, name)
            with open(path, "rb") as f:
                cal = Calendar.from_ical(f.read())
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue
                dtstart = component.get("dtstart")
                if dtstart is None:
                    continue
                dt = dtstart.dt
                if not isinstance(dt, datetime):
                    continue
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                else:
                    dt = dt.astimezone(pytz.UTC)
                if now <= dt <= cutoff:
                    starts.add(dt)

    return sorted(starts)


def to_cron(refresh_time: datetime) -> str:
    utc = refresh_time.astimezone(pytz.UTC)
    minute = (utc.minute // 5) * 5
    return f"{minute} {utc.hour} {utc.day} {utc.month} *"


def build_crons(game_starts: List[datetime]) -> List[str]:
    seen: set = set()
    crons = []
    for start in game_starts:
        cron = to_cron(start + GAME_DURATION + REFRESH_DELAY)
        if cron not in seen:
            seen.add(cron)
            crons.append(cron)
    return crons


def update_workflow(crons: List[str]) -> bool:
    with open(WORKFLOW_PATH) as f:
        content = f.read()

    lines = [f"    - cron: '{FALLBACK_CRON}'  # fallback daily refresh"]
    for cron in crons:
        lines.append(f"    - cron: '{cron}'")
    new_schedule = "  schedule:\n" + "\n".join(lines) + "\n"

    new_content = re.sub(
        r"  schedule:\n(?:    - cron: '[^'\n]+'[^\n]*\n)+",
        new_schedule,
        content,
    )
    if new_content == content:
        return False

    with open(WORKFLOW_PATH, "w") as f:
        f.write(new_content)
    return True


def main() -> None:
    game_starts = collect_game_starts()
    crons = build_crons(game_starts)

    print(f"Upcoming games in next {DAYS_AHEAD} days: {len(game_starts)}, cron entries: {len(crons)}")
    for cron in crons:
        print(f"  {cron}")

    if update_workflow(crons):
        print("Workflow schedule updated")
    else:
        print("No schedule changes")


if __name__ == "__main__":
    main()
