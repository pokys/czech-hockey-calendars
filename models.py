from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class CalendarSpec:
    key: str
    name: str
    out_file: str
    alias_files: List[str] = field(default_factory=list)
    include_team_cze: bool = True
    include_playoff: bool = True
    include_all_games: bool = False


@dataclass(frozen=True)
class TournamentConfig:
    key: str
    title: str
    category: str
    wikipedia_url: Optional[str]
    calendars: List[CalendarSpec] = field(default_factory=list)


@dataclass
class Game:
    tournament_key: str
    tournament_title: str
    category: str
    start: datetime
    team1: str
    team2: str
    phase_key: str
    phase_label: str
    group_label: Optional[str]
    venue: Optional[str]
    gamecenter: Optional[str] = None
    score1: Optional[int] = None
    score2: Optional[int] = None
    status_suffix: Optional[str] = None
    playoff_index: Optional[int] = None
