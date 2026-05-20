from models import CalendarSpec, TournamentConfig


TOURNAMENTS = [
    TournamentConfig(
        key="iihf-wm-2026",
        title="IIHF Mistrovství světa v ledním hokeji 2026",
        category="men",
        wikipedia_url="https://cs.wikipedia.org/wiki/Mistrovství_světa_v_ledním_hokeji_2026",
        calendars=[
            CalendarSpec(
                key="cze",
                name="IIHF MS 2026 - Česko",
                out_file="archive/2026/iihf-wm-cze-men.ics",
                alias_files=["czech-hockey-men.ics"],
                include_team_cze=True,
                include_playoff=False,
                include_final=True,
            ),
            CalendarSpec(
                key="all",
                name="IIHF MS 2026 - Všechny zápasy",
                out_file="archive/2026/iihf-wm-all.ics",
                alias_files=["czech-hockey-all.ics"],
                include_all_games=True,
            ),
        ],
    ),
]
