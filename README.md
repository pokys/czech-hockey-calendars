# Czech Hockey Calendars

Veřejný ICS kalendář pro českou mužskou reprezentaci na MS v hokeji.

Hlavní odběr:
- `https://raw.githubusercontent.com/pokys/czech-hockey-calendars/main/dist/czech-hockey-men.ics`

Co v něm je:
- zápasy Česka
- po odehrání i skóre a typ konce zápasu, pokud jsou na Wikipedii

Zdroj dat:
- primárně Wikipedia
- automatická aktualizace přes GitHub Actions

## Stabilní odkazy
- `dist/czech-hockey-men.ics`
- `dist/czech-hockey-all.ics`

## Odkazy (RAW)
- `https://raw.githubusercontent.com/pokys/czech-hockey-calendars/main/dist/czech-hockey-men.ics`
- `https://raw.githubusercontent.com/pokys/czech-hockey-calendars/main/dist/czech-hockey-all.ics`

## Archivní výstupy
- `dist/archive/2026/iihf-wm-cze-men.ics`
- `dist/archive/2026/iihf-wm-cze-men-plus-playoff.ics`
- `dist/archive/2026/iihf-cze-all.ics`

## Co se generuje
- skupinové zápasy české reprezentace
- všechny play-off zápasy bez ohledu na účast Česka u kombinovaných kalendářů
- pokud jsou dvojice v play-off známé ve zdroji, zobrazí se konkrétní týmy
- po odehrání zápasu se doplní skóre a typ konce (FT/OT/SO), pokud je zdroj obsahuje

## Feedy
- `men`: zápasy českých mužů
- `all`: stejné veřejné jádro plus případné play-off

## Zdroje dat
- Wikipedia je hlavní zdroj

## Architektura
- `config/tournaments.py`: konfigurace turnajů a výstupních kalendářů
- `sources/wikipedia.py`: hlavní parser Wikipedie
- `calendar_builder.py`: společné generování ICS
- `generate.py`: hlavní entrypoint

## Spuštění lokálně
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate.py
```

## GitHub Actions
Workflow běží každé 2 hodiny a je možné jej spustit ručně přes `workflow_dispatch`. Po vygenerování automaticky commitne změny v `dist/*.ics`.
