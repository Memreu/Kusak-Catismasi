"""Gerçek veriden gizliliği koruyan sentetik bir veri seti üretir (Gauss kopula).

Ham anket verisi paylaşılamadığı için repodaki kodların herkes tarafından
çalıştırılabilmesi amacıyla `data/sentetik_veri.csv` bu betikle üretilmiştir.

Yöntem:
1. Her değişken, sıra (rank) dönüşümüyle standart normal skorlara çevrilir.
2. Bu skorların korelasyon matrisi hesaplanır.
3. Aynı korelasyon yapısına sahip çok değişkenli normal dağılımdan yeni örnekler çekilir.
4. Her değişken, gerçek verideki marjinal dağılımın yüzdelikleri kullanılarak orijinal
   kategorilerine geri dönüştürülür.

Sonuç: Tek tek değişkenlerin dağılımları ve değişkenler arası ilişkiler yaklaşık olarak
korunur, ancak hiçbir satır gerçek bir katılımcıya karşılık gelmez. Betik, üretilen
satırların hiçbirinin gerçek veride birebir bulunmadığını ayrıca kontrol eder.

Kullanım:
    python analysis/python/sentetik_veri.py   # data/private/analiz_verisi.csv gerektirir
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "private" / "analiz_verisi.csv"
OUT = ROOT / "data" / "sentetik_veri.csv"


def uret(real: pd.DataFrame, n: int, seed: int = 2025) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    real = real.copy()
    real["siparis_sikligi"] = real["siparis_sikligi"].fillna(real["siparis_sikligi"].mode()[0])

    codes, cats = {}, {}
    for c in real.columns:
        if not pd.api.types.is_numeric_dtype(real[c]):
            cat = pd.Categorical(real[c])
            cats[c] = cat.categories
            codes[c] = cat.codes.astype(float)
        else:
            codes[c] = real[c].astype(float).to_numpy()
    X = pd.DataFrame(codes)

    # 1-2) normal skorlar ve korelasyon (eşitlikler rastgele kırılır)
    Z = X.apply(lambda s: stats.norm.ppf(
        (stats.rankdata(s + rng.uniform(-1e-6, 1e-6, len(s))) - 0.5) / len(s)))
    corr = np.corrcoef(Z.to_numpy(), rowvar=False)
    # 3) örnekleme
    sample = rng.multivariate_normal(np.zeros(len(corr)), corr, size=n)
    U = stats.norm.cdf(sample)
    # 4) marjinallere geri dönüş
    out = {}
    for i, c in enumerate(X.columns):
        vals = np.quantile(X[c].to_numpy(), U[:, i], method="inverted_cdf")
        out[c] = pd.Categorical.from_codes(vals.astype(int), cats[c]) if c in cats else vals.astype(int)
    return pd.DataFrame(out)[real.columns]


if __name__ == "__main__":
    real = pd.read_csv(SRC).drop(columns=["yas_18_alti"], errors="ignore")
    syn = uret(real, n=len(real))

    likert = [c for c in real.columns if c[:3] in {"SIN", "PER", "CAB", "DUY", "FIY", "KON", "SAD", "ALS"}]
    ortak = set(map(tuple, real[likert].to_numpy())) & set(map(tuple, syn[likert].to_numpy()))
    assert not ortak, f"{len(ortak)} sentetik satır gerçek bir yanıtla birebir aynı!"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    syn.to_csv(OUT, index=False)
    fark = (real[likert].corr() - syn[likert].corr()).abs().to_numpy()
    print(f"{len(syn)} sentetik satır → {OUT.relative_to(ROOT)}")
    print(f"Gerçek satırla birebir eşleşen sentetik satır: 0 · "
          f"madde korelasyonlarındaki ortalama mutlak fark: {np.nanmean(fark[np.triu_indices(len(likert), 1)]):.3f}")
