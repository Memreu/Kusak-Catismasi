# Kuşak Çatışması: R ile doğrulayıcı faktör analizi (CFA) ve kovaryans tabanlı SEM
#
# Python'daki PLS-SEM sonuçlarını farklı bir yöntemle (lavaan, ML tahmini) sınar ve
# kuşaklar arası ölçme değişmezliğini test eder. Kuşak ortalamalarını karşılaştırmak
# anlamlıdır ancak ölçek iki grupta da aynı şeyi ölçüyorsa (en az metrik değişmezlik).
#
# Kullanım (repo kök dizininden):
#   Rscript analysis/R/cfa_sem.R            # sentetik veri
#   Rscript analysis/R/cfa_sem.R --gercek   # data/private/analiz_verisi.csv
#
# Gerekli paketler: lavaan, psych

suppressPackageStartupMessages({
  library(lavaan)
  library(psych)
})

args <- commandArgs(trailingOnly = TRUE)
gercek <- "--gercek" %in% args
src <- if (gercek) "data/private/analiz_verisi.csv" else "data/sentetik_veri.csv"
out_dir <- if (gercek) "results/R" else "results/sentetik/R"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

d <- read.csv(src, encoding = "UTF-8", stringsAsFactors = FALSE)
cat(sprintf("Veri: %s (n = %d)\n", src, nrow(d)))

bloklar <- list(
  PERF = c("PERF2", "PERF3", "PERF4"),
  CABA = c("CABA5", "CABA6", "CABA7"),
  DUYG = c("DUYG8", "DUYG9", "DUYG10"),
  FIY  = c("FIY11", "FIY12", "FIY13"),
  ALS  = c("ALS18", "ALS19", "ALS20", "ALS21"),
  SAD  = c("SAD15", "SAD16", "SAD17")
)

# 1) Güvenilirlik: Cronbach alfa (psych) ----------------------------------------
guv <- do.call(rbind, lapply(names(bloklar), function(b) {
  a <- suppressWarnings(psych::alpha(d[, bloklar[[b]]], warnings = FALSE)$total$raw_alpha)
  data.frame(yapi = b, madde = length(bloklar[[b]]), alfa = round(a, 3))
}))

# 2) Ölçüm modeli (CFA) --------------------------------------------------------
olcum <- paste(sprintf("%s =~ %s", names(bloklar),
                       sapply(bloklar, paste, collapse = " + ")), collapse = "\n")
cfa_fit <- cfa(olcum, data = d, estimator = "MLR")
d$kusak <- ifelse(d$kusak == "Z", "Z", "Diger")  # yerel ayardan bağımsız grup adları
uyum_ad <- c("chisq.scaled", "df", "pvalue.scaled", "cfi.robust", "tli.robust",
             "rmsea.robust", "srmr")
cfa_uyum <- fitMeasures(cfa_fit, uyum_ad)
# McDonald omega: CFA'nın standartlaştırılmış yüklerinden (sum λ)² / ((sum λ)² + sum θ)
ss <- standardizedSolution(cfa_fit)
guv$omega <- sapply(guv$yapi, function(b) {
  l <- ss$est.std[ss$op == "=~" & ss$lhs == b]
  round(sum(l)^2 / (sum(l)^2 + sum(1 - l^2)), 3)
})

# 3) Yapısal model (PLS-SEM ile aynı yollar) ----------------------------------
yapisal <- paste(olcum, "
  DUYG ~ a1*PERF + a2*CABA
  FIY  ~ a3*PERF + a4*CABA
  SAD  ~ b1*DUYG + b2*FIY + ALS
  perf_duyg_sad := a1*b1
  caba_duyg_sad := a2*b1
  perf_fiy_sad  := a3*b2
  caba_fiy_sad  := a4*b2", sep = "\n")
sem_fit <- sem(yapisal, data = d, estimator = "MLR")
sem_uyum <- fitMeasures(sem_fit, uyum_ad)
yollar <- subset(standardizedSolution(sem_fit), op %in% c("~", ":="),
                 select = c(lhs, op, rhs, label, est.std, se, pvalue, ci.lower, ci.upper))
r2 <- lavInspect(sem_fit, "r2")[c("DUYG", "FIY", "SAD")]

# 4) Kuşaklar arası ölçme değişmezliği -----------------------------------------
# Not: Daha küçük grupta (n≈107) gizil korelasyon matrisi pozitif tanımlı olmayabilir;
# lavaan bu durumda uyarı verir. Sonuçlar bu nedenle temkinli yorumlanmalıdır.
pd_uyari <- character(0)
yapilandirma <- withCallingHandlers(
  cfa(olcum, data = d, group = "kusak", estimator = "MLR"),
  warning = function(w) { pd_uyari <<- c(pd_uyari, conditionMessage(w)); invokeRestart("muffleWarning") })
metrik <- suppressWarnings(cfa(olcum, data = d, group = "kusak", estimator = "MLR", group.equal = "loadings"))
skaler <- suppressWarnings(cfa(olcum, data = d, group = "kusak", estimator = "MLR",
              group.equal = c("loadings", "intercepts")))
degismezlik <- do.call(rbind, lapply(list(yapilandirma = yapilandirma, metrik = metrik,
                                          skaler = skaler), function(m)
  as.data.frame(as.list(fitMeasures(m, c("chisq.scaled", "df", "cfi.robust", "rmsea.robust", "srmr"))))))
degismezlik$model <- rownames(degismezlik)
degismezlik$delta_cfi <- c(NA, diff(degismezlik$cfi.robust))
degismezlik$delta_rmsea <- c(NA, diff(degismezlik$rmsea.robust))

# 5) Çıktılar --------------------------------------------------------------------
fmt <- function(x) format(round(x, 3), nsmall = 3)
satirlar <- c(
  "# R sonuçları: CFA, kovaryans tabanlı SEM ve ölçme değişmezliği", "",
  sprintf("Veri: %s, n = %d. Tahmin yöntemi: MLR (robust ML).", if (gercek) "gerçek" else "sentetik", nrow(d)), "",
  "## Güvenilirlik", "", "| Yapı | Madde | Cronbach α | McDonald ω |", "|---|---:|---:|---:|",
  sprintf("| %s | %d | %s | %s |", guv$yapi, guv$madde, fmt(guv$alfa), fmt(guv$omega)), "",
  "## Model uyumu", "", "| Model | χ² (ölçekli) | sd | CFI | TLI | RMSEA | SRMR |", "|---|---:|---:|---:|---:|---:|---:|",
  sprintf("| CFA (ölçüm modeli) | %s | %d | %s | %s | %s | %s |", fmt(cfa_uyum["chisq.scaled"]), as.integer(cfa_uyum["df"]),
          fmt(cfa_uyum["cfi.robust"]), fmt(cfa_uyum["tli.robust"]), fmt(cfa_uyum["rmsea.robust"]), fmt(cfa_uyum["srmr"])),
  sprintf("| SEM (yapısal model) | %s | %d | %s | %s | %s | %s |", fmt(sem_uyum["chisq.scaled"]), as.integer(sem_uyum["df"]),
          fmt(sem_uyum["cfi.robust"]), fmt(sem_uyum["tli.robust"]), fmt(sem_uyum["rmsea.robust"]), fmt(sem_uyum["srmr"])),
  "", "Referans: CFI/TLI ≥ .90 kabul edilebilir, ≥ .95 iyi; RMSEA ≤ .08; SRMR ≤ .08.", "",
  "## Yapısal yollar (standartlaştırılmış)", "", "| Yol | β | SH | p | %95 GA |", "|---|---:|---:|---:|---|",
  sprintf("| %s | %s | %s | %s | [%s, %s] |",
          ifelse(yollar$op == "~", paste(yollar$rhs, "→", yollar$lhs), yollar$lhs),
          fmt(yollar$est.std), fmt(yollar$se), fmt(yollar$pvalue), fmt(yollar$ci.lower), fmt(yollar$ci.upper)),
  "", sprintf("R²: DUYG = %s, FIY = %s, SAD = %s", fmt(r2["DUYG"]), fmt(r2["FIY"]), fmt(r2["SAD"])), "",
  "## Kuşaklar arası ölçme değişmezliği", "", "| Model | χ² | sd | CFI | RMSEA | SRMR | ΔCFI | ΔRMSEA |", "|---|---:|---:|---:|---:|---:|---:|---:|",
  sprintf("| %s | %s | %d | %s | %s | %s | %s | %s |", degismezlik$model, fmt(degismezlik$chisq.scaled),
          as.integer(degismezlik$df), fmt(degismezlik$cfi.robust), fmt(degismezlik$rmsea.robust),
          fmt(degismezlik$srmr), ifelse(is.na(degismezlik$delta_cfi), "", fmt(degismezlik$delta_cfi)),
          ifelse(is.na(degismezlik$delta_rmsea), "", fmt(degismezlik$delta_rmsea))),
  "", "Ölçüt (Chen, 2007): ΔCFI ≥ −.010 ve ΔRMSEA ≤ .015 ise değişmezlik korunur.",
  if (length(pd_uyari)) "\n> ⚠️ lavaan uyarısı: Gruplardan birinde gizil değişken kovaryans matrisi pozitif tanımlı değil (küçük grup büyüklüğü / yüksek korelasyonlar). Değişmezlik sonuçlarını temkinli yorumlayın." else ""
)
writeLines(satirlar, file.path(out_dir, "sonuclar.md"), useBytes = TRUE)
cat(paste(satirlar, collapse = "\n"), "\n")
