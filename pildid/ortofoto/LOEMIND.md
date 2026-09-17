# Puutumata ortofotod

Siin on Maa- ja Ruumiameti WMS-ist tõmmatud pildid **täpselt nii, nagu need tulid** —
ilma jaama märgita, 640×400, nimega `<KKR-kood>.jpg`.

Väljundis olevad pildid (`veeb/photos/ortofoto/`) tehakse **igal buildil neist uuesti**,
lisades punase rõnga pildi keskele. Seetõttu saab märgi suurust või värvi muuta ilma
WMS-i uuesti tülitamata — muuda `MARK_M` või `margi_jaam()` ja jooksuta build.

**Ära joonista siia midagi peale.** Kui need originaalid ära rikkuda, on ainus tee
tagasi uus tõmme Maa-ameti serverist.

Kaadri laius sõltub valgalast (`ORTO_SAMM`): 220 m väikestel jõgedel kuni 800 m Narva
jõel. Põhjus on see, et jõe laius kasvab valgalaga — ühtne kaader jätaks kas suured jõed
kaadrist välja või väikesed ojad nähtamatuks.

Pilt tõmmatakse ainult siis, kui faili veel ei ole. Kustuta fail, kui tahad uut.
