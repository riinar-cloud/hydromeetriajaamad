# Eesti hüdromeetriajaamade andmed

Üks leht jaama kohta: asukoht ja ortofoto, tänane vooluhulk koos ajaloolise võrdlusega,
veetase, veetemperatuur ja kogu mõõtmisperioodi aegrida CSV-na.

Riigi ilmateenistus hoiab neid andmeid kolmel eri lehel. Siin on need koos.

**Leht:** https://<kasutaja>.github.io/<repo>/

## Mis siin on

```
docs/                     avaldatav leht — GitHub Pages serveerib seda
  index.html              liides, ehitatud liides/ kaustast
  data/stations.json      kõik 57 jaama: identiteet ja operatiivne seis
  data/stations/<kood>.json   ühe jaama aegrida: ajalooline norm ja 12 kuud
  data/csv/<kood>.csv     kogu mõõtmisperiood, osal jaamadel alates 1922
  photos/ortofoto/        jaama märgiga, tehtud pildid/ortofoto/ pealt
  photos/jaam/            jaamafotod, kui neid on
  varad/                  React, kaardiplaadid, kirjatüübid — et leht ei sõltuks CDN-ist

ehita_veeb.py             ainus ehitusskript: tõmbab andmed ja kirjutab docs/ täis
liides/                   liidese lähtefailid ja JSON-leping
andmed/                   ehituse sisend ja seis (JSON)
pildid/ortofoto/          puutumata WMS-tõmmised — ÄRA joonista neile
pildid/jaam/              käsitsi lisatavad jaamafotod
```

**`liides/JSON-leping.md` on ainus tõde selle kohta, mida liides andmetest loeb.**
Build kontrollib väljundit selle 11 reegli vastu ja ütleb lõpus, kas kõik läbis.

Jaama võti on **KKR kood** (`SJA7595000`), mitte nimi — nimi ei ole allikate vahel unikaalne.

### Miks pildid on kahes kohas

`pildid/ortofoto/` on Maa-ameti WMS-ist tõmmatud originaalid. `docs/photos/ortofoto/` on
neist igal buildil uuesti tehtud koopiad, millele on joonistatud jaama asukoha märk.
Nii saab märki muuta ilma WMS-i uuesti tülitamata. Originaale ei tõmmata kunagi teist
korda — ainult siis, kui fail puudub.

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
python ehita_veeb.py                 # täisehitus, ~8 min
python ehita_veeb.py --only-now      # ainult operatiivnäidud, sekundid
python ehita_veeb.py --valjund docs  # kirjuta docs/ sisse (nii teeb CI)
```

Vaja on `pyproj` ja `pillow`. Selle repo sisu tekitab CLAUDE kaustas `avalda.py`, mis
peegeldab sinna `veeb/` väljundi — repo sees seda skripti ei ole, sest tal ei oleks
siin midagi teha.

Leht vajab HTTP-serverit, `file://` pealt ei tööta:

```
cd docs && python -m http.server 8731
```

## Piirangud

- Jaamafotosid ei ole — Keskkonnaagentuuri luba on küsimata. Ortofotod on kõigil 57 jaamal.
- Aegread on valideeritud eelmise aasta lõpuni; hilisem on operatiivne toorandmestik.
- Räpina ja Roostoja näidud on hüdroelektrijaamade mõju all. Hoiatus on lehel.
