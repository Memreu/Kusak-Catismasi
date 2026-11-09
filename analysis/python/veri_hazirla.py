"""Ham SPSS verisini analize hazır, anonim bir CSV'ye dönüştürür.

Ham veri (Genel_Spss.sav, Yanıt Tablosu.xlsx) katılımcı gizliliği nedeniyle repoda
bulunmaz. Bu betik yalnızca ham veriye erişimi olan araştırmacılar içindir; çıktısı
`data/private/` klasörüne yazılır ve `.gitignore` ile GitHub'a gönderilmez.

Kullanım:
    python analysis/python/veri_hazirla.py --sav Genel_Spss.sav [--xlsx "Yanıt Tablosu.xlsx"]

Neden xlsx?
    SPSS dosyasındaki `OrtSipariş` (aylık sipariş sıklığı) değişkeninde "3-5 Kez" ve
    "9-11 Kez" yanıtları aynı koda (4) birleşmiş durumda. Yanıt tablosu verilirse her
    SPSS satırı, 21 Likert maddesinin birebir eşleşmesiyle orijinal form yanıtına
    bağlanır ve sipariş sıklığı düzeltilir. Eşleşmeyen satırlarda bu değişken boş bırakılır.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "private" / "analiz_verisi.csv"

LIKERT = ["SIN1", "PERF2", "PERF3", "PERF4", "CABA5", "CABA6", "CABA7", "DUYG8", "DUYG9",
          "DUYG10", "FIY11", "FIY12", "FIY13", "KONT14", "SAD15", "SAD16", "SAD17",
          "ALS18", "ALS19", "ALS20", "ALS21"]
SIKLIK = {"0-2 Kez": 1, "3-5 Kez": 2, "6-8 Kez": 3, "9-11 Kez": 4, "+12 Kez": 5}
# SPSS kodu -> düzeltilmiş kod (4 belirsiz: 3-5 veya 9-11)
SPSS_SIKLIK = {1: 1, 7: 3, 5: 5}


def hazirla(sav: Path, xlsx: Path | None = None) -> pd.DataFrame:
    import pyreadstat

    df, _ = pyreadstat.read_sav(str(sav))
    out = pd.DataFrame({
        "kusak": df["Kusak"].map({1: "Z", 2: "Diğer"}),
        "cinsiyet": df["Cinsiyet"].map({1: "Erkek", 2: "Kadın"}),
        "egitim": df["Egitim"].astype(int),
        "meslek": df["Meslek"].astype(int),
        "eko_durum": df["Eko_Durum"].map({1: "Kötü", 2: "Orta", 3: "İyi"}),
        "sehir_grup": df["Sehir_Grup"].map({1: "Büyükşehir", 99: "Diğer"}),
        "uygulama": df["SıkUygulama"].astype(int),
        "uygulama_sayisi": df["KaçUygulama"].astype(int),
    })
    out["siparis_sikligi"] = df["OrtSipariş"].map(SPSS_SIKLIK).astype("Int64")

    if xlsx is not None:
        raw = pd.read_excel(xlsx)
        items = raw.iloc[:, 12:33].copy()
        items.columns = LIKERT
        items["siklik"] = raw.iloc[:, 11].map(SIKLIK)
        items["yas"] = raw.iloc[:, 2]
        items = items.dropna(subset=LIKERT)
        lookup: dict[tuple, set] = {}
        yaslar: dict[tuple, set] = {}
        for _, r in items.iterrows():
            k = tuple(r[LIKERT].astype(int))
            lookup.setdefault(k, set()).add(r["siklik"])
            yaslar.setdefault(k, set()).add(r["yas"])
        # Yaş kaydedilmez; yalnızca evren tanımı (18+) dışında kalan yanıtlar işaretlenir.
        out["yas_18_alti"] = [
            (lambda a: bool(a) and all(v < 18 for v in a))(yaslar.get(tuple(r[LIKERT].astype(int)), set()))
            for _, r in df.iterrows()
        ]
        print(f"18 yaş altı görünen yanıt: {int(out.yas_18_alti.sum())}")
        duzeltilen = 0
        for i, r in df.iterrows():
            adaylar = lookup.get(tuple(r[LIKERT].astype(int)), set())
            if len(adaylar) == 1 and not np.isnan(next(iter(adaylar))):
                out.loc[i, "siparis_sikligi"] = int(next(iter(adaylar)))
                duzeltilen += 1
        print(f"Sipariş sıklığı yanıt tablosuyla {duzeltilen}/{len(df)} satırda doğrulandı.")
    else:
        print("Uyarı: yanıt tablosu verilmedi; '3-5' ve '9-11 Kez' ayrıştırılamadığı için "
              "bu satırlarda sipariş sıklığı boş bırakıldı.")

    for c in LIKERT:
        out[c] = df[c].astype(int)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sav", type=Path, required=True)
    ap.add_argument("--xlsx", type=Path)
    a = ap.parse_args()
    data = hazirla(a.sav, a.xlsx)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUT, index=False)
    print(f"{len(data)} satır → {OUT.relative_to(ROOT)}")
