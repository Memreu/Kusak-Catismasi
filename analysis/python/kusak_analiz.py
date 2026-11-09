"""Kuşak Çatışması anketinin uçtan uca analizi (Python).

Kullanım:
    python analysis/python/kusak_analiz.py                 # sentetik veriyle (repoda hazır)
    python analysis/python/kusak_analiz.py --gercek        # data/private/analiz_verisi.csv ile

Çıktılar `results/` (sentetik veride `results/sentetik/`) klasörüne yazılır:
    tablolar/*.md      okunabilir sonuç tabloları
    sonuclar.json      README'de kullanılan özet sayılar
    grafikler/*.png    görseller
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

from pls_sem import PLSModel, cronbach_alpha

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = {
    "PERF": ["PERF2", "PERF3", "PERF4"],
    "CABA": ["CABA5", "CABA6", "CABA7"],
    "DUYG": ["DUYG8", "DUYG9", "DUYG10"],
    "FIY": ["FIY11", "FIY12", "FIY13"],
    "ALS": ["ALS18", "ALS19", "ALS20", "ALS21"],
    "SAD": ["SAD15", "SAD16", "SAD17"],
}
NAMES = {"PERF": "Performans beklentisi", "CABA": "Çaba beklentisi", "DUYG": "Duygusal değer",
         "FIY": "Fiyat değeri", "ALS": "Alışkanlık", "SAD": "Sadakat"}
PATHS = [("PERF", "DUYG"), ("CABA", "DUYG"), ("PERF", "FIY"), ("CABA", "FIY"),
         ("DUYG", "SAD"), ("FIY", "SAD"), ("ALS", "SAD")]
SIKLIK = {1: "0-2", 2: "3-5", 3: "6-8", 4: "9-11", 5: "12+"}
MESLEK = {1: "Öğrenci", 2: "Tam zamanlı", 3: "Yarı zamanlı", 4: "Serbest", 5: "Emekli", 6: "İşsiz"}
UYGULAMA = {1: "Yemeksepeti", 2: "Getir", 3: "Trendyol", 4: "TıklaGelsin", 5: "Diğer"}

BLUE, RED, ORANGE, GREEN, GREY, PURPLE = "#2E5EAA", "#C0392B", "#E67E22", "#29A36A", "#8C8C8C", "#6C3483"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 110, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.grid": True,
                     "grid.alpha": 0.3, "font.family": "DejaVu Sans"})


def p_fmt(p: float) -> str:
    return "< .001" if p < 0.001 else f"{p:.3f}".replace("0.", ".", 1)


def p_lbl(p: float) -> str:
    return "p < .001" if p < 0.001 else f"p = {p_fmt(p)}"


def md(df: pd.DataFrame, path: Path, title: str, note: str = "") -> None:
    txt = f"## {title}\n\n{df.to_markdown(index=False, floatfmt='.3f')}\n"
    if note:
        txt += f"\n{note}\n"
    path.write_text(txt, encoding="utf-8")


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=1)


# --------------------------------------------------------------------------- #
def main(gercek: bool, n_boot: int) -> None:
    src = ROOT / "data" / ("private/analiz_verisi.csv" if gercek else "sentetik_veri.csv")
    out = ROOT / "results" if gercek else ROOT / "results" / "sentetik"
    tab, fig = out / "tablolar", out / "grafikler"
    tab.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(src)
    for lv, cols in BLOCKS.items():
        d[lv] = d[cols].mean(axis=1)
    R: dict = {"veri": "gerçek" if gercek else "sentetik", "n": len(d),
               "n_z": int((d.kusak == "Z").sum()), "n_diger": int((d.kusak == "Diğer").sum())}

    # 1) Güvenilirlik ve geçerlilik (PLS ölçüm modeli) ------------------------
    model = PLSModel(BLOCKS, PATHS)
    pls = model.fit(d)
    rel = pls.reliability.copy()
    rel.insert(0, "yapı", [NAMES[i] for i in rel.index])
    rel["madde"] = [len(BLOCKS[i]) for i in pls.reliability.index]
    md(rel, tab / "01_guvenilirlik.md", "Güvenilirlik ve yakınsak geçerlilik",
       "Eşikler: Cronbach α ≥ .60 (keşifsel), birleşik güvenilirlik ρc ≥ .70, AVE ≥ .50.")
    htmt = pls.htmt.round(3)
    (tab / "02_htmt.md").write_text("## HTMT oranları\n\n" + htmt.fillna("").to_markdown() +
                                    "\n\nEşik: < .85 (Henseler vd., 2015).\n", encoding="utf-8")
    fl = pls.fornell_larcker.round(3)
    (tab / "03_fornell_larcker.md").write_text(
        "## Fornell-Larcker kriteri\n\nKöşegen: √AVE, diğer hücreler: gizil değişken korelasyonları.\n\n"
        + fl.to_markdown() + "\n", encoding="utf-8")
    R["guvenilirlik"] = pls.reliability.round(3).to_dict(orient="index")
    R["htmt_max"] = float(np.nanmax(pls.htmt.to_numpy()))
    R["vif_max"] = float(pls.outer_vif.max())

    # 2) Normallik ------------------------------------------------------------
    norm = pd.DataFrame({"yapı": [NAMES[k] for k in BLOCKS],
                         "çarpıklık": [stats.skew(d[k], bias=False) for k in BLOCKS],
                         "basıklık": [stats.kurtosis(d[k], bias=False) for k in BLOCKS]})
    md(norm, tab / "04_normallik.md", "Çarpıklık ve basıklık", "Referans aralığı: ±2.")

    # 3) Ki-kare testleri -----------------------------------------------------
    d["indirim_onemli"] = np.where(d.SIN1 >= 5, "Evet", "Hayır")
    rows = []
    for ad, a, b in [("Kuşak × sipariş sıklığı", "kusak", "siparis_sikligi"),
                     ("Kuşak × en sık kullanılan uygulama", "kusak", "uygulama"),
                     ("Kuşak × indirimin belirleyici olması", "kusak", "indirim_onemli"),
                     ("Şehir büyüklüğü × uygulama", "sehir_grup", "uygulama")]:
        ct = pd.crosstab(d[a], d[b])
        chi2, p, dof, exp = stats.chi2_contingency(ct, correction=False)
        v = np.sqrt(chi2 / (ct.to_numpy().sum() * (min(ct.shape) - 1)))
        rows.append({"test": ad, "n": int(ct.to_numpy().sum()), "χ²": chi2, "sd": dof, "p": p,
                     "Cramér V": v, "beklenen < 5 olan hücre %": 100 * (exp < 5).mean()})
    chi = pd.DataFrame(rows)
    md(chi, tab / "05_ki_kare.md", "Ki-kare bağımsızlık testleri",
       "Sipariş sıklığı, SPSS dosyasındaki kodlama hatası düzeltilerek kullanılmıştır (bkz. README).")
    R["ki_kare"] = chi.set_index("test")[["χ²", "sd", "p", "Cramér V"]].round(3).to_dict(orient="index")
    zr = pd.crosstab(d.kusak, d.indirim_onemli, normalize="index")["Evet"]
    R["indirim_onemli_oran"] = zr.round(3).to_dict()

    # 4) t-testleri -----------------------------------------------------------
    def ttests(group: str, a: str, b: str, vars_: list[str]) -> pd.DataFrame:
        rows = []
        for v in vars_:
            x, y = d.loc[d[group] == a, v], d.loc[d[group] == b, v]
            t = stats.ttest_ind(x, y)
            welch = stats.ttest_ind(x, y, equal_var=False)
            sp = np.sqrt(((len(x) - 1) * x.var() + (len(y) - 1) * y.var()) / (len(x) + len(y) - 2))
            rows.append({"yapı": NAMES[v], f"{a} ort.": x.mean(), f"{b} ort.": y.mean(),
                         "t": t.statistic, "sd": t.df, "p": t.pvalue,
                         "Welch p": welch.pvalue, "Cohen d": (x.mean() - y.mean()) / sp})
        return pd.DataFrame(rows)

    t_kusak = ttests("kusak", "Z", "Diğer", list(BLOCKS))
    if "yas_18_alti" in d and d.yas_18_alti.any():  # duyarlılık analizi: 18 yaş altını çıkar
        tam = d
        d = d[~d.yas_18_alti.astype(bool)]
        t_18 = ttests("kusak", "Z", "Diğer", list(BLOCKS))
        d = tam
        md(t_18, tab / "06b_t_kusak_18_ustu.md", "Duyarlılık: 18 yaş altı yanıtlar çıkarıldığında kuşak karşılaştırması",
           f"{int(d.yas_18_alti.sum())} yanıt araştırma evreninin (18+) dışında kaldığı için çıkarılmıştır; n = {int((~d.yas_18_alti.astype(bool)).sum())}.")
        R["duyarlilik_18"] = {"cikarilan": int(d.yas_18_alti.sum()),
                              "p": t_18.set_index("yapı").p.round(4).to_dict()}
    t_cins = ttests("cinsiyet", "Kadın", "Erkek", list(BLOCKS))
    t_sehir = ttests("sehir_grup", "Büyükşehir", "Diğer", list(BLOCKS))
    md(t_kusak, tab / "06_t_kusak.md", "Kuşağa göre karşılaştırma (H4a, H4b)")
    md(t_cins, tab / "07_t_cinsiyet.md", "Cinsiyete göre karşılaştırma")
    md(t_sehir, tab / "08_t_sehir.md", "Şehir büyüklüğüne göre karşılaştırma")
    R["t_kusak"] = t_kusak.set_index("yapı").round(3).to_dict(orient="index")
    R["t_cinsiyet"] = t_cins.set_index("yapı").round(3).to_dict(orient="index")
    R["t_sehir_min_p"] = float(t_sehir.p.min())

    # 5) ANOVA ----------------------------------------------------------------
    an = d.dropna(subset=["siparis_sikligi"]).copy()
    an["siklik"] = an.siparis_sikligi.astype(int).map(SIKLIK)
    m1 = smf.ols("ALS ~ C(siklik)", an).fit()
    a1 = sm.stats.anova_lm(m1, typ=2)
    eta1 = a1.sum_sq.iloc[0] / a1.sum_sq.sum()
    rho = stats.spearmanr(an.siparis_sikligi, an.ALS)
    d["meslek_ad"] = d.meslek.map(MESLEK)
    m2 = smf.ols("CABA ~ C(meslek_ad)", d).fit()
    a2 = sm.stats.anova_lm(m2, typ=2)
    m3 = smf.ols("SAD ~ C(kusak, Sum) * C(cinsiyet, Sum)", d).fit()
    a3 = sm.stats.anova_lm(m3, typ=3).drop(index="Intercept")
    anova = pd.DataFrame([
        {"model": "Alışkanlık ~ sipariş sıklığı", "F": a1.F.iloc[0], "sd1": a1.df.iloc[0],
         "sd2": a1.df.iloc[1], "p": a1["PR(>F)"].iloc[0], "η²": eta1},
        {"model": "Çaba beklentisi ~ meslek", "F": a2.F.iloc[0], "sd1": a2.df.iloc[0],
         "sd2": a2.df.iloc[1], "p": a2["PR(>F)"].iloc[0], "η²": a2.sum_sq.iloc[0] / a2.sum_sq.sum()},
        *[{"model": f"Sadakat ~ kuşak × cinsiyet: {k.replace('C(kusak, Sum)', 'kuşak').replace('C(cinsiyet, Sum)', 'cinsiyet')}",
           "F": r.F, "sd1": r.df, "sd2": a3.df.iloc[-1], "p": r["PR(>F)"],
           "η²": r.sum_sq / (r.sum_sq + a3.sum_sq.iloc[-1])}
          for k, r in a3.iloc[:-1].iterrows()],
    ])
    md(anova, tab / "09_anova.md", "Varyans analizleri",
       "İki yönlü ANOVA'da Tip III kareler toplamı kullanılmıştır. η²: kısmi eta kare.")
    R["anova_siklik"] = {"F": a1.F.iloc[0], "sd": [int(a1.df.iloc[0]), int(a1.df.iloc[1])],
                         "p": a1["PR(>F)"].iloc[0], "eta2": eta1, "spearman": rho.statistic,
                         "ortalamalar": an.groupby("siparis_sikligi").ALS.mean().round(2).to_dict()}
    R["anova_meslek_p"] = a2["PR(>F)"].iloc[0]
    inter = a3.iloc[-2]
    R["makas"] = {"F": inter.F, "p": inter["PR(>F)"],
                  "ortalamalar": d.groupby(["kusak", "cinsiyet"]).SAD.mean().round(2)
                  .rename(lambda x: x).to_dict()}
    R["makas"]["ortalamalar"] = {f"{k[0]}-{k[1]}": v for k, v in R["makas"]["ortalamalar"].items()}

    # 6) Regresyonlar (standartlaştırılmış) ------------------------------------
    zd = d[list(BLOCKS)].apply(zscore)
    regs = []
    for y, xs, h in [("DUYG", ["PERF", "CABA"], "H1a, H2a"), ("FIY", ["PERF", "CABA"], "H1b, H2b"),
                     ("SAD", ["DUYG", "FIY"], "H3a, H3b"), ("SAD", ["DUYG", "FIY", "ALS"], "ek")]:
        m = smf.ols(f"{y} ~ {' + '.join(xs)}", zd).fit()
        for x in xs:
            regs.append({"hipotez": h, "bağımlı": NAMES[y], "bağımsız": NAMES[x], "β": m.params[x],
                         "t": m.tvalues[x], "p": m.pvalues[x], "R²": m.rsquared, "F": m.fvalue})
    regs = pd.DataFrame(regs)
    md(regs, tab / "10_regresyon.md", "Çoklu regresyon (standartlaştırılmış katsayılar)")
    R["regresyon"] = regs.round(3).to_dict(orient="records")

    # 7) Moderasyon (H5, H6) -----------------------------------------------------
    c = d.copy()
    for v in ["DUYG", "FIY", "ALS"]:
        c[v + "_c"] = c[v] - c[v].mean()
    c["eko"] = pd.Categorical(c.eko_durum, ["Kötü", "Orta", "İyi"])
    mods = []
    for ad, base, full in [
        ("H5a: Duygusal değer × Alışkanlık", "SAD ~ DUYG_c + ALS_c", "+ DUYG_c:ALS_c"),
        ("H5b: Fiyat değeri × Alışkanlık", "SAD ~ FIY_c + ALS_c", "+ FIY_c:ALS_c"),
        ("H6a: Fiyat değeri × Ekonomik algı", "SAD ~ FIY_c + C(eko)", "+ FIY_c:C(eko)"),
        ("H6b: Duygusal değer × Ekonomik algı", "SAD ~ DUYG_c + C(eko)", "+ DUYG_c:C(eko)"),
    ]:
        m0, m1_ = smf.ols(base, c).fit(), smf.ols(f"{base} {full}", c).fit()
        f, p, df_diff = m1_.compare_f_test(m0)
        mods.append({"etkileşim": ad, "ΔR²": m1_.rsquared - m0.rsquared, "F": f,
                     "sd": int(df_diff), "p": p})
    mods = pd.DataFrame(mods)
    slopes = []
    for g in ["Kötü", "Orta", "İyi"]:
        s = c[c.eko_durum == g]
        row = {"ekonomik algı": g, "n": len(s)}
        for x in ["DUYG", "FIY"]:
            m = smf.ols(f"SAD ~ {x}", s.assign(SAD=zscore(s.SAD), **{x: zscore(s[x])})).fit()
            row[f"β ({NAMES[x].lower()})"] = m.params[x]
            row[f"p ({NAMES[x].lower()})"] = m.pvalues[x]
        slopes.append(row)
    slopes = pd.DataFrame(slopes)
    md(mods, tab / "11_moderasyon.md", "Moderasyon analizleri (merkezlenmiş değişkenler)",
       "Her model tek bir bağımsız değişken, düzenleyici değişken ve etkileşim teriminden oluşur (PROCESS Model 1 mantığı). "
       "Ekonomik algı iki kukla değişkenle (Orta, İyi; referans: Kötü) modellenmiştir; F testi iki etkileşim terimini birlikte sınar.")
    md(slopes, tab / "12_eko_gruplar.md", "Ekonomik algı gruplarında değer → sadakat (standartlaştırılmış β)")
    R["moderasyon"] = mods.round(4).set_index("etkileşim").to_dict(orient="index")
    R["eko_gruplar"] = slopes.round(3).set_index("ekonomik algı").to_dict(orient="index")

    # 8) Aracılık: bootstrap dolaylı etki ---------------------------------------
    rng = np.random.default_rng(7)
    med = []
    for m_ in ["DUYG", "FIY"]:
        def ab(df):
            a = smf.ols(f"{m_} ~ PERF", df).fit().params["PERF"]
            fit = smf.ols(f"SAD ~ PERF + {m_}", df).fit()
            return a * fit.params[m_], fit.params["PERF"]
        ind, direct = ab(zd)
        total = smf.ols("SAD ~ PERF", zd).fit().params["PERF"]
        boots = [ab(zd.iloc[rng.integers(0, len(zd), len(zd))])[0] for _ in range(n_boot)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        med.append({"yol": f"Performans → {NAMES[m_]} → Sadakat", "toplam (c)": total,
                    "doğrudan (c')": direct, "dolaylı (a×b)": ind, "%95 GA alt": lo, "%95 GA üst": hi})
    med = pd.DataFrame(med)
    md(med, tab / "13_aracilik.md", "Aracılık analizi (standartlaştırılmış, bootstrap)",
       f"Dolaylı etkinin güven aralığı {n_boot} bootstrap örneğiyle hesaplanmıştır (yüzdelik yöntem).")
    R["aracilik"] = med.round(3).to_dict(orient="records")

    # 9) PLS-SEM yapısal model ---------------------------------------------------
    boot = model.bootstrap(d, n_boot=n_boot, indirect=[("PERF", "DUYG", "SAD"), ("CABA", "DUYG", "SAD"),
                                                       ("PERF", "FIY", "SAD"), ("CABA", "FIY", "SAD")])
    boot = boot.merge(pls.f2.assign(yol=pls.f2.kaynak + " → " + pls.f2.hedef)[["yol", "f2"]],
                      on="yol", how="left")
    md(boot, tab / "14_pls_sem.md", "PLS-SEM yapısal model (bootstrap)",
       f"R²: " + ", ".join(f"{NAMES[k]} = {v:.3f}" for k, v in pls.r2.items())
       + f". {n_boot} bootstrap örneği; GA: %95 yüzdelik güven aralığı.")
    R["pls"] = {"r2": pls.r2.round(3).to_dict(),
                "yollar": boot.round(4).set_index("yol").to_dict(orient="index")}

    (out / "sonuclar.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float),
                                       encoding="utf-8")

    # 10) Grafikler ---------------------------------------------------------------
    grafik_model(pls, boot, fig / "01_pls_model.png")
    grafik_kusak(d, t_kusak, fig / "02_kusak_karsilastirma.png")
    grafik_makas_eko(d, slopes, fig / "03_makas_ve_ekonomi.png")
    grafik_siklik(an, fig / "04_siklik_aliskanlik.png")
    grafik_htmt(pls, fig / "05_olcum_modeli.png")
    print(f"Analiz tamamlandı ({R['veri']} veri, n={len(d)}) → {out.relative_to(ROOT)}")


# --------------------------------------------------------------------------- #
def grafik_model(pls, boot, path):
    pos = {"PERF": (0.08, 0.72), "CABA": (0.08, 0.28), "DUYG": (0.45, 0.72), "FIY": (0.45, 0.28),
           "ALS": (0.45, 0.02), "SAD": (0.85, 0.45)}
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(-0.08, 1.02); ax.set_ylim(-0.12, 0.92); ax.axis("off")
    b = boot.set_index("yol")
    for s, t in PATHS:
        r = b.loc[f"{s} → {t}"]
        (x1, y1), (x2, y2) = pos[s], pos[t]
        sig = r.p < 0.05
        ax.annotate("", xy=(x2 - 0.075, y2 + (y1 - y2) * 0.12), xytext=(x1 + 0.075, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1 + 5 * abs(r.katsayi),
                                    color=BLUE if sig else GREY, alpha=0.85))
        stars = "***" if r.p < .001 else "**" if r.p < .01 else "*" if r.p < .05 else " (ns)"
        tpos = {("PERF", "FIY"): 0.25, ("CABA", "DUYG"): 0.75}.get((s, t), 0.5)
        lx, ly = x1 + (x2 - x1) * tpos, y1 + (y2 - y1) * tpos
        ax.text(lx, ly + 0.035, f"β = {r.katsayi:.2f}{stars}", ha="center",
                fontsize=10, bbox=dict(fc="white", ec="none", pad=1.5))
    for lv, (x, y) in pos.items():
        endo = lv in pls.r2.index
        ax.add_patch(matplotlib.patches.FancyBboxPatch((x - 0.075, y - 0.06), 0.15, 0.12,
                     boxstyle="round,pad=0.01", fc="#EAF0FA" if not endo else "#FDEBD0",
                     ec=BLUE if not endo else ORANGE, lw=2))
        ax.text(x, y + (0.012 if endo else 0), NAMES[lv].replace(" ", "\n", 1), ha="center",
                va="center", fontsize=10, fontweight="bold")
        if endo:
            ax.text(x, y - 0.04, f"R² = {pls.r2[lv]:.2f}", ha="center", fontsize=9, color=ORANGE)
    ax.set_title("PLS-SEM yapısal model: standartlaştırılmış yol katsayıları")
    ax.text(0.5, -0.11, "* p < .05  ** p < .01  *** p < .001 · ok kalınlığı katsayıyla orantılı",
            ha="center", fontsize=9, color=GREY)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)


def grafik_kusak(d, t_kusak, path):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    keys = list(BLOCKS); x = np.arange(len(keys)); w = 0.38
    for i, (g, col) in enumerate([("Z", ORANGE), ("Diğer", BLUE)]):
        s = d[d.kusak == g]
        m = [s[k].mean() for k in keys]
        ci = [1.96 * s[k].std() / np.sqrt(len(s)) for k in keys]
        ax.bar(x + (i - 0.5) * w, m, w, yerr=ci, capsize=3, color=col,
               label=f"{'Z kuşağı' if g == 'Z' else 'Diğer kuşaklar'} (n={len(s)})")
    for i, r in enumerate(t_kusak.itertuples()):
        if r.p < 0.05:
            ax.text(i, 6.4, p_lbl(r.p), ha="center", color=RED, fontweight="bold", fontsize=9)
    ax.set_xticks(x, [NAMES[k].replace(" ", "\n") for k in keys]); ax.set_ylim(1, 7.6)
    ax.set_ylabel("Ortalama (1–7)"); ax.legend(loc="upper right", ncol=2)
    ax.set_title("Kuşaklara göre yapı ortalamaları (%95 GA)")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)


def grafik_makas_eko(d, slopes, path):
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    for g, col, mk in [("Kadın", PURPLE, "o"), ("Erkek", GREEN, "s")]:
        s = d[d.cinsiyet == g].groupby("kusak").SAD.agg(["mean", "std", "count"]).loc[["Z", "Diğer"]]
        ci = 1.96 * s["std"] / np.sqrt(s["count"])
        ax[0].errorbar([0, 1], s["mean"], yerr=ci, marker=mk, ms=8, lw=2.4, capsize=4, color=col, label=g)
    ax[0].set_xticks([0, 1], ["Z kuşağı", "Diğer kuşaklar"]); ax[0].set_xlim(-0.3, 1.3)
    ax[0].set_ylabel("Sadakat ortalaması"); ax[0].legend(title="Cinsiyet")
    ax[0].set_title("Makas etkisi: kuşak × cinsiyet")
    cols = {"Kötü": RED, "Orta": ORANGE, "İyi": GREEN}
    for _, r in slopes.iterrows():
        g = r["ekonomik algı"]
        s = d[d.eko_durum == g]
        b, a = np.polyfit(s.DUYG, s.SAD, 1)
        xs = np.linspace(s.DUYG.min(), s.DUYG.max(), 10)
        ax[1].scatter(s.DUYG, s.SAD, s=12, alpha=0.25, color=cols[g])
        ax[1].plot(xs, a + b * xs, lw=2.6, color=cols[g],
                   label=f"{g} (n={r.n}): β = {r['β (duygusal değer)']:.2f}, {p_lbl(r['p (duygusal değer)'])}")
    ax[1].set_xlabel("Duygusal değer"); ax[1].set_ylabel("Sadakat"); ax[1].legend(fontsize=9)
    ax[1].set_title("Ekonomik algıya göre duygusal değer → sadakat")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)


def grafik_siklik(an, path):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    g = an.groupby("siparis_sikligi").ALS.agg(["mean", "std", "count"])
    ci = 1.96 * g["std"] / np.sqrt(g["count"])
    ax.errorbar(g.index, g["mean"], yerr=ci, marker="o", ms=8, lw=2.4, capsize=4, color=BLUE)
    for k, r in g.iterrows():
        ax.text(k, 1.3, f"n = {int(r['count'])}", ha="center", fontsize=9, color=GREY)
    ax.set_xticks(list(SIKLIK), [f"{v}\nkez/ay" for v in SIKLIK.values()])
    ax.set_ylabel("Alışkanlık ortalaması (1–7)"); ax.set_ylim(1, 7)
    ax.set_title("Sipariş sıklığı arttıkça alışkanlık artıyor")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)


def grafik_htmt(pls, path):
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    rel = pls.reliability.loc[list(BLOCKS)]
    x = np.arange(len(rel)); w = 0.27
    for i, (c, col, lab) in enumerate([("alpha", BLUE, "Cronbach α"), ("rho_c", GREEN, "Birleşik güv. ρc"),
                                        ("AVE", ORANGE, "AVE")]):
        ax[0].bar(x + (i - 1) * w, rel[c], w, color=col, label=lab)
    ax[0].axhline(0.7, ls="--", color=GREY, lw=1); ax[0].axhline(0.5, ls=":", color=GREY, lw=1)
    ax[0].set_xticks(x, [NAMES[k].replace(" ", "\n") for k in rel.index], fontsize=9)
    ax[0].set_ylim(0, 1.12); ax[0].legend(fontsize=9, loc="upper center", ncol=3); ax[0].set_title("Ölçüm modeli kalitesi")
    h = pls.htmt.loc[list(BLOCKS), list(BLOCKS)].to_numpy()
    im = ax[1].imshow(np.where(np.isnan(h), np.nan, h), cmap="Blues", vmin=0, vmax=0.85)
    for i in range(len(h)):
        for j in range(len(h)):
            if not np.isnan(h[i, j]):
                ax[1].text(j, i, f"{h[i, j]:.2f}", ha="center", va="center", fontsize=9,
                           color="white" if h[i, j] > 0.55 else "black")
    ax[1].set_xticks(range(len(h)), list(BLOCKS)); ax[1].set_yticks(range(len(h)), list(BLOCKS))
    ax[1].grid(False); ax[1].set_title("HTMT (eşik < .85)")
    fig.colorbar(im, ax=ax[1], shrink=0.8)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gercek", action="store_true", help="data/private/analiz_verisi.csv kullan")
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    main(a.gercek, a.n_boot)
