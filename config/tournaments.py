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
            ),
            CalendarSpec(
                key="cze-plus-playoff",
                name="IIHF MS 2026 - Česko a play-off",
                out_file="archive/2026/iihf-wm-cze-men-plus-playoff.ics",
                include_team_cze=True,
                include_playoff=True,
            ),
        ],
    ),
    TournamentConfig(
        key="iihf-2026-czech-teams",
        title="IIHF 2026 - Česko",
        category="combined",
        wikipedia_url=None,
        calendars=[
            CalendarSpec(
                key="combined-cze-plus-playoff",
                name="IIHF 2026 - Česko a play-off",
                out_file="archive/2026/iihf-cze-all.ics",
                alias_files=["czech-hockey-all.ics"],
                include_team_cze=True,
                include_playoff=True,
            )
        ],
    ),
]
