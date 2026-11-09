# R sonuçları: CFA, kovaryans tabanlı SEM ve ölçme değişmezliği

Veri: gerçek, n = 236. Tahmin yöntemi: MLR (robust ML).

## Güvenilirlik

| Yapı | Madde | Cronbach α | McDonald ω |
|---|---:|---:|---:|
| PERF | 3 | 0.730 | 0.729 |
| CABA | 3 | 0.809 | 0.814 |
| DUYG | 3 | 0.681 | 0.664 |
| FIY | 3 | 0.663 | 0.692 |
| ALS | 4 | 0.799 | 0.813 |
| SAD | 3 | 0.627 | 0.639 |

## Model uyumu

| Model | χ² (ölçekli) | sd | CFI | TLI | RMSEA | SRMR |
|---|---:|---:|---:|---:|---:|---:|
| CFA (ölçüm modeli) | 331.621 | 137 | 0.848 | 0.810 | 0.087 | 0.097 |
| SEM (yapısal model) | 349.465 | 142 | 0.837 | 0.804 | 0.088 | 0.109 |

Referans: CFI/TLI ≥ .90 kabul edilebilir, ≥ .95 iyi; RMSEA ≤ .08; SRMR ≤ .08.

## Yapısal yollar (standartlaştırılmış)

| Yol | β | SH | p | %95 GA |
|---|---:|---:|---:|---|
| PERF → DUYG | 0.429 | 0.110 | 0.000 | [ 0.213, 0.644] |
| CABA → DUYG | 0.599 | 0.110 | 0.000 | [ 0.382, 0.815] |
| PERF → FIY | 0.205 | 0.127 | 0.105 | [-0.043, 0.453] |
| CABA → FIY | 0.203 | 0.138 | 0.140 | [-0.067, 0.473] |
| DUYG → SAD | 0.592 | 0.092 | 0.000 | [ 0.412, 0.773] |
| FIY → SAD | 0.270 | 0.100 | 0.007 | [ 0.073, 0.466] |
| ALS → SAD | 0.443 | 0.106 | 0.000 | [ 0.236, 0.651] |
| perf_duyg_sad | 0.254 | 0.077 | 0.001 | [ 0.103, 0.405] |
| caba_duyg_sad | 0.355 | 0.084 | 0.000 | [ 0.190, 0.519] |
| perf_fiy_sad | 0.055 | 0.038 | 0.147 | [-0.019, 0.130] |
| caba_fiy_sad | 0.055 | 0.045 | 0.221 | [-0.033, 0.143] |

R²: DUYG = 0.808, FIY = 0.127, SAD = 0.763

## Kuşaklar arası ölçme değişmezliği

| Model | χ² | sd | CFI | RMSEA | SRMR | ΔCFI | ΔRMSEA |
|---|---:|---:|---:|---:|---:|---:|---:|
| yapilandirma | 528.554 | 274 | 0.824 | 0.095 | 0.105 |  |  |
| metrik | 554.878 | 287 | 0.813 | 0.096 | 0.107 | -0.012 | 0.001 |
| skaler | 584.405 | 300 | 0.803 | 0.096 | 0.108 | -0.010 | 0.000 |

Ölçüt (Chen, 2007): ΔCFI ≥ −.010 ve ΔRMSEA ≤ .015 ise değişmezlik korunur.

> ⚠️ lavaan uyarısı: Gruplardan birinde gizil değişken kovaryans matrisi pozitif tanımlı değil (küçük grup büyüklüğü / yüksek korelasyonlar). Değişmezlik sonuçlarını temkinli yorumlayın.
