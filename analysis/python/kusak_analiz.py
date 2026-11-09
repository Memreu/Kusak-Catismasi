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


def _bitir(fig, path=None) -> None:
    """Grafiği kaydet (path verilirse) veya notebook'ta göster."""
    fig.tight_layout()
    if path is None:
        plt.show()
    else:
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        plt.close(fig)


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

    # 10) Güç analizi -------------------------------------------------------------
    guc = guc_analizi(len(d), R["n_z"], R["n_diger"])
    md(guc, tab / "15_guc_analizi.md", "Güç analizi (α = .05, güç = .80)",
       "F testleri için Cohen (1988) etki büyüklükleri: f² = .02 küçük, .15 orta, .35 büyük; "
       "t-testi için d = .20 küçük, .50 orta. 'En küçük saptanabilir etki', mevcut örneklemle "
       "%80 güçle yakalanabilecek en küçük etki büyüklüğüdür.")
    R["guc"] = guc.round(3).to_dict(orient="records")

    # 11) Çok gruplu analiz (PLS-MGA, permütasyon testi) ---------------------------
    mga = pls_mga(d, model, n_perm=max(200, n_boot // 2))
    md(mga, tab / "16_pls_mga.md", "Çok gruplu PLS analizi: Z kuşağı vs diğer kuşaklar",
       f"Fark = Z − Diğer. p değerleri {max(200, n_boot // 2)} permütasyonla hesaplanmıştır "
       "(Chin ve Dibbern, 2010). Ölçme değişmezliği sınırda olduğu için (R çıktısı) farklar temkinli yorumlanmalıdır.")
    R["mga"] = mga.round(3).set_index("yol").to_dict(orient="index")

    # 12) Önem-performans haritası (IPMA) --------------------------------------------
    ipma = ipma_analizi(d, pls)
    md(ipma, tab / "17_ipma.md", "Önem-performans haritası (hedef: sadakat)",
       "Önem: sadakat üzerindeki standartlaştırılmış toplam etki. Performans: yapının 0–100 "
       "ölçeğine dönüştürülmüş ortalaması (PLS dış ağırlıklarıyla). Yüksek önem + düşük performans = öncelikli iyileştirme alanı.")
    R["ipma"] = ipma.round(3).set_index("yapı").to_dict(orient="index")

    (out / "sonuclar.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float),
                                       encoding="utf-8")

    # 10) Grafikler ---------------------------------------------------------------
    grafik_model(pls, boot, fig / "01_pls_model.png")
    grafik_kusak(d, t_kusak, fig / "02_kusak_karsilastirma.png")
    grafik_makas_eko(d, slopes, fig / "03_makas_ve_ekonomi.png")
    grafik_siklik(an, fig / "04_siklik_aliskanlik.png")
    grafik_htmt(pls, fig / "05_olcum_modeli.png")
    grafik_mga(mga, fig / "06_kusak_modelleri.png")
    grafik_ipma(ipma, fig / "07_onem_performans.png")
    print(f"Analiz tamamlandı ({R['veri']} veri, n={len(d)}) → {out.relative_to(ROOT)}")


# --------------------------------------------------------------------------- #
def grafik_model(pls, boot, path=None):
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
    _bitir(fig, path)


def grafik_kusak(d, t_kusak, path=None):
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
    _bitir(fig, path)


def grafik_makas_eko(d, slopes, path=None):
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
    _bitir(fig, path)


def grafik_siklik(an, path=None):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    g = an.groupby("siparis_sikligi").ALS.agg(["mean", "std", "count"])
    ci = 1.96 * g["std"] / np.sqrt(g["count"])
    ax.errorbar(g.index, g["mean"], yerr=ci, marker="o", ms=8, lw=2.4, capsize=4, color=BLUE)
    for k, r in g.iterrows():
        ax.text(k, 1.3, f"n = {int(r['count'])}", ha="center", fontsize=9, color=GREY)
    ax.set_xticks(list(SIKLIK), [f"{v}\nkez/ay" for v in SIKLIK.values()])
    ax.set_ylabel("Alışkanlık ortalaması (1–7)"); ax.set_ylim(1, 7)
    ax.set_title("Sipariş sıklığı arttıkça alışkanlık artıyor")
    _bitir(fig, path)


def grafik_htmt(pls, path=None):
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
    _bitir(fig, path)


# --------------------------------------------------------------------------- #
def _f_power(f2: float, u: int, n: int, alpha: float = 0.05) -> float:
    """Çoklu regresyon F testi için güç (Cohen: λ = f² · n)."""
    v = n - u - 1
    crit = stats.f.ppf(1 - alpha, u, v)
    return 1 - stats.ncf.cdf(crit, u, v, f2 * n)


def _t_power(dd: float, n1: int, n2: int, alpha: float = 0.05) -> float:
    df = n1 + n2 - 2
    nc = dd * np.sqrt(n1 * n2 / (n1 + n2))
    crit = stats.t.ppf(1 - alpha / 2, df)
    return 1 - stats.nct.cdf(crit, df, nc) + stats.nct.cdf(-crit, df, nc)


def guc_analizi(n: int, n1: int, n2: int) -> pd.DataFrame:
    from scipy.optimize import brentq

    rows = []
    for u, ad in [(3, "Sadakat ← duygusal değer + fiyat değeri + alışkanlık"),
                  (2, "Duygusal / fiyat değeri ← performans + çaba")]:
        gerekli = next(k for k in range(u + 3, 5000) if _f_power(0.15, u, k) >= 0.80)
        gerekli_kucuk = next(k for k in range(u + 3, 5000) if _f_power(0.02, u, k) >= 0.80)
        mde = brentq(lambda f: _f_power(f, u, n) - 0.80, 1e-4, 0.5)
        rows.append({"test": f"Regresyon / PLS yolu ({u} yordayıcı): {ad}",
                     "orta etki için gereken n": gerekli, "küçük etki için gereken n": gerekli_kucuk,
                     "mevcut n": n, "en küçük saptanabilir etki": f"f² = {mde:.3f}",
                     "orta etkiyi yakalama gücü": _f_power(0.15, u, n)})
    gerekli_t = next(k for k in range(4, 5000) if _t_power(0.5, k, k) >= 0.80)
    mde_t = brentq(lambda x: _t_power(x, n1, n2) - 0.80, 1e-3, 1.5)
    rows.append({"test": f"Kuşak karşılaştırması (t-testi, {n1} vs {n2})",
                 "orta etki için gereken n": 2 * gerekli_t,
                 "küçük etki için gereken n": 2 * next(k for k in range(4, 5000) if _t_power(0.2, k, k) >= 0.80),
                 "mevcut n": n1 + n2, "en küçük saptanabilir etki": f"d = {mde_t:.3f}",
                 "orta etkiyi yakalama gücü": _t_power(0.5, n1, n2)})
    return pd.DataFrame(rows)


def pls_mga(d: pd.DataFrame, model: PLSModel, n_perm: int = 1000, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    def coefs(sub):
        p, r2 = model._paths_r2(model._estimate(sub)[2])
        return pd.Series({f"{a} → {b}": c for a, b, c in p.itertuples(index=False)}), r2

    g = d.kusak.to_numpy()
    cz, r2z = coefs(d[g == "Z"]); cd, r2d = coefs(d[g == "Diğer"])
    diff = cz - cd
    perm = []
    for _ in range(n_perm):
        sh = rng.permutation(g)
        try:
            a, _ = coefs(d[sh == "Z"]); b, _ = coefs(d[sh == "Diğer"])
            perm.append(a - b)
        except np.linalg.LinAlgError:
            continue
    perm = pd.DataFrame(perm)
    p = {k: (np.abs(perm[k]) >= abs(diff[k])).mean() for k in diff.index}
    out = pd.DataFrame({"yol": diff.index, "Z kuşağı β": cz.values, "Diğer kuşaklar β": cd.values,
                        "fark": diff.values, "p (permütasyon)": [p[k] for k in diff.index]})
    r2 = pd.DataFrame({"yol": [f"R² ({NAMES[k]})" for k in r2z.index], "Z kuşağı β": r2z.values,
                       "Diğer kuşaklar β": r2d.values, "fark": (r2z - r2d).values,
                       "p (permütasyon)": np.nan})
    return pd.concat([out, r2], ignore_index=True)


def ipma_analizi(d: pd.DataFrame, pls) -> pd.DataFrame:
    p = {(a, b): c for a, b, c in pls.paths.itertuples(index=False)}
    toplam = {
        "PERF": p[("PERF", "DUYG")] * p[("DUYG", "SAD")] + p[("PERF", "FIY")] * p[("FIY", "SAD")],
        "CABA": p[("CABA", "DUYG")] * p[("DUYG", "SAD")] + p[("CABA", "FIY")] * p[("FIY", "SAD")],
        "DUYG": p[("DUYG", "SAD")], "FIY": p[("FIY", "SAD")], "ALS": p[("ALS", "SAD")],
    }
    rows = []
    for lv, imp in toplam.items():
        w = pls.weights[lv] / pls.weights[lv].sum()
        x = (d[BLOCKS[lv]] - 1) / 6 * 100
        rows.append({"yapı": NAMES[lv], "kod": lv, "önem (toplam etki)": imp,
                     "performans (0-100)": float((x * w.values).sum(axis=1).mean())})
    return pd.DataFrame(rows)


def grafik_mga(mga, path=None):
    m = mga[~mga.yol.str.startswith("R²")].copy()
    fig, ax = plt.subplots(figsize=(11, 4.6))
    y = np.arange(len(m))[::-1]; h = 0.38
    ax.barh(y + h / 2, m["Z kuşağı β"], h, color=ORANGE, label="Z kuşağı")
    ax.barh(y - h / 2, m["Diğer kuşaklar β"], h, color=BLUE, label="Diğer kuşaklar")
    for yi, r in zip(y, m.itertuples()):
        top = max(r._2, r._3, 0)
        renk = RED if r._5 < 0.05 else GREY
        ax.text(top + 0.02, yi, f"fark {r.fark:+.2f} · {p_lbl(r._5)}", va="center", fontsize=9, color=renk)
    ax.set_yticks(y, [r.replace("PERF", "Performans").replace("CABA", "Çaba").replace("DUYG", "Duygusal d.")
                      .replace("FIY", "Fiyat d.").replace("ALS", "Alışkanlık").replace("SAD", "Sadakat")
                      for r in m.yol])
    ax.axvline(0, color="black", lw=0.8); ax.set_xlim(min(-0.1, m[["Z kuşağı β", "Diğer kuşaklar β"]].min().min() - 0.05), 1.0)
    ax.set_xlabel("Standartlaştırılmış yol katsayısı"); ax.legend(loc="lower right")
    ax.set_title("Model kuşaklarda aynı mı işliyor? (PLS çok gruplu analiz)")
    _bitir(fig, path)


def grafik_ipma(ipma, path=None):
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    xm, ym = ipma["önem (toplam etki)"].mean(), ipma["performans (0-100)"].mean()
    ax.axvline(xm, color=GREY, ls="--", lw=1); ax.axhline(ym, color=GREY, ls="--", lw=1)
    for r in ipma.itertuples():
        imp, perf = r._3, r._4
        oncelik = imp > xm and perf < ym
        ax.scatter(imp, perf, s=260, color=RED if oncelik else BLUE, zorder=3, edgecolor="white", lw=2)
        ax.annotate(r.yapı, (imp, perf), xytext={"PERF": (-10, -20), "CABA": (10, 6)}.get(r.kod, (10, 6)),
                    ha="right" if r.kod == "PERF" else "left", textcoords="offset points", fontsize=10,
                    fontweight="bold" if oncelik else "normal")
    ax.text(0.98, 0.03, "ÖNCELİKLİ ALAN\nyüksek önem · düşük performans", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9, color=RED)
    ax.set_xlabel("Önem: sadakat üzerindeki toplam etki"); ax.set_ylabel("Performans (0–100)")
    ax.set_xlim(0, ipma["önem (toplam etki)"].max() * 1.3); ax.set_ylim(20, 90)
    ax.set_title("Önem-performans haritası: sadakat için nereye yatırım yapılmalı?")
    _bitir(fig, path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gercek", action="store_true", help="data/private/analiz_verisi.csv kullan")
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    plt.switch_backend("Agg")
    main(a.gercek, a.n_boot)
