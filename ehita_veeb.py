# -*- coding: utf-8 -*-
"""
Ehitab andmed vastavalt disainipoole JSON-lepingule.
Leping: liides/JSON-leping.md (avaldamise repos) või
        disain/Doktoritöö disainibrief/JSON-leping.md (kohapeal, Claude Designi eksport).

Sisend:
  liides/                     liidese failid ja leping
  pildid/ortofoto/<code>.jpg  puutumata WMS-tõmmised
  pildid/jaam/<code>.jpg      käsitsi lisatud jaamafotod
  andmed/                     ids, kraabitud metaandmed, tunnilogi

Väljund (vaikimisi veeb/, CI-s docs/):
  data/stations.json          indeks + operatiivnäidud + jaama päis
  data/stations/<code>.json   daily norm + viimased 12 kuud
  data/csv/<code>.csv         kogu mõõtmisperiood
  photos/ortofoto/<code>.jpg  ortofoto jaama märgiga
  photos/jaam/<code>.jpg      jaamafoto, kui on
  varad/                      React, kaardiplaadid, kirjatüübid kohalikuna

Operatiivnäidud (level_cm, water_temp, level_delta_24h) tulevad XML-ist.
Kui XML jaama ei kajasta, kukume tagasi EstModeli ööpäevase väärtuse peale (D-1),
et ükski kohustuslik väli ei jääks tühjaks.

Kasutus:
  python ehita_veeb.py                 kõik
  python ehita_veeb.py --only-now      ainult operatiivväljad stations.json-is
  python ehita_veeb.py --valjund docs  kirjuta mujale kui veeb/
"""
import json, os, re, sys, time, datetime, statistics, urllib.request
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
# Väljundkaust. Kohapeal "veeb", avaldamise repos "docs" (--valjund docs), sest
# GitHub Pages oskab haru pealt serveerida ainult juurt või /docs.
OUT = os.path.join(BASE, sys.argv[sys.argv.index("--valjund") + 1]
                   if "--valjund" in sys.argv else "veeb")
# Pildid, millest väljund tehakse. Kaks kausta, sest neid hallatakse eri moodi:
#   pildid/ortofoto/  genereeritud WMS-ist, puutumata originaalid (vahemälu)
#   pildid/jaam/      KÄSITSI lisatud jaamafotod — generaator ei puutu neid kunagi
# Sama jaotus nagu väljundis, et kaks allikat ei saaks kunagi segamini minna.
PILDID = os.path.join(BASE, "pildid")
FOTOD_KASITSI = os.path.join(PILDID, "jaam")
# Liidese failid; .dc.html saab väljundis nimeks index.html. Disain hoiab faili kirjeldava
# nimega meelega — ümbernimetamine on ehitusskripti töö.
# Kaks kohta: kohapeal on ainus tõde Claude Designi eksport (mis kirjutatakse iga korraga
# üle), avaldamise repos on sellest tehtud koopia kaustas liides/.
DISAIN = next((k for k in (os.path.join(BASE, "liides"),
                           os.path.join(BASE, "disain", "Doktoritöö disainibrief"))
               if os.path.isdir(k)), os.path.join(BASE, "liides"))
# Tunnilogi: build peab ISE tunniajalugu pidama, sest level_delta_3h/6h/12h jaoks
# ei ole allikat. XML annab ainult praeguse hetke, f_hydroseire on ~12 h vanas.
# Leping nõuab, et kõik neli vahet tuleksid SAMAST aegreast -> ainus tee on oma logi.
TUNNILOGI = os.path.join(BASE, "andmed", "tunnilogi.json")
# Välised varad tõmmatakse siia ja liidese viited kirjutatakse kohalikeks. Põhjus:
# avalik leht ei tohi sõltuda CDN-ist (unpkg maas = leht surnud), OSM-i plaadiserverist
# (nende kasutustingimused ei taha avalikke lehti otse küljes) ega Google Fontsist
# (iga külastaja IP läheks Google'ile). Kaust on vahemälu — kustuta, kui tahad uuesti.
VARAD = os.path.join(OUT, "varad")
LOGI_TUNDE = 30          # hoia veidi rohkem kui 24 h
DELTA_AKNAD = (3, 6, 12, 24)
EST = "https://estmodel.envir.ee"
KKA = "https://keskkonnaandmed.envir.ee"
XMLURL = "https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php"
UA = {"User-Agent": "Mozilla/5.0 (hydro-site build)"}
AKEN = 5

ONLY_NOW = "--only-now" in sys.argv

# jaama nimi -> nimi XML-is, kui lahknevad
XML_NIMI = {"Kehra (Hüdro)": "Kehra", "Uue-Lõve (Hüdro)": "Uue-Lõve",
            "Narva karjääri": "Narva Karjääri", "Tulijärve": "Tulijarve-WL"}
# XML-is puuduvad või mitmeti tõlgendatavad (Linnusaarel kaks kandidaati)
KAARDISTAMATA = {"Linnusaare", "Põhjaka I", "Põhjaka II", "Särevere"}

# Hoiatused jaamade kohta, mille näite mõjutab hüdroelektrijaama töö.
# Esimene on TSITAAT ilmateenistuse operatiivlehelt; teine on meie oma mõõtmine
# (Võhandu jõgi: Kirumpää ülalpool looduslik vs Räpina allpool, tunnisisene
# kõikumine 22x suurem). Neid ei tohi kokku sulatada — allikad on eri.
NOTES = {
    "SJA4456000": [  # Räpina, Võhandu jõgi
        {"type": "regulated",
         "text": "Veetaseme näidud on tugevalt mõjutatud jaama lähedal asuvate "
                 "hüdroelektrijaamade tööst.",
         "source": "Keskkonnaagentuur"},
        {"type": "regulated",
         "text": "Hüdroelektrijaama töö mõjutab ka vooluhulka: tunnisisene kõikumine on "
                 "ligi 20 korda suurem kui samal jõel ülalpool asuvas Kirumpää jaamas.",
         "source": "Eesti hüdromeetriajaamad"},
    ],
    "SJA2558000": [  # Roostoja, Rannapungerja jõgi
        {"type": "regulated",
         "text": "Veetaseme näidud on tugevalt mõjutatud jaama lähedal asuvate "
                 "hüdroelektrijaamade tööst.",
         "source": "Keskkonnaagentuur"},
    ],
}


def get(url, timeout=60, binary=False, katseid=3):
    for k in range(katseid):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
            return data if binary else json.loads(data.decode("utf-8"))
        except Exception:
            if k == katseid - 1:
                raise
            time.sleep(1.5 * (k + 1))


def r3(v):
    return None if v is None else round(v, 3)


def dix365(d):
    """Kalendripäev 1..365. Liigaasta 29. veebruar liidetakse 28. veebruari alla."""
    if d.month == 2 and d.day == 29:
        return 59
    leap = (d.year % 4 == 0 and d.year % 100 != 0) or d.year % 400 == 0
    y = d.timetuple().tm_yday
    return y - 1 if (leap and y > 60) else y


_TRAFO = None


def lest_wgs84(x, y):
    global _TRAFO
    if x is None or y is None:
        return None, None
    try:
        if _TRAFO is None:
            from pyproj import Transformer
            _TRAFO = Transformer.from_crs("EPSG:3301", "EPSG:4326", always_xy=True)
        lon, lat = _TRAFO.transform(x, y)
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None


# Ortofoto poollaius meetrites valgala järgi. TAASTATUD tabel: funktsioon ise oli koodist
# kadunud ja ainsaks jäljeks jäid valmis pildid. Mõõtsin väärtused nende pealt tagasi —
# Kaansoo (178 km²) 110 m, Särevere (572) 160 m, Räpina (1132) 240 m langevad WMS-i
# vastusega piksli täpsusega kokku, Narva linn (56 047) 400 m peaaegu. Seetõttu on see
# tabel, mitte valem: valemit, mis neid nelja punkti seletaks, ei ole.
# Uued pildid ei tule vanadega baidi täpsusega samad — aluskaart on vahepeal uuenenud.
ORTO_SAMM = ((400, 110), (900, 160), (5000, 240))
ORTO_URL = "https://kaart.maaamet.ee/wms/fotokaart"
# Puutumata WMS-tõmmised. Väljundis olevad on NEIST tuletatud, jaama märgiga.
ORTO_ALGNE = os.path.join(PILDID, "ortofoto")
# Jaama märgi läbimõõt MAAPINNAL, mitte pikslites: registrikoordinaadi ebakindlus on
# meetrites, seega peab märk katma igal jaamal sama maalapi, olenemata kaadri laiusest.
MARK_M = 24.0


def ortofoto_r(km2):
    """Kaadri poollaius meetrites. Vt ORTO_SAMM kommentaari."""
    for piir, laius in ORTO_SAMM:
        if (km2 or 0) < piir:
            return float(laius)
    return 400.0


def margi_jaam(algne, sihtfail, r_meetrit):
    """Rõngas pildi keskele — jaam ongi kaadri keskpunkt, arvutada ei ole midagi.

    Rõngas, mitte täpp: registrikoordinaat on jaama registreeritud punkt ja kui täpselt
    see päris mõõtekohaga kattub, ei ole teada. Avatud keskkoht ei kata seda, mida
    vaadata tahad, ega väida täpsust, mida meil ei ole.
    """
    from PIL import Image, ImageDraw
    pilt = Image.open(algne).convert("RGBA")
    w, h = pilt.size
    rp = MARK_M / (2 * r_meetrit / w) / 2         # raadius pikslites
    # Joonistan 4x suurendusega läbipaistvale kihile ja vähendan tagasi: PIL-i ellips ei
    # ole pehmendatud ja 19 px rõngas tuleks muidu kandiline.
    S = 4
    kiht = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    joonis = ImageDraw.Draw(kiht)
    cx, cy = w * S / 2, h * S / 2
    punane = max(2.0, rp / 8)                     # joone jämedus käib ringi suurusega kaasa
    aar = max(1.0, rp / 20)
    # Tume äär mõlemal pool punast: punane üksi kaob heleda katuse või liivase kalda peal.
    for raadius, varv, jamedus in (
            (rp + (punane + aar) / 2, (20, 16, 14, 235), aar),
            (rp, (208, 42, 32, 255), punane),
            (rp - (punane + aar) / 2, (20, 16, 14, 235), aar)):
        joonis.ellipse([(cx - raadius * S), (cy - raadius * S),
                        (cx + raadius * S), (cy + raadius * S)],
                       outline=varv, width=max(1, round(jamedus * S)))
    kiht = kiht.resize((w, h), Image.LANCZOS)
    pilt = Image.alpha_composite(pilt, kiht).convert("RGB")
    os.makedirs(os.path.dirname(sihtfail), exist_ok=True)
    pilt.save(sihtfail, "JPEG", quality=88, optimize=True)


def ortofoto(x, y, km2, sihtfail):
    """Maa- ja Ruumiameti ortofoto jaama ümbrusest, 640x400. x, y on L-EST97 meetrites."""
    r = ortofoto_r(km2)
    hh = r * 400 / 640
    url = (f"{ORTO_URL}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=EESTIFOTO&STYLES="
           f"&SRS=EPSG:3301&BBOX={x - r},{y - hh},{x + r},{y + hh}"
           f"&WIDTH=640&HEIGHT=400&FORMAT=image/jpeg")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as vastus:
        pilt = vastus.read()
    if not pilt.startswith(b"\xff\xd8"):
        raise RuntimeError("WMS ei andnud JPEG-i")
    os.makedirs(os.path.dirname(sihtfail), exist_ok=True)
    with open(sihtfail, "wb") as f:
        f.write(pilt)


def vali_kood(toores, hs):
    if not toores:
        return None
    kand = [k.strip() for k in str(toores).split(";") if k.strip().isdigit()]
    if not kand:
        return None
    for k in kand:
        if int(k) in hs:
            return int(k)
    return int(kand[0])


SKAALA = {"Q": 1.0, "H": 100.0, "T": 1.0}  # H meetrid -> cm


def aegrida(kkr, par):
    rows = get(f"{EST}/stations/{kkr}/measurements?parameter={par}&start-year=1922&end-year=2026")
    if not rows:
        return None
    k = SKAALA[par]
    pts = sorted((datetime.date.fromisoformat(r["startDate"]), r["value"] * k,
                  r.get("qualityFlag")) for r in rows)
    d0, d1 = pts[0][0], pts[-1][0]
    v = [None] * ((d1 - d0).days + 1)
    esimene_kontrollimata = None
    for d, val, flag in pts:
        v[(d - d0).days] = r3(val)
        if flag == "UNCHECKED" and esimene_kontrollimata is None:
            esimene_kontrollimata = d
    return {"start": d0, "end": d1, "v": v, "first_unchecked": esimene_kontrollimata}


def paarid(ts):
    return [(ts["start"] + datetime.timedelta(days=i), x) for i, x in enumerate(ts["v"]) if x is not None]


def aknad(pp, valid_through):
    """Kalendripäev -> valideeritud ajaloolised väärtused (ilma jooksva aastata)."""
    kogum = {}
    for d, x in pp:
        if d.isoformat() > valid_through:
            continue
        kogum.setdefault(dix365(d), []).append(x)
    return kogum


def aken_vaartused(kogum, d):
    w = []
    for off in range(-AKEN, AKEN + 1):
        w.extend(kogum.get((d - 1 + off) % 365 + 1, []))
    return w


def daily_norm(kogum):
    """365 kirjet, ringikujuline aken -> 31.12 ja 01.01 vahel hüpet ei teki."""
    out = []
    for d in range(1, 366):
        w = sorted(aken_vaartused(kogum, d))
        if len(w) < 10:
            return None
        q = lambda p: w[min(len(w) - 1, int(p / 100 * len(w)))]
        p10, p25, med, p75, p90 = r3(q(10)), r3(q(25)), r3(statistics.median(w)), r3(q(75)), r3(q(90))
        # leping: p10 <= p25 <= med <= p75 <= p90 peab kehtima igal päeval
        p25, p75 = min(p25, med), max(p75, med)
        p10, p90 = min(p10, p25), max(p90, p75)
        out.append({"d": d, "p10": p10, "p25": p25, "med": med, "p75": p75, "p90": p90})
    return out


def mediaan_paeval(kogum, d):
    w = aken_vaartused(kogum, d)
    return r3(statistics.median(w)) if len(w) >= 10 else None


# ----------------------------------------------------------------- CSV
CSV_PAIS = ["kuupäev", "vooluhulk_m3s", "veetase_cm", "veetemp_c", "valideeritud"]


def koma(v, kohti=3):
    """JSON-arv -> eesti komakohaga sõne. None -> tühi lahter."""
    if v is None:
        return ""
    t = f"{v:.{kohti}f}".rstrip("0").rstrip(".")
    return (t or "0").replace(".", ",")


def kirjuta_csv(kkr, Q, ts, vt, sihtkaust):
    """Kogu aegrida ühte CSV-sse. Q on baasrida; H ja T joondatakse selle järgi."""
    import csv
    n = len(Q["v"])
    def joonda(par):
        t = ts.get(par)
        if not t:
            return [None] * n
        nihe = (t["start"] - Q["start"]).days
        arr = [None] * n
        for k, x in enumerate(t["v"]):
            p = nihe + k
            if 0 <= p < n:
                arr[p] = x
        return arr
    h, t_ = joonda("H"), joonda("T")
    ridu = 0
    with open(os.path.join(sihtkaust, f"{kkr}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(CSV_PAIS)
        for k in range(n):
            if Q["v"][k] is None and h[k] is None and t_[k] is None:
                continue
            kp = (Q["start"] + datetime.timedelta(days=k)).isoformat()
            w.writerow([kp, koma(Q["v"][k]), koma(h[k], 1), koma(t_[k], 1),
                        "jah" if kp <= vt else "ei"])
            ridu += 1
    return ridu


# ----------------------------------------------------------------- tunnilogi
def tund(t):
    """Ajatempel -> täistunni võti. Build käib :15, näit on :00 mõõtmine."""
    return t.replace(minute=0, second=0, microsecond=0).isoformat(timespec="seconds").replace("+00:00", "Z")


def lae_logi():
    if not os.path.exists(TUNNILOGI):
        return {}
    try:
        return json.load(open(TUNNILOGI, encoding="utf-8")).get("jaamad", {})
    except Exception:
        return {}


def salvesta_logi(logi, nyyd):
    piir = tund(nyyd - datetime.timedelta(hours=LOGI_TUNDE))
    kärbitud = {c: {k: v for k, v in h.items() if k >= piir} for c, h in logi.items()}
    kärbitud = {c: h for c, h in kärbitud.items() if h}
    json.dump({"uuendatud": nyyd.isoformat(timespec="seconds").replace("+00:00", "Z"),
               "tunde": LOGI_TUNDE, "jaamad": kärbitud},
              open(TUNNILOGI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return kärbitud


def vahed_logist(logi_jaam, praegune, nyyd):
    """level_delta_3h/6h/12h/24h ühest ja samast tunnireast."""
    out = {}
    for h in DELTA_AKNAD:
        k = tund(nyyd - datetime.timedelta(hours=h))
        vana = logi_jaam.get(k)
        out[f"level_delta_{h}h"] = round(praegune - vana) if vana is not None else None
    return out


# ----------------------------------------------------------------- operatiiv
def operatiiv(jaamad):
    """XML -> {code: {level_cm, water_temp, level_delta_24h}}"""
    root = ET.fromstring(get(XMLURL, binary=True))
    vaadeldud = datetime.datetime.fromtimestamp(int(root.get("timestamp")), datetime.timezone.utc)
    nimi2 = {XML_NIMI.get(j["name"], j["name"]): (j["code"], j["_id"])
             for j in jaamad if j["name"] not in KAARDISTAMATA and j.get("_id")}
    arv = lambda s: (lambda t: float(t) if t else None)((s or "").strip())

    praegu, koodid = {}, {}
    for s in root.findall("station"):
        n = (s.findtext("name") or "").strip()
        if n not in nimi2:
            continue
        code, sid = nimi2[n]
        wl, wt = arv(s.findtext("waterlevel")), arv(s.findtext("watertemperature"))
        k = {}
        if wl is not None:
            k["level_cm"] = round(wl); koodid[sid] = code
        if wt is not None:
            k["water_temp"] = round(wt, 1)
        if k:
            praegu[code] = k

    # --- tunnilogi: salvesta selle tunni näit ja arvuta vahed OMA logist ---
    # Leping p1: kõik neli vahet peavad tulema samast tunniaegreast. Segu XML-ist ja
    # f_hydroseirest (WL avg = tunni KESKMINE) ei oleks võrreldav, seega logi on ainus tee.
    logi = lae_logi()
    t_nyyd = tund(vaadeldud)
    for code, k in praegu.items():
        if "level_cm" in k:
            logi.setdefault(code, {})[t_nyyd] = k["level_cm"]
    logi = salvesta_logi(logi, vaadeldud)

    for code, k in praegu.items():
        if "level_cm" not in k:
            continue
        k.update(vahed_logist(logi.get(code, {}), k["level_cm"], vaadeldud))

    # level_delta_24h tagavara ööpäevasest allikast, kui logis pole veel 24 h ajalugu.
    # Leping lubab seda: "level_delta_24h peaks siiski olemas olema, sest selle saab ka
    # ööpäevasest allikast." Lühemaid aknaid EI tohi nii täita — need jäävad null-iks.
    puudu = [sid for sid, code in koodid.items()
             if praegu.get(code, {}).get("level_delta_24h") is None]
    if puudu:
        siht = vaadeldud - datetime.timedelta(hours=24)
        a = (siht - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
        b = (siht + datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
        parim = {}
        for r in get(f"{KKA}/f_hydroseire?jaam_kood=in.({','.join(map(str, puudu))})"
                     f"&aegrida_nimi=eq.WL%20avg&timeline_ts_utc=gte.{a}&timeline_ts_utc=lte.{b}"
                     f"&select=jaam_kood,timeline_ts_utc,vaartus&limit=20000", timeout=90):
            t = datetime.datetime.fromisoformat(r["timeline_ts_utc"]).replace(tzinfo=datetime.timezone.utc)
            vahe = abs((t - siht).total_seconds())
            if r["jaam_kood"] not in parim or vahe < parim[r["jaam_kood"]][0]:
                parim[r["jaam_kood"]] = (vahe, r["vaartus"])
        for sid in puudu:
            code = koodid[sid]
            if sid in parim and "level_cm" in praegu.get(code, {}):
                praegu[code]["level_delta_24h"] = round(praegu[code]["level_cm"] - parim[sid][1])

    for code, k in praegu.items():
        k["_tund"] = t_nyyd          # sisemine: measured.level / measured.water_temp jaoks
    return praegu, vaadeldud


# ----------------------------------------------------------------- liides
def kopeeri_liides():
    """Disaini eksport -> veeb/. Sisenemisfail saab nimeks index.html."""
    import glob, shutil
    if not os.path.isdir(DISAIN):
        return [f"disaini kausta ei leitud: {DISAIN}"]
    hoiatused = []
    tugi = os.path.join(DISAIN, "support.js")
    if os.path.exists(tugi):
        shutil.copy2(tugi, os.path.join(OUT, "support.js"))
    else:
        hoiatused.append("support.js puudub disaini ekspordist")
    lehed = sorted(glob.glob(os.path.join(DISAIN, "*.dc.html")))
    if not lehed:
        return hoiatused + ["disaini ekspordist ei leitud ühtki .dc.html faili"]
    shutil.copy2(lehed[0], os.path.join(OUT, "index.html"))
    print(f"     {os.path.basename(lehed[0])} -> index.html", flush=True)
    for muu in lehed[1:]:
        nimi = os.path.basename(muu).replace(".dc.html", ".html")
        shutil.copy2(muu, os.path.join(OUT, nimi))
        print(f"     {os.path.basename(muu)} -> {nimi}", flush=True)
    # Kohe siinsamas, mitte eraldi kutsena: kopeerimine toob CDN-viited iga kord tagasi.
    return hoiatused + kohalikud_varad()


def toonud(url, sihtfail, paised=None):
    """Tõmbab faili, kui seda veel ei ole. Kaust on vahemälu — teine build ei tõmba uuesti."""
    if os.path.exists(sihtfail) and os.path.getsize(sihtfail) > 0:
        return
    os.makedirs(os.path.dirname(sihtfail), exist_ok=True)
    p = urllib.request.Request(url, headers=paised or UA)
    with urllib.request.urlopen(p, timeout=60) as r:
        sisu = r.read()
    with open(sihtfail, "wb") as f:
        f.write(sisu)


def kohalikud_varad():
    """Väline viide -> kohalik fail. Avalik leht ei tohi sõltuda kolmandast serverist."""
    hoiatused, tommatud = [], 0
    idx = os.path.join(OUT, "index.html")
    tugi = os.path.join(OUT, "support.js")
    if not os.path.exists(idx):
        return ["index.html puudub, varasid ei saa kohalikuks teha"]
    html = open(idx, encoding="utf-8", newline="").read()
    js = open(tugi, encoding="utf-8", newline="").read() if os.path.exists(tugi) else ""

    # 1. React, ReactDOM, Babel. CDN maas tähendaks, et leht ei käivitu üldse.
    for url in sorted(set(re.findall(r"https://unpkg\.com/[^\"']+", js))):
        nimi = url.rsplit("/", 1)[-1]
        siht = os.path.join(VARAD, "js", nimi)
        try:
            uus = not os.path.exists(siht)
            toonud(url, siht)
            tommatud += uus
            js = js.replace(url, f"varad/js/{nimi}")
        except Exception as e:
            hoiatused.append(f"vara {nimi}: {e}")

    # 2. OSM plaadid. Staatiline z8 ruudustik, tõmmatakse üks kord.
    osm_ua = {"User-Agent": "eesti-hydromeetriajaamad/1.0 (doktoritoo; staatiline z8 kaart)"}
    for url in sorted(set(re.findall(r"https://tile\.openstreetmap\.org/\d+/\d+/\d+\.png", html))):
        z, tx, ty = url.rsplit("/", 3)[1:]
        nimi = f"{z}_{tx}_{ty}"
        siht = os.path.join(VARAD, "kaart", nimi)
        try:
            uus = not os.path.exists(siht)
            toonud(url, siht, osm_ua)
            tommatud += uus
            if uus:
                time.sleep(0.3)          # ära kolgi võõrast serverit
            html = html.replace(url, f"varad/kaart/{nimi}")
        except Exception as e:
            hoiatused.append(f"kaardiplaat {nimi}: {e}")

    # 3. Google Fonts. Muidu läheb iga külastaja IP Google'ile.
    m = re.search(r"https://fonts\.googleapis\.com/css2\?[^\"']+", html)
    if m:
        url, siht = m.group(0), os.path.join(VARAD, "fondid", "fondid.css")
        try:
            if not os.path.exists(siht):
                # woff2 tuleb ainult siis, kui päring näeb välja nagu brauseri oma
                brauser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/"
                                         "537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                css = urllib.request.urlopen(
                    urllib.request.Request(url.replace("&amp;", "&"), headers=brauser),
                    timeout=60).read().decode("utf-8")
                for f in sorted(set(re.findall(r"https://fonts\.gstatic\.com/[^)\"']+", css))):
                    nimi = f.rsplit("/", 1)[-1]
                    toonud(f, os.path.join(VARAD, "fondid", nimi))
                    tommatud += 1
                    css = css.replace(f, nimi)
                os.makedirs(os.path.dirname(siht), exist_ok=True)
                with open(siht, "w", encoding="utf-8", newline="") as fh:
                    fh.write(css)
            html = html.replace(url, "varad/fondid/fondid.css")
        except Exception as e:
            hoiatused.append(f"fondid: {e}")
    # preconnect Google'i serverile ei ole enam vajalik ega soovitav
    html = re.sub(r"\s*<link rel=\"preconnect\" href=\"https://fonts\.gstatic\.com\"[^>]*>", "", html)

    with open(idx, "w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    if js:
        with open(tugi, "w", encoding="utf-8", newline="") as fh:
            fh.write(js)

    jaanud = sorted(set(re.findall(
        r"https?://(?:unpkg\.com|tile\.openstreetmap\.org|fonts\.(?:googleapis|gstatic)\.com)[^\"'\s)]*",
        html + js)))
    if jaanud:
        hoiatused.append(f"väline viide jäi alles ({len(jaanud)} tk), nt {jaanud[0]}")
    print(f"     varad kohalikud, uusi tõmmatud {tommatud}", flush=True)
    return hoiatused


# ----------------------------------------------------------------- valideeri
def valideeri(doc, kaust):
    v = []
    if len(doc["stations"]) != doc["count"]:
        v.append(f"count {doc['count']} != jaamu {len(doc['stations'])}")
    kohustuslik = ["code", "name", "river", "county", "municipality", "lat", "lon",
                   "catchment_km2", "mouth_distance_km", "opened", "automated",
                   "series_start", "series_days", "q", "q_delta_24h", "median_now",
                   "percentile", "validated", "specific_runoff", "median_specific_runoff",
                   "level_cm", "median_level_cm", "water_temp",
                   "median_water_temp", "photos", "measured", "notes",
                   "level_delta_3h", "level_delta_6h", "level_delta_12h", "level_delta_24h"]
    for s in doc["stations"]:
        for f in kohustuslik:
            if f not in s:
                v.append(f"{s['code']}: väli {f} puudub")
        if s["municipality"] is not None and not isinstance(s["municipality"], str):
            v.append(f"{s['code']}: municipality vale tüüp")
        if not (57.4 <= s["lat"] <= 59.8 and 21.7 <= s["lon"] <= 28.3):
            v.append(f"{s['code']}: koordinaat väljaspool Eestit {s['lat']},{s['lon']}")
        p = os.path.join(kaust, "data", "stations", f"{s['code']}.json")
        if not os.path.exists(p):
            v.append(f"{s['code']}: aegrea fail puudub")
            continue
        j = json.load(open(p, encoding="utf-8"))
        if len(j["daily"]) != 365 or [x["d"] for x in j["daily"]] != list(range(1, 366)):
            v.append(f"{s['code']}: daily ei ole katkematu 1..365")
        for x in j["daily"]:
            jrk = [x.get("p10"), x["p25"], x["med"], x["p75"], x.get("p90")]
            jrk = [y for y in jrk if y is not None]
            if any(a > b for a, b in zip(jrk, jrk[1:])):
                v.append(f"{s['code']}: daily d={x['d']} protsentiilid ei ole kasvavas järjekorras"); break
            if ("p10" in x) != ("p90" in x):
                v.append(f"{s['code']}: daily d={x['d']} p10 ja p90 peavad olema mõlemad või kumbki"); break
        kp = [datetime.date.fromisoformat(x["date"]) for x in j["year"]]
        if any((kp[i + 1] - kp[i]).days != 1 for i in range(len(kp) - 1)):
            v.append(f"{s['code']}: year ei ole katkematu päevade jada")
        vt = j["validated_through"]
        if any(x["validated"] != (x["date"] <= vt) for x in j["year"]):
            v.append(f"{s['code']}: validated ei klapi validated_through-ga")
        # 7. iga code kohta on CSV
        if not os.path.exists(os.path.join(kaust, "data", "csv", f"{s['code']}.csv")):
            v.append(f"{s['code']}: CSV puudub")
        # 8. aegrea failis ei ole operatiivvälju ega photo-t
        lisa = set(j) - {"code", "validated_through", "daily", "year"}
        if lisa:
            v.append(f"{s['code']}: aegreas keelatud väljad {sorted(lisa)}")
        # 9. iga photos-kirje fail on olemas ja source täidetud
        for ph in s.get("photos", []):
            if not ph.get("source"):
                v.append(f"{s['code']}: photos kirjel puudub source")
            if not os.path.exists(os.path.join(kaust, ph["file"].replace("/", os.sep))):
                v.append(f"{s['code']}: photos fail puudub: {ph['file']}")
        if "photo" in s:
            v.append(f"{s['code']}: vana väli 'photo' on käibelt maas")
        # 11. iga notes kirjel on type, text ja source
        for nt in s.get("notes", []):
            if not all(nt.get(f) for f in ("type", "text", "source")):
                v.append(f"{s['code']}: notes kirjel puudub type/text/source")
        # 10. iga measured võti sisaldab kas date või time, mitte mõlemat
        for võti, m in (s.get("measured") or {}).items():
            if m is None:
                continue
            if ("date" in m) == ("time" in m):
                v.append(f"{s['code']}: measured.{võti} peab sisaldama kas date VÕI time")
    return v


# ----------------------------------------------------------------- build
def main():
    os.makedirs(os.path.join(OUT, "data", "stations"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "photos", "ortofoto"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "photos", "jaam"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "data", "csv"), exist_ok=True)
    idx_fail = os.path.join(OUT, "data", "stations.json")

    if ONLY_NOW:
        doc = json.load(open(idx_fail, encoding="utf-8"))
        ids = json.load(open(os.path.join(BASE, "andmed", "ids.json"), encoding="utf-8"))
        for s in doc["stations"]:
            s["_id"] = ids.get(s["code"])
        praegu, vaadeldud = operatiiv(doc["stations"])
        for s in doc["stations"]:
            s.pop("_id", None)
        for s in doc["stations"]:
            o = praegu.get(s["code"], {})
            for f in ("level_cm", "water_temp", "level_delta_3h", "level_delta_6h",
                  "level_delta_12h", "level_delta_24h"):
                if f in o:
                    s[f] = o[f]
        doc["updated"] = vaadeldud.isoformat(timespec="seconds").replace("+00:00", "Z")
        json.dump(doc, open(idx_fail, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"operatiivväljad uuendatud: {len(praegu)}/{len(doc['stations'])} jaama")
        # liides ka siin: muidu jääb veeb/index.html disaini uue ekspordi taha seisma
        for h in kopeeri_liides():
            print(f"  hoiatus: {h}", flush=True)
        return

    meta_fail = os.path.join(BASE, "andmed", "metaandmed.json")
    kraabitud = json.load(open(meta_fail, encoding="utf-8"))["jaamad"] if os.path.exists(meta_fail) else {}

    print("1/4  jaamad ...", flush=True)
    hydro = [s for s in get(f"{EST}/stations") if s["type"] == "HYDROLOGICAL"]
    aktiivsed = [s for s in hydro
                 if get(f"{EST}/stations/{s['code']}/measurements?parameter=Q&start-year=2026&end-year=2026")]
    print(f"     aktiivse Q-ga: {len(aktiivsed)}", flush=True)

    print("2/4  register ...", flush=True)
    koodid = ",".join(s["code"] for s in aktiivsed)
    reg = {r["kkr_kood"]: r for r in get(
        f"{KKA}/f_seirejaamad?kkr_kood=in.({koodid})&select=kood,nimi,kkr_kood,veekogu_nimi,"
        f"ehak_tekst,alg_kpv,kesk_x,kesk_y,suudmest")}
    hs = {}
    for r in get(f"{KKA}/f_hydroseire?timeline_ts_utc=gte.2026-09-01&select=jaam_kood,"
                 f"jaam_laiuskraad,jaam_pikkuskraad,valgala_suurus_km2&limit=20000"):
        hs.setdefault(r["jaam_kood"], r)

    print("3/4  aegread ja normid ...", flush=True)
    stations, vead = [], []
    for i, s in enumerate(aktiivsed, 1):
        kkr = s["code"]
        r = reg.get(kkr, {})
        sid = vali_kood(r.get("kood"), hs)
        h = hs.get(sid, {})
        km2 = h.get("valgala_suurus_km2") or s.get("area")
        km2 = round(km2, 2) if km2 else None

        ts = {}
        for par in ("Q", "H", "T"):
            try:
                t = aegrida(kkr, par)
                if t: ts[par] = t
            except Exception as e:
                vead.append(f"{kkr} {par}: {e}")
        if "Q" not in ts:
            vead.append(f"{kkr}: Q puudub"); continue

        Q = ts["Q"]
        ppQ = paarid(Q)
        viim_kp, viim_q = ppQ[-1]
        # validated_through tuleb ALLIKAST, mitte kalendrist: EstModeli qualityFlag
        # märgib valideerimata read "UNCHECKED"-iks. Kalendrist tuletamine ("eelmise
        # aasta lõpp") oleks 1. jaanuaril valetanud, kuni agentuur pole tegelikult
        # valideerinud. Tagavara ainult siis, kui lipud puuduvad üldse.
        if Q["first_unchecked"] is not None:
            vt = (Q["first_unchecked"] - datetime.timedelta(days=1)).isoformat()
        else:
            vt = Q["end"].isoformat()   # ükski rida pole märgitud kontrollimata -> kõik valideeritud

        kogumQ = aknad(ppQ, vt)
        daily = daily_norm(kogumQ)
        if daily is None:
            vead.append(f"{kkr}: daily normi ei saa arvutada (liiga lühike rida)"); continue
        dv = dix365(viim_kp)
        median_now = mediaan_paeval(kogumQ, dv)
        percentile = None
        w = aken_vaartused(kogumQ, dv)
        if len(w) >= 10:
            percentile = round(100 * sum(1 for x in w if x < viim_q) / len(w))

        # H ja T mediaanid samal kalendripäeval + D-1 väärtused tagavaraks
        med_level = med_temp = None
        d1_level = d1_temp = None
        for par, seter in (("H", "level"), ("T", "temp")):
            if par not in ts:
                continue
            pp = paarid(ts[par])
            kog = aknad(pp, vt)
            m = mediaan_paeval(kog, dv)
            last = pp[-1][1] if pp and pp[-1][0] == viim_kp else None
            if par == "H":
                med_level, d1_level = m, last
            else:
                med_temp, d1_temp = m, last

        delta_q = r3(viim_q - ppQ[-2][1]) if len(ppQ) >= 2 and (viim_kp - ppQ[-2][0]).days == 1 else 0.0

        # viimased 12 kuud, katkematu päevade jada
        algus = viim_kp - datetime.timedelta(days=364)
        kaart = {d: x for d, x in ppQ}
        year = []
        d = algus
        while d <= viim_kp:
            year.append({"date": d.isoformat(), "q": kaart.get(d),
                         "validated": d.isoformat() <= vt})
            d += datetime.timedelta(days=1)

        lat, lon = h.get("jaam_laiuskraad"), h.get("jaam_pikkuskraad")
        if lat is None or lon is None:
            lat, lon = lest_wgs84(r.get("kesk_x"), r.get("kesk_y"))

        ehak = [e.strip() for e in (r.get("ehak_tekst") or "").split(",")] + [None] * 3
        county = re.sub(r"\s*maakond$", "", ehak[0]) if ehak[0] else None
        km = kraabitud.get(kkr, {})
        avatud = (r.get("alg_kpv") or "")[:10]

        # --- fotod: leping p3, massiiv oma viidetega ---
        #
        # Vahemälu on VALMIS pilt väljundis, mitte lähtepilt. Põhjus: avaldamise repos
        # on ainult väljund, sest ringita originaalid ei kuulu avalikule lehele. CI peab
        # seega saama hakkama ilma lähtepiltideta — ja saab, sest valmis pilt on repos.
        # Lähtepildid elavad ainult ehitusmasinas ja neid on vaja ainult siis, kui märki
        # tahetakse muuta: kustuta väljundist pilt ja jooksuta build.
        photos = []
        algne = os.path.join(ORTO_ALGNE, f"{kkr}.jpg")
        orto = os.path.join(OUT, "photos", "ortofoto", f"{kkr}.jpg")
        if not os.path.exists(orto):
            if not os.path.exists(algne) and r.get("kesk_x") and r.get("kesk_y"):
                try:
                    ortofoto(r["kesk_x"], r["kesk_y"], km2, algne)
                except Exception as e:
                    vead.append(f"{kkr} ortofoto: {e}")
            if os.path.exists(algne):
                try:
                    margi_jaam(algne, orto, ortofoto_r(km2))
                except Exception as e:
                    vead.append(f"{kkr} jaamamärk: {e}")
        if os.path.exists(orto):
            photos.append({"file": f"photos/ortofoto/{kkr}.jpg", "type": "ortofoto",
                           "source": "Maa- ja Ruumiamet, jaama märk lisatud"})

        # jaamafoto ainult siis, kui keegi on selle käsitsi lisanud. Sama loogika:
        # kui lähtekaust puudub (CI), jääb varem kopeeritud pilt väljundisse alles.
        kasitsi = os.path.join(FOTOD_KASITSI, f"{kkr}.jpg")
        jaamafoto = os.path.join(OUT, "photos", "jaam", f"{kkr}.jpg")
        if os.path.exists(kasitsi):
            import shutil; shutil.copy2(kasitsi, jaamafoto)
        if os.path.exists(jaamafoto):
            photos.append({"file": f"photos/jaam/{kkr}.jpg",
                           "type": "jaamafoto", "source": "Keskkonnaagentuur"})

        kirje = {
            "_id": sid,          # sisemine, eemaldatakse enne kirjutamist
            "code": kkr,
            "name": re.sub(r"\s*\((?:Hüdro|hüdro)\)", "",
                     (r.get("nimi") or s["name"].split(":")[-1].strip()).replace(" HJ", "")).strip(),
            "river": (r.get("veekogu_nimi") or s["name"].split(":")[0]).split("/")[0].strip(),
            "county": county,
            "municipality": ehak[1],
            "lat": lat, "lon": lon,
            "catchment_km2": km2,
            "mouth_distance_km": round(r["suudmest"], 2) if r.get("suudmest") is not None else None,
            "opened": int(avatud[:4]) if avatud else None,
            "automated": km.get("automated"),
            "series_start": f"{avatud[8:10]}.{avatud[5:7]}.{avatud[:4]}" if avatud else None,
            "series_days": sum(1 for x in Q["v"] if x is not None),
            "photos": photos,
            "notes": NOTES.get(kkr, []),

            "q": viim_q,
            "q_delta_24h": delta_q,
            "median_now": median_now,
            "percentile": percentile,
            "validated": viim_kp.isoformat() <= vt,

            "specific_runoff": round(1000 * viim_q / km2, 1) if km2 else None,
            "median_specific_runoff": round(1000 * median_now / km2, 1) if (km2 and median_now) else None,
            "level_cm": round(d1_level) if d1_level is not None else None,
            "median_level_cm": round(med_level) if med_level is not None else None,
            "level_delta_3h": None,
            "level_delta_6h": None,
            "level_delta_12h": None,
            "level_delta_24h": None,
            "water_temp": round(d1_temp, 1) if d1_temp is not None else None,
            "median_water_temp": round(med_temp, 1) if med_temp is not None else None,
            # Leping p2a. Vooluhulk ja äravoolumoodul on ööpäevased -> date.
            # Veetase ja temperatuur saavad time-i siis, kui tulevad operatiivkihist;
            # muidu jäävad ööpäevaseks ja kannavad date-i. Täidetakse allpool.
            "measured": {
                "q": {"date": viim_kp.isoformat()},
                "runoff": {"date": viim_kp.isoformat()} if km2 else None,
                "level": {"date": viim_kp.isoformat()} if d1_level is not None else None,
                "water_temp": {"date": viim_kp.isoformat()} if d1_temp is not None else None,
            },
        }
        stations.append(kirje)

        # Leping p2: aegrea fail sisaldab AINULT aegrida. Identiteet, operatiivseis
        # ja photo on stations.json-is ega tohi siin korduda.
        json.dump({"code": kkr, "validated_through": vt, "daily": daily, "year": year},
                  open(os.path.join(OUT, "data", "stations", f"{kkr}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        csv_ridu = kirjuta_csv(kkr, Q, ts, vt, os.path.join(OUT, "data", "csv"))
        print(f"     [{i:>2}/{len(aktiivsed)}] {kirje['name']:<18} {kirje['river']:<22} "
              f"daily {len(daily)}  year {len(year)}  pct {percentile}  csv {csv_ridu}", flush=True)

    print("4/4  operatiivnäidud XML-ist ...", flush=True)
    praegu, vaadeldud = operatiiv(stations)
    kaetud = 0
    for s in stations:
        o = praegu.get(s["code"], {})
        if o: kaetud += 1
        for f in ("level_cm", "water_temp", "level_delta_3h", "level_delta_6h",
                  "level_delta_12h", "level_delta_24h"):
            if f in o:
                s[f] = o[f]
        if o.get("_tund"):
            if "level_cm" in o:
                s["measured"]["level"] = {"time": o["_tund"]}
            if "water_temp" in o:
                s["measured"]["water_temp"] = {"time": o["_tund"]}
    print(f"     operatiivselt kaetud {kaetud}/{len(stations)}, ülejäänud D-1 väärtustel", flush=True)

    ids = {s["code"]: s.pop("_id", None) for s in stations}
    json.dump(ids, open(os.path.join(BASE, "andmed", "ids.json"), "w", encoding="utf-8"), indent=1)
    stations.sort(key=lambda k: (k["river"], k["name"]))
    vt_global = min(json.load(open(os.path.join(OUT, "data", "stations", f"{s['code']}.json"),
                                   encoding="utf-8"))["validated_through"] for s in stations)
    doc = {"updated": vaadeldud.isoformat(timespec="seconds").replace("+00:00", "Z"),
           "count": len(stations), "validated_through": vt_global, "stations": stations}
    json.dump(doc, open(idx_fail, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\nliides disaini ekspordist ...", flush=True)
    vead += kopeeri_liides()

    print("\nvalideerimine ...", flush=True)
    probleemid = valideeri(doc, OUT)
    if probleemid:
        print(f"  {len(probleemid)} probleemi:")
        for p in probleemid[:25]:
            print("   ", p)
    else:
        print("  kõik 11 lepingu kontrolli läbitud")
    if vead:
        print(f"\nehitusvead ({len(vead)}): {vead}")
    print(f"\nvalmis: {len(stations)} jaama -> {OUT}")


if __name__ == "__main__":
    main()
