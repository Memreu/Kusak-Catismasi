"""Bağımlılıksız (yalnızca numpy/pandas) PLS-SEM uygulaması.

SmartPLS'teki varsayılan ayarları izler: yansıtıcı ölçüm (Mode A), yol ağırlıklandırma
şeması, standartlaştırılmış göstergeler. Bootstrap ile yol katsayıları, dolaylı etkiler ve
güven aralıkları hesaplanır.

Örnek:
    model = PLSModel(
        blocks={"PERF": ["PERF2", "PERF3", "PERF4"], ...},
        paths=[("PERF", "DUYG"), ("DUYG", "SAD"), ...],
    )
    res = model.fit(df)
    boot = model.bootstrap(df, n_boot=2000)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class PLSResult:
    scores: pd.DataFrame
    weights: pd.Series
    loadings: pd.Series
    paths: pd.DataFrame          # kaynak, hedef, katsayı
    r2: pd.Series
    f2: pd.DataFrame
    reliability: pd.DataFrame    # alpha, rho_c, AVE
    fornell_larcker: pd.DataFrame
    htmt: pd.DataFrame
    outer_vif: pd.Series
    iterations: int


def _std(a: np.ndarray) -> np.ndarray:
    return (a - a.mean(0)) / a.std(0, ddof=0)


def _ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, float]:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    r2 = 1 - resid.var() / y.var()
    return beta, r2


def cronbach_alpha(X: np.ndarray) -> float:
    k = X.shape[1]
    return k / (k - 1) * (1 - X.var(0, ddof=1).sum() / X.sum(1).var(ddof=1))


@dataclass
class PLSModel:
    blocks: dict[str, list[str]]
    paths: list[tuple[str, str]]
    max_iter: int = 300
    tol: float = 1e-7
    lvs: list[str] = field(init=False)

    def __post_init__(self):
        self.lvs = list(self.blocks)
        self.endog = sorted({t for _, t in self.paths}, key=self.lvs.index)

    def _preds(self, lv: str) -> list[str]:
        return [s for s, t in self.paths if t == lv]

    # ------------------------------------------------------------------ #
    def _estimate(self, X: pd.DataFrame):
        Xb = {lv: _std(X[cols].to_numpy(float)) for lv, cols in self.blocks.items()}
        w = {lv: np.ones(len(cols)) for lv, cols in self.blocks.items()}
        n = len(X)

        def lv_scores(w):
            return {lv: _std(Xb[lv] @ w[lv]) for lv in self.lvs}

        for it in range(1, self.max_iter + 1):
            Y = lv_scores(w)
            Z = {}
            for j in self.lvs:
                inner = np.zeros(n)
                preds = self._preds(j)
                if preds:  # öncüller: j'nin öncüllerine regresyon katsayıları
                    b, _ = _ols(Y[j], np.column_stack([Y[p] for p in preds]))
                    inner += np.column_stack([Y[p] for p in preds]) @ b
                for s, t in self.paths:  # ardıllar: korelasyon
                    if s == j:
                        inner += np.corrcoef(Y[j], Y[t])[0, 1] * Y[t]
                Z[j] = _std(inner)
            w_new = {}
            for j in self.lvs:  # Mode A
                wj = Xb[j].T @ Z[j] / n
                wj = wj / (Xb[j] @ wj).std(ddof=0)
                w_new[j] = wj
            delta = max(np.abs(w_new[j] - w[j]).max() for j in self.lvs)
            w = w_new
            if delta < self.tol:
                break
        return Xb, w, lv_scores(w), it

    def _paths_r2(self, Y: dict[str, np.ndarray]):
        rows, r2 = [], {}
        for t in self.endog:
            preds = self._preds(t)
            b, r2[t] = _ols(Y[t], np.column_stack([Y[p] for p in preds]))
            rows += [(p, t, float(c)) for p, c in zip(preds, b)]
        return pd.DataFrame(rows, columns=["kaynak", "hedef", "katsayi"]), pd.Series(r2)

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame) -> PLSResult:
        Xb, w, Y, it = self._estimate(X)
        paths, r2 = self._paths_r2(Y)

        weights, loadings = {}, {}
        for lv, cols in self.blocks.items():
            for c, wi, xi in zip(cols, w[lv], Xb[lv].T):
                weights[(lv, c)] = wi
                loadings[(lv, c)] = np.corrcoef(xi, Y[lv])[0, 1]
        loadings = pd.Series(loadings)

        # f²: hedefin R²'si, kaynak modelden çıkarıldığında ne kadar düşüyor?
        f2 = []
        for s, t in self.paths:
            others = [p for p in self._preds(t) if p != s]
            r2_ex = _ols(Y[t], np.column_stack([Y[p] for p in others]))[1] if others else 0.0
            f2.append((s, t, (r2[t] - r2_ex) / (1 - r2[t])))
        f2 = pd.DataFrame(f2, columns=["kaynak", "hedef", "f2"])

        rel = {}
        for lv, cols in self.blocks.items():
            l = loadings[lv].to_numpy()
            rel[lv] = {
                "alpha": cronbach_alpha(X[cols].to_numpy(float)),
                "rho_c": l.sum() ** 2 / (l.sum() ** 2 + (1 - l ** 2).sum()),
                "AVE": (l ** 2).mean(),
            }
        rel = pd.DataFrame(rel).T

        S = pd.DataFrame(Y)
        fl = S.corr()
        for lv in self.lvs:
            fl.loc[lv, lv] = np.sqrt(rel.loc[lv, "AVE"])

        # HTMT (Henseler vd., 2015)
        R = X[[c for cols in self.blocks.values() for c in cols]].corr().abs()
        htmt = pd.DataFrame(np.nan, index=self.lvs, columns=self.lvs)
        for i, a in enumerate(self.lvs):
            for b in self.lvs[:i]:
                A, B = self.blocks[a], self.blocks[b]
                het = R.loc[A, B].to_numpy().mean()
                mono = lambda C: R.loc[C, C].to_numpy()[np.triu_indices(len(C), 1)].mean()
                htmt.loc[a, b] = het / np.sqrt(mono(A) * mono(B))

        vif = {}
        for lv, cols in self.blocks.items():
            Z = _std(X[cols].to_numpy(float))
            for k, c in enumerate(cols):
                others = np.delete(Z, k, axis=1)
                vif[c] = 1 / (1 - _ols(Z[:, k], others)[1])

        return PLSResult(S, pd.Series(weights), loadings, paths, r2, f2, rel, fl,
                         htmt, pd.Series(vif), it)

    # ------------------------------------------------------------------ #
    def bootstrap(self, X: pd.DataFrame, n_boot: int = 2000, seed: int = 42,
                  indirect: list[tuple[str, ...]] | None = None) -> pd.DataFrame:
        """Yol katsayıları (ve istenirse dolaylı etkiler) için bootstrap özeti."""
        rng = np.random.default_rng(seed)
        base_paths, _ = self._paths_r2(self._estimate(X)[2])
        est = {f"{s} → {t}": c for s, t, c in base_paths.itertuples(index=False)}
        indirect = indirect or []

        def ind(paths_df, chain):
            p = 1.0
            for a, b in zip(chain, chain[1:]):
                p *= paths_df.query("kaynak == @a and hedef == @b")["katsayi"].iloc[0]
            return p

        for ch in indirect:
            est[" → ".join(ch)] = ind(base_paths, ch)

        draws = {k: [] for k in est}
        n = len(X)
        for _ in range(n_boot):
            sample = X.iloc[rng.integers(0, n, n)].reset_index(drop=True)
            try:
                p, _ = self._paths_r2(self._estimate(sample)[2])
            except np.linalg.LinAlgError:
                continue
            for s, t, c in p.itertuples(index=False):
                draws[f"{s} → {t}"].append(c)
            for ch in indirect:
                draws[" → ".join(ch)].append(ind(p, ch))

        rows = []
        for k, v in draws.items():
            v = np.asarray(v)
            se = v.std(ddof=1)
            t = est[k] / se
            rows.append({
                "yol": k, "katsayi": est[k], "std_hata": se, "t": t,
                "p": 2 * stats.t.sf(abs(t), df=n - 1),
                "ga_alt": np.percentile(v, 2.5), "ga_ust": np.percentile(v, 97.5),
            })
        return pd.DataFrame(rows)
