# Käsitsi lisatavad jaamafotod

Pane siia jaama maapealne foto nimega `<KKR-kood>.jpg`, näiteks `SJA7595000.jpg`.
Build kopeerib selle veebi kausta `veeb/photos/jaam/` ja lisab `stations.json`-i
`photos` massiivi viitega "Keskkonnaagentuur".

Generaator ei puutu seda kausta kunagi — ortofotod lähevad eraldi
kausta `veeb/photos/ortofoto/` ja ei saa siinseid pilte üle kirjutada.

TÄHELEPANU: ilmateenistuse jaamafotod EI OLE CC-BY all. Enne siia panemist
peab olema Keskkonnaagentuuri luba. Kui viide peaks olema mõni muu kui
"Keskkonnaagentuur", tuleb see `ehita_veeb.py`-s muuta.
