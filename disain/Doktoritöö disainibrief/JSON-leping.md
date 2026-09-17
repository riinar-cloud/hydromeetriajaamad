# JSON-leping — Eesti hüdromeetriajaamade veebileht

Liides loeb kõik sisu JSON-failidest. Kõik siin loetletud väljad on maketis päriselt kasutusel; midagi muud liides ei loe ja midagi vähemat ei talu.

## Üldreeglid

- Kodeering UTF-8, ilma BOM-ita. (Erand: CSV-failid on BOM-iga, et Excel avaks täpitähed õigesti — vt p2 CSV.)
- **Arvud on JSON-arvud**, punktkomaga (`1.38`), mitte sõned. Koma ja ühikud lisab liides ise.
- **Kuupäevad** `YYYY-MM-DD`. Ainult `updated` on täisajatempel ISO 8601 UTC-s.
- `null` on lubatud ainult seal, kus allpool nii kirjas. Puuduv arv tuleb anda `null`-ina, mitte nullina — `0` tähendab mõõdetud nulli.
- Ühikud on fikseeritud ega tule JSON-ist: vooluhulk m³/s, veetase cm, temperatuur °C, äravoolumoodul l/s/km², valgala km².

## 1. `data/stations.json` — indeksleht, kaart ja jaama päis

Üks fail, kõik jaamad. Liides loeb selle korra ja ehitab sellest nii kaardipunktid, tabeli kui jaama lehe plokid 01 ja 02.

```json
{
  "updated": "2026-09-15T08:00:00Z",
  "count": 57,
  "validated_through": "2025-12-31",
  "stations": [
    {
      "code": "SJA7595000",
      "name": "Kaansoo",
      "river": "Saarjõgi",
      "county": "Pärnu",
      "municipality": "Põhja-Pärnumaa vald",
      "lat": 58.6239,
      "lon": 24.9761,
      "catchment_km2": 178,
      "mouth_distance_km": 1.0,
      "opened": 1979,
      "automated": 2006,
      "series_start": "01.11.1979",
      "series_days": 13541,

      "q": 1.38,
      "q_delta_24h": 0.11,
      "median_now": 0.27,
      "percentile": 83,
      "validated": false,

      "specific_runoff": 7.8,
      "median_specific_runoff": 1.5,
      "level_cm": 97,
      "median_level_cm": 74,
      "level_delta_24h": -6,
      "water_temp": 11.7,
      "median_water_temp": 12.4
    }
  ]
}
```

### Väljade tähendus

| Väli | Tüüp | Kohustuslik | Tähendus |
|---|---|---|---|
| `updated` | string | jah | Millal andmed viimati uuendati. Ülemine riba. |
| `count` | int | jah | Jaamade arv massiivis. |
| `validated_through` | date | jah | Viimane valideeritud kuupäev. Kogu lehe kontrollimata/valideeritud eristus tuleb ainult sellest ühest väljast. |
| `code` | string | jah | KKR kood. Unikaalne võti, sama mis aegrea failinimi. |
| `name` | string | jah | Jaama nimi. |
| `river` | string | jah | Jõe nimi nimetavas käändes. **Liides ei käänada** — ära anna käändevorme. Registri sünonüümsetest nimedest (`Porijõgi / Reola jõgi`) antakse ainult **esimene osa enne kaldkriipsu**. |
| `county` | string | jah | Maakond ilma sõnata "maakond". |
| `municipality` | string \| null | jah | Vald. `null`, kui pole teada. |
| `lat`, `lon` | float | jah | WGS84 kraadid. Kaardipunkti asukoht. |
| `catchment_km2` | number | jah | Valgala. Määrab ka kaardipunkti suuruse. |
| `mouth_distance_km` | float | jah | Kaugus suudmest. |
| `opened` | int | jah | Avamisaasta. |
| `automated` | int \| null | jah | Automatiseerimise aasta. |
| `series_start` | string | jah | Aegrea algus kujul `DD.MM.YYYY` — kuvatakse muutmata. |
| `series_days` | int | jah | Aegrea pikkus päevades. |

### Operatiivsed näidud

Neli paari: iga näit ja sama kalendripäeva ajalooline mediaan. Liides kuvab need ühel real, sildid "väärtus täna" ja "mediaanväärtus samal kalendripäeval".

| Väli | Tüüp | Paariline mediaan |
|---|---|---|
| `q` | float | `median_now` |
| `specific_runoff` | float | `median_specific_runoff` |
| `level_cm` | int | `median_level_cm` |
| `water_temp` | float | `median_water_temp` |

Muutus, ainult veetasemel ja vooluhulgal: `q_delta_24h` (float, m³/s) ning `level_delta_3h`, `level_delta_6h`, `level_delta_12h`, `level_delta_24h` (int, cm). Märk on oluline — liides paneb ise `+` või `−` ette.

Veetaseme neli muutust kuvatakse üksteise all lühemast pikemani (3 h, 6 h, 12 h, 24 h). Jada on üleujutusriski indikaator: kui lühem aken näitab suuremat muutust kui pikem, siis tõus kiireneb. Seetõttu on **järjekord oluline ja kõik neli peavad tulema samast tunniaegreast** — eri allikatest kokku pandud jada ei ole võrreldav.

`level_delta_3h`, `level_delta_6h` ja `level_delta_12h` on `null`, kui jaamal puudub tunniaegrida (vt osa 2a). `level_delta_24h` peaks siiski olemas olema, sest selle saab ka ööpäevasest allikast.

`percentile` (int 0–100) on tänase vooluhulga koht sama kalendripäeva ajaloolises jaotuses kogu mõõtmisperioodi ulatuses. 50 = mediaan.

`validated` (bool) peab olema `false`, kui näit on pärast `validated_through` kuupäeva.

### Tuletatud väljad

`specific_runoff` = `q / catchment_km2 * 1000`. Arvuta ise ja pane faili — liides ei arvuta.

## 2. `data/stations/<code>.json` — aegrida

Üks fail jaama kohta, failinimi = `code`. Näide: `data/stations/SJA7595000.json`. Liides laadib selle alles siis, kui jaama leht avatakse.

Fail sisaldab **ainult aegrida**. Operatiivne seis (`q`, `level_cm`, `percentile` jne), identiteet ja `photos` on `stations.json`-is ega tohi siin korduda — kaks allikat sama numbri kohta läheksid varem või hiljem lahku. Jaama leht joonistab plokid 01 ja 02 valmis enne, kui aegrida on laaditud.

```json
{
  "code": "SJA7595000",
  "validated_through": "2025-12-31",
  "daily": [
    { "d": 1, "p10": 0.06, "p25": 0.09, "med": 0.14, "p75": 0.24, "p90": 0.40 }
  ],
  "year": [
    { "date": "2025-10-01", "q": 0.42, "validated": true },
    { "date": "2026-09-15", "q": 1.38, "validated": false }
  ]
}
```

### `daily` — ajalooline norm

- Täpselt **365 kirjet**, `d` = 1…365 tõusvas järjekorras. Liigaasta 29. veebruar liidetakse 28. veebruari alla.
- `p10`, `p25`, `med`, `p75`, `p90` = selle kalendripäeva 10., 25., 50., 75. ja 90. protsentiil kogu valideeritud mõõtmisperioodist, arvutatud samast ±5-päevasest aknast.
- `p10 ≤ p25 ≤ med ≤ p75 ≤ p90` peab kehtima igal päeval.
- `p10` ja `p90` võivad puududa. Liides joonistab siis ainult kvartiilivöötme — aga kas mõlemad on olemas või kumbki, mitte üks.
- **Kõver peab olema perioodiline**: `daily[364]` ja `daily[0]` satuvad graafikul kõrvuti, nii et 31. detsembri ja 1. jaanuari vahel ei tohi olla hüpet. Kui norm arvutatakse silutult, tee silumine ringikujuline.

#### Kuupäev → `d` teisendus

Liides peab kasutama **täpselt seda** teisendust, kui paneb `year` punkti kokku vastava `daily`
kirjega. Tavaline day-of-year ei sobi: liigaastal nihkuks kõik pärast 29. veebruari ühe päeva
võrra paigast.

```js
function dayIndex(date) {                 // -> 1..365
  const d = new Date(date);
  if (d.getMonth() === 1 && d.getDate() === 29) return 59;   // 29.02 -> 28.02
  const yday = Math.floor((d - new Date(d.getFullYear(), 0, 1)) / 86400000) + 1;
  const leap = new Date(d.getFullYear(), 1, 29).getMonth() === 1;
  return (leap && yday > 60) ? yday - 1 : yday;
}
```

2026 ei ole liigaasta, seega praegu viga ei avaldu — esimest korda tuleks see välja **2028. aastal**.

Norm ise on kontrollitud: indeksil 59 on rohkem vaatlusi kui naabritel (59 vs 47), sest sinna
langevad nii 28. kui 29. veebruar, aga ±5-päevane aken koondab ~500 väärtust, nii et samm
`d=58 → d=59` on 0,0000 (tüüpiline naabersamm 0,0120). Küüru ei teki. Aastavahetuse õmblus on
igal 57 jaamal väiksem kui sama jaama suurim tavaline päevasamm.

### `year` — viimased 12 kuud

- Päevased väärtused, `date` tõusvas järjekorras, ilma lünkadeta.
- Aken on **täpselt 12 kuud tagasi tänasest**: makett kasutab 2025-10-01 … 2026-09-15, kokku 350 kirjet. Pikkus ei ole fikseeritud, aga järjestikused päevad on.
- `q` võib olla `null`, kui mõõtmine puudub — liides jätab joonesse lünga.
- `validated` = `date ≤ validated_through`.

### CSV allalaadimine

**Muudetud 16.09.2026.** CSV-nupp laeb alla **kogu aegrea**, mitte `year` massiivi. Liides ei genereeri midagi — nupp on tavaline link valmis failile:

```html
<a href="data/csv/SJA7595000.csv" download>Laadi kogu aegrida (CSV)</a>
```

Failid on `data/csv/<code>.csv`, üks jaama kohta, kogu mõõtmisperiood (osal jaamadel alates 1922).

```
kuupäev;vooluhulk_m3s;veetase_cm;veetemp_c;valideeritud
1979-11-01;0,26;42;;jah
2026-09-15;1,38;99;12,1;ei
```

- Semikoolon eraldajaks, koma komakohaks, CRLF, **UTF-8 BOM-iga** (et Excel avaks täpitähed õigesti).
- Kuupäev ISO `YYYY-MM-DD`, et sortimine töötaks ka tekstina.
- Tühi lahter = mõõtmine puudub. `0` on mõõdetud null — talvel on veetemperatuur päriselt 0.
- Päev, mil ühtegi kolmest näidust ei mõõdetud, on failist välja jäetud.
- Kokku 1 234 278 rida, 30 MB. Tasub serveril gzip sisse lülitada.

## 2a. Mõõtmise aeg

Iga näit kannab oma mõõtmisaega. Väli `measured` jaama kirjes `stations.json`-is, neli võtit — üks iga näidu kohta:

```json
"measured": {
  "q":          { "date": "2026-09-16" },
  "runoff":     { "date": "2026-09-16" },
  "level":      { "time": "2026-09-17T08:00:00Z" },
  "water_temp": { "time": "2026-09-17T08:00:00Z" }
}
```

| Võti | Vastab näidule |
|---|---|
| `q` | `q` |
| `runoff` | `specific_runoff` |
| `level` | `level_cm` |
| `water_temp` | `water_temp` |

Reeglid:

- Iga võti sisaldab **kas `date` või `time`, mitte mõlemat**. `date` = `YYYY-MM-DD`, ööpäevane keskmine. `time` = ISO 8601 UTC, hetkenäit.
- `null` on lubatud nii üksiku võtme kui terve `measured` välja kohal. Liides jätab ajatempli siis lihtsalt kuvamata — ta ei asenda seda teise näidu ajaga ega buildi ajaga.
- Sama näit võib eri jaamadel kanda eri kuju. Kui jaam ei ole operatiivkihis kaetud, tuleb veetase ööpäevasest allikast ja kannab `date`-i, mitte `time`-i. Liides talub mõlemat.
- Ajatempel on alati UTC. Teisenduse ja vormingu teeb liides: `date` → `16.09.2026`, `time` → `17.09.2026 08:00 seisuga`.

Sõnastus "seisuga" on tahtlikult neutraalne — see ei väida, kas tegu on hetkenäidu või tunni keskmisega. Kui Keskkonnaagentuur vastab, mida XML tegelikult annab, saab selle täpsustada.

`updated` juurtasemel jääb alles ja tähendab **buildi aega**: millal andmeid viimati tõmmati. See ei ole näidu mõõtmisaeg ja liides ei kasuta seda kunagi näidu juures.

## 2b. Jaamapõhised hoiatused

Väli `notes` jaama kirjes `stations.json`-is. Massiiv, sest hoiatusi võib juurde tulla.

```json
"notes": [
  {
    "type": "regulated",
    "text": "Veetaseme näidud on tugevalt mõjutatud jaama lähedal asuvate hüdroelektrijaamade tööst.",
    "source": "Keskkonnaagentuur"
  }
]
```

| Väli | Tüüp | Tähendus |
|---|---|---|
| `type` | string | Hoiatuse liik. Liides valib kuvamisviisi selle järgi, teksti sisu lugemata. Praegu ainult `regulated`. |
| `text` | string | Hoiatuse tekst. Kuvatakse muutmata. |
| `source` | string | Kes hoiatust kannab. Kuvatakse teksti järel. |

Tühi massiiv või puuduv väli tähendab, et hoiatust ei ole — nii on 55 jaamal 57-st.

Hoiatus kuvatakse operatiivsete näitude **kohal**, mitte jaluses. Põhjus: `regulated` hoiatus puudutab otseselt veetaseme vaheseeriat, mida leping kirjeldab üleujutusriski indikaatorina. Neil jaamadel tähendab kiire muutus paisu tööd, mitte hüdroloogilist sündmust — lugeja peab seda teadma enne numbrite nägemist, mitte pärast.

Allikaviide on kirje osa, mitte liidese tekst. Hoiatus on tsitaat, mitte meie väide.

## 3. Fotod

Jaama kirjes `stations.json`-is on **`photos` massiiv**. Iga pilt kannab oma autoriviidet — viide seisab pildi peal, mitte jaluses, ja tuleb andmetest, mitte kõvakodeeritult.

```json
"photos": [
  { "file": "photos/ortofoto/SJA7595000.jpg", "type": "ortofoto",  "source": "Maa- ja Ruumiamet" },
  { "file": "photos/jaam/SJA7595000.jpg",     "type": "jaamafoto", "source": "Keskkonnaagentuur" }
]
```

| Väli | Tüüp | Tähendus |
|---|---|---|
| `file` | string | Tee veebijuure suhtes. |
| `type` | string | `ortofoto` või `jaamafoto`. Kuvatakse viite alguses. |
| `source` | string | Autoriõiguse valdaja täpne nimi. Kuvatakse muutmata. |

Reeglid:

- Järjekord massiivis on kuvamisjärjekord. **Ortofoto esimesena** — see näitab jõelõiku ja valglat, mis on lehe konteksti jaoks olulisem kui mõõteseade.
- 0, 1 või 2 pilti on kõik lubatud. Tühi massiiv või puuduv väli tähendab, et liides näitab märgistatud kohatäidet.
- Kaks pilti kuvatakse üksteise all, mõlemad oma viitega. Rohkem kui kaks liides ei oota — kui neid tuleb, on see lepingumuudatus.
- Pilt ilma `source`-ita jäetakse massiivist välja. Vale autoriviide on halvem kui pildi puudumine.
- Vana üksikväli `photo` on **käibelt maas**. Liides seda ei loe.

Ortofotod ja jaamafotod on eri kaustades, sest ortofotod genereeritakse automaatselt ja jaamafotod tulevad käsitsi. Nii ei kirjuta generaator kunagi käsitsi lisatud pilti üle ja peremeeskaust ei pea segarežiimi taluma.

## 4. Mida liides ise teeb — ära dubleeri JSON-is

- Numbrite vormindus: koma, tühikud tuhandeliste vahel, `+`/`−` märgid.
- Ühikute nimed ja siltide tekstid.
- Protsentiili riba värvid ja graafiku telgede skaala.
- Graafiku y-telje jaotus arvutatakse `daily` ja `year` väärtustest.
- Kontrollimata andmete visuaalne eristus — üks `validated_through` kuupäev on kogu info, mida vaja.

## 5. Valideerimine enne üleandmist

1. `stations.json` sisaldab `count` jaama ja igal on kõik kohustuslikud väljad.
2. Iga `code` kohta on olemas `data/stations/<code>.json`.
3. Iga koordinaat jääb maismaale: `lat` 57,4…59,8 ja `lon` 21,7…28,3.
4. `daily` on 365 kirjet, `d` katkematu 1…365, perioodiline, `p10 ≤ p25 ≤ med ≤ p75 ≤ p90`.
5. `year` kuupäevad on katkematu päevade jada.
6. `validated` väärtused on kooskõlas `validated_through` kuupäevaga.
7. Iga `code` kohta on olemas `data/csv/<code>.csv`.
8. Aegrea failides ei ole ühtki operatiivset välja ega `photos`-i.
9. Iga `photos` kirje `file` on serveris olemas ja `source` on täidetud.
10. Iga `measured` võti sisaldab kas `date` või `time`, mitte mõlemat.
11. Iga `notes` kirjel on `type`, `text` ja `source`.
