# -*- coding: utf-8 -*-
"""
Valmistab avaldamise repo kausta CLAUDE/avaldus.

Miks eraldi kaust: CLAUDE kaust on 32 GB doktoritöö materjali. Repo peab sisaldama
ainult seda, mis läheb avalikuks — leht ise ja see, mida build vajab, et lehte
GitHubi peal iga tund uuendada.

Miks docs/: GitHub Pages oskab haru pealt serveerida ainult juurt või /docs. Juur oleks
ehitusfailidega segamini, seega docs.

Käivitamine:
    python ehita_veeb.py            # ehitab veeb/ valmis
    python avalda.py                # peegeldab selle avaldus/ repo kausta

Repo esimene kord üles:
    cd avaldus
    git init && git add -A && git commit -m "Esimene versioon"
    git remote add origin <sinu repo URL>
    git push -u origin main
Seejärel GitHubis: Settings -> Pages -> Deploy from a branch -> main -> /docs
"""
import os, shutil, sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "avaldus")
VEEB = os.path.join(BASE, "veeb")
DISAIN_ALAM = os.path.join("disain", "Doktoritöö disainibrief")

# Ainult need failid disaini ekspordist. Ülejäänu (uploads/, näidisandmed) on 5 MB,
# mida build ei vaja ja mis avalikus repos ainult segaks.
DISAIN_FAILID = (".dc.html", "support.js", "JSON-leping.md")

ANDMED = ("ids.json", "metaandmed.json", "tunnilogi.json")

GITIGNORE = """__pycache__/
*.pyc
.DS_Store
Thumbs.db
"""

# Git normaliseerib vaikimisi realõpud. CSV puhul on see viga: leping nõuab CRLF-i ja
# UTF-8 BOM-i, et Excel avaks failid õigesti. Kontrollitud — ilma selleta salvestas git
# CSV-d LF-iga ja Linuxi CI oleks need nii ka välja serveerinud.
# Järjekord loeb: git võtab iga atribuudi jaoks VIIMASE sobiva rea.
GITATTRIBUTES = """* text=auto eol=lf
*.csv -text
*.jpg -text
*.png -text
*.woff2 -text
"""

TOOVOOG = """name: Uuenda andmeid

on:
  schedule:
    # Operatiivnäidud iga tund. GitHubi cron hilineb koormuse all, vt README.
    - cron: "15 * * * *"
    # Täisehitus kord ööpäevas, kui EstModeli eelmine päev on kindlalt kohal.
    - cron: "40 5 * * *"
  workflow_dispatch:
    inputs:
      taisehitus:
        description: "Tee täisehitus (aegread ja CSV-d uuesti)"
        type: boolean
        default: false

permissions:
  contents: write

concurrency:
  group: uuendus
  cancel-in-progress: false

jobs:
  uuenda:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Paigalda sõltuvused
        run: pip install pyproj

      - name: Vali režiim
        id: reziim
        run: |
          if [ "${{ github.event.schedule }}" = "40 5 * * *" ] || \\
             [ "${{ inputs.taisehitus }}" = "true" ]; then
            echo "lipud=--valjund docs" >> "$GITHUB_OUTPUT"
          else
            echo "lipud=--only-now --valjund docs" >> "$GITHUB_OUTPUT"
          fi

      - name: Ehita
        run: python ehita_veeb.py ${{ steps.reziim.outputs.lipud }}

      - name: Commit
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A docs andmed
          if git diff --staged --quiet; then
            echo "muutusi ei ole"
          else
            git commit -m "Andmed $(date -u '+%Y-%m-%d %H:%M UTC')"
            git push
          fi
"""


LUGEMINE = """# Eesti hüdromeetriajaamade andmed

Üks leht jaama kohta: asukoht ja ortofoto, tänane vooluhulk koos ajaloolise võrdlusega,
veetase, veetemperatuur ja kogu mõõtmisperioodi aegrida CSV-na.

Riigi ilmateenistus hoiab neid andmeid kolmel eri lehel. Siin on need koos.

**Leht:** https://<kasutaja>.github.io/<repo>/

## Mis siin on

| | |
|---|---|
| `docs/` | Avaldatav leht. GitHub Pages serveerib seda. |
| `docs/data/stations.json` | Kõik 57 jaama, operatiivne seis ja identiteet. |
| `docs/data/stations/<kood>.json` | Ühe jaama aegrida: ajalooline norm ja viimased 12 kuud. |
| `docs/data/csv/<kood>.csv` | Kogu mõõtmisperiood, osal jaamadel alates 1922. |
| `ehita_veeb.py` | Ainus ehitusskript. Tõmbab andmed ja kirjutab `docs/` täis. |
| `disain/.../JSON-leping.md` | Andmeleping. Ainus tõde selle kohta, mida liides loeb. |

Jaama võti on **KKR kood** (`SJA7595000`), mitte nimi — nimi ei ole allikate vahel unikaalne.

## Andmeallikad

| Allikas | Mida annab | Värskus |
|---|---|---|
| [EstModel](https://estmodel.envir.ee) | ööpäevane vooluhulk, veetase, veetemperatuur | eelmine päev |
| [keskkonnaandmed.envir.ee](https://keskkonnaandmed.envir.ee) | tunniandmed | ööpäevase partiina |
| [ilmateenistus.ee XML](https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php) | veetase ja -temperatuur praegu | ~tunnis |
| [Maa- ja Ruumiamet WMS](https://kaart.maaamet.ee) | ortofotod | üks kord, vahemällu |

Andmed on Keskkonnaagentuuri omad, litsents CC-BY 4.0. Ortofotod Maa- ja Ruumiameti omad.
Kaardialus © OpenStreetMap contributors.

## Uuendamine

`.github/workflows/uuenda.yml` jookseb iga tunni :15 ja uuendab operatiivnäidud; kord
ööpäevas kell 05:40 UTC teeb täisehituse koos aegridade ja CSV-dega.

Kaks asja, mida teada:

- **`andmed/tunnilogi.json` peab repos olema.** `level_delta_3h/6h/12h` jaoks ei ole
  allikat — build peab ise tunniajalugu pidama. Kui logi kaob, on need väljad `null`
  kuni 12 tundi.
- **GitHubi cron hilineb** koormuse all 5–20 minutit. Veetaseme mõõtmisaeg tuletatakse
  eeldusest, et build jookseb täistunni järel — suure hilinemise korral võib tunnitempel
  nihkuda. Mõõdetud väärtused ise on õiged.

Käsitsi: Actions -> Uuenda andmeid -> Run workflow.

## Kohapeal

```
python ehita_veeb.py              # täisehitus kausta veeb/
python ehita_veeb.py --only-now   # ainult operatiivnäidud
python avalda.py                  # peegeldab veeb/ -> avaldus/docs/
```

Leht vajab HTTP-serverit, `file://` pealt ei tööta:

```
cd docs && python -m http.server 8731
```

## Piirangud

- Jaamafotosid ei ole — Keskkonnaagentuuri luba on küsimata. Ortofotod on kõigil 57 jaamal.
- Aegread on valideeritud eelmise aasta lõpuni; hilisem on operatiivne toorandmestik.
- Räpina ja Roostoja näidud on hüdroelektrijaamade mõju all. Hoiatus on lehel.
"""


def kopeeri_fail(lahte, siht):
    os.makedirs(os.path.dirname(siht), exist_ok=True)
    shutil.copy2(lahte, siht)


def peegelda(lahte, siht):
    """Kopeerib kausta ja kustutab sihist failid, mida lähtes enam ei ole."""
    uusi = muutunud = kustutatud = 0
    for kaust, _, failid in os.walk(lahte):
        suht = os.path.relpath(kaust, lahte)
        os.makedirs(os.path.join(siht, suht), exist_ok=True)
        for f in failid:
            a, b = os.path.join(kaust, f), os.path.join(siht, suht, f)
            if not os.path.exists(b):
                shutil.copy2(a, b); uusi += 1
            elif os.path.getmtime(a) > os.path.getmtime(b) + 1 or \
                    os.path.getsize(a) != os.path.getsize(b):
                shutil.copy2(a, b); muutunud += 1
    for kaust, _, failid in os.walk(siht):
        suht = os.path.relpath(kaust, siht)
        for f in failid:
            if not os.path.exists(os.path.join(lahte, suht, f)):
                os.remove(os.path.join(kaust, f)); kustutatud += 1
    return uusi, muutunud, kustutatud


def main():
    if not os.path.isdir(VEEB):
        sys.exit(f"veeb/ puudub — jooksuta enne: python ehita_veeb.py")

    os.makedirs(REPO, exist_ok=True)

    # 1. leht -> docs/
    docs = os.path.join(REPO, "docs")
    u, m, k = peegelda(VEEB, docs)
    print(f"docs/         uusi {u}, muutunud {m}, kustutatud {k}")
    # Ilma selleta jätab Jekyll alakriipsuga kaustad vahele ja töötleb faile asjatult.
    open(os.path.join(docs, ".nojekyll"), "w").close()

    # 2. ehitusskript
    for f in ("ehita_veeb.py", "avalda.py"):
        kopeeri_fail(os.path.join(BASE, f), os.path.join(REPO, f))

    # 3. andmed, mida build vajab. tunnilogi.json PEAB kaasas käima, muidu
    #    lähevad level_delta_3h/6h/12h iga CI käivitusega nulli.
    for f in ANDMED:
        lahte = os.path.join(BASE, "andmed", f)
        if os.path.exists(lahte):
            kopeeri_fail(lahte, os.path.join(REPO, "andmed", f))
        else:
            print(f"  hoiatus: andmed/{f} puudub")

    # 4. disaini eksport — ainult liidese failid
    lahte_d = os.path.join(BASE, DISAIN_ALAM)
    n = 0
    for f in os.listdir(lahte_d):
        if f.endswith(DISAIN_FAILID):
            kopeeri_fail(os.path.join(lahte_d, f), os.path.join(REPO, DISAIN_ALAM, f))
            n += 1
    print(f"disain/       {n} faili")

    # 5. käsitsi lisatavate jaamafotode kaust peab repos olema, ka tühjana
    fotod = os.path.join(REPO, "fotod")
    os.makedirs(fotod, exist_ok=True)
    open(os.path.join(fotod, ".gitkeep"), "w").close()

    # 6. repo enda failid
    with open(os.path.join(REPO, ".gitignore"), "w", encoding="utf-8", newline="\n") as f:
        f.write(GITIGNORE)
    with open(os.path.join(REPO, ".gitattributes"), "w", encoding="utf-8", newline="\n") as f:
        f.write(GITATTRIBUTES)
    tv = os.path.join(REPO, ".github", "workflows")
    os.makedirs(tv, exist_ok=True)
    with open(os.path.join(tv, "uuenda.yml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(TOOVOOG)
    # README kirjutatakse ainult üks kord — pärast on see sinu oma, mitte skripti oma.
    lugemine = os.path.join(REPO, "README.md")
    if not os.path.exists(lugemine):
        with open(lugemine, "w", encoding="utf-8", newline="\n") as f:
            f.write(LUGEMINE)

    kokku = sum(os.path.getsize(os.path.join(d, f))
                for d, _, fs in os.walk(REPO) if ".git" not in d for f in fs)
    arv = sum(len(fs) for d, _, fs in os.walk(REPO) if ".git" not in d)
    print(f"\nvalmis: {REPO}\n        {arv} faili, {kokku / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
