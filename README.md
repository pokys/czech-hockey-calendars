# Czech Hockey Calendars

Veřejné ICS kalendáře pro MS v ledním hokeji 2026.

## Kalendáře

### Česko
Pouze zápasy české reprezentace + finále.

```
https://raw.githubusercontent.com/pokys/czech-hockey-calendars/main/dist/czech-hockey-men.ics
```

### Všechny zápasy
Kompletní program — všechny skupinové zápasy i celý play-off.

```
https://raw.githubusercontent.com/pokys/czech-hockey-calendars/main/dist/czech-hockey-all.ics
```

## Co obsahuje každá událost

**Název:** týmy, skóre a typ konce (FT / OT / SO) po odehrání zápasu

**Detail:**
- fáze (Skupina / Čtvrtfinále / …)
- skupina (Skupina A / Skupina B)
- stadion
- třetinové výsledky po odehrání
- odkaz na Wikipedia

## Zdroj dat

Wikipedia (cs.wikipedia.org) — automatická aktualizace přes GitHub Actions každou hodinu.

## Archivní soubory

- `dist/archive/2026/iihf-wm-cze-men.ics` — stejné jako `czech-hockey-men.ics`
- `dist/archive/2026/iihf-wm-all.ics` — stejné jako `czech-hockey-all.ics`

## Architektura

- `config/tournaments.py` — konfigurace turnajů a výstupních kalendářů
- `sources/wikipedia.py` — parser Wikipedie (Hokejbox2 wikitext + HTML fallback)
- `calendar_builder.py` — generování ICS
- `generate.py` — entrypoint

## Spuštění lokálně

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate.py
```
