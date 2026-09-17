# Eesti hüdromeetriajaamade andmed

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
