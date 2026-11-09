# Ders raporu ile yeniden analizin karşılaştırılması

Proje raporundaki (SPSS ve SmartPLS ile hazırlanmış) sonuçlar, aynı SPSS veri dosyasından (`Genel_Spss.sav`, n = 236) Python ve R ile bağımsız olarak yeniden hesaplanmıştır. Sonuçların büyük çoğunluğu birebir örtüşüyor; aşağıdaki tablo **farklılık gösteren** noktaları ve nedenlerini listeler. Bu repodaki README ve tablolar yeniden hesaplanan değerleri kullanır.

## Birebir doğrulanan sonuçlar

- Tüm ölçeklerin Cronbach α değerleri (0,627–0,809) ve madde VIF değerleri
- H1–H3 regresyon katsayıları (β = 0,288 / 0,407 / 0,146 / 0,193 / 0,320 / 0,310)
- Kuşak t-testleri: alışkanlık (3,50 vs 4,00; p = ,009) ve sadakat (p = ,157)
- Cinsiyet t-testlerinin anlamlı çıkan sonuçları (çaba p = ,011; duygusal değer p = ,017; alışkanlık p = ,044)
- H5a/H5b moderasyonları (p = ,622 / ,620), H6b moderasyonu (p = ,029)
- Ekonomik algı gruplarında duygusal değer → sadakat eğimleri (β = 0,284 / 0,544 / 0,330)
- Aracılık analizi (c = 0,340; c' = 0,175 / 0,255; dolaylı etki = 0,165 / 0,085)
- Kuşak × cinsiyet etkileşimi (F = 3,525; p = ,062)
- Ki-kare: kuşak × uygulama (p = ,210), kuşak × indirim (p = ,099), şehir × uygulama (p = ,492)
- PLS-SEM f² değerleri (çaba → duygusal değer 0,294; alışkanlık → sadakat 0,252)

## Farklılık gösteren noktalar

| Konu | Raporda | Yeniden hesaplanan | Açıklama |
|---|---|---|---|
| Örneklem büyüklüğü | 239 (Z: 130, diğer: 109) | **236** (Z: 129, diğer: 107) | SPSS dosyasında 236 geçerli satır var; raporun bazı tabloları da N = 236 kullanıyor |
| Duygusal değer regresyonu R² | 0,683 | **0,343** | β değerleri aynı; R² korelasyonlarla tutarlı değil |
| Fiyat değeri regresyonu R² | 0,125 | **0,081** | β değerleri aynı |
| PLS-SEM R² (sadakat / duygusal / fiyat) | 0,634 / 0,683 / 0,125 | **0,431 / 0,411 / 0,085** | Raporun f² değerleri, yeniden hesaplanan R² değerleriyle tutarlı |
| Fornell-Larcker tablosunda alışkanlık satırı | 0,52 / 0,43 / 0,47 / 0,52 | **0,22 / 0,28 / 0,16 / 0,07** (DUYG / FIY / PERF / CABA) | Ayırt edici geçerlilik sonucu değişmiyor (√AVE yine daha büyük) |
| Sipariş sıklığı değişkeni | 4 grup; N = 104'lük grup "9-11 Kez" olarak etiketli | 5 grup | SPSS'te "3-5 Kez" ve "9-11 Kez" aynı koda (4) birleşmiş; yanıt tablosuyla 231 satırda düzeltildi |
| Kuşak × sipariş sıklığı χ² | χ²(4) = 9,575; p = ,048 | **χ²(4) = 9,377; p = ,052** | Düzeltilmiş kodlamayla fark sınırda, .05 düzeyinde anlamlı değil |
| Alışkanlık ~ sipariş sıklığı ANOVA | F(3, 232) = 16,12 | **F(4, 226) = 14,72; p < ,001; η² = 0,21** | Sonuç aynı: sıklık arttıkça alışkanlık artıyor |
| Cinsiyet t-testleri (fark olmayanlar) | Fiyat t = 0,36, p = ,716; sadakat p = ,214; performans p = ,376 | Fiyat t = 1,16, p = ,249; sadakat p = ,767; performans p = ,456 | Sonuç aynı (fark yok); bazı grup ortalamaları da raporda farklı |
| H6a: Fiyat değeri × ekonomik algı | p = ,411, **red** | **F(2, 230) = 5,88; p = ,003** | Moderasyon anlamlı. Fiyat değerinin sadakate etkisi iyi ekonomik algıda en zayıf (β = 0,24), orta ve kötü algıda güçlü (β = 0,58 / 0,49). Raporun tartışma bölümündeki "p = ,003" ifadesiyle uyumlu |
| H6b'nin yorumu | "İyi ekonomik algı güçlendirir" | En güçlü etki **orta** algıda (β = 0,54); iyi algıda 0,33 | Moderasyon anlamlı ama ilişki doğrusal bir "refah arttıkça güçlenir" deseni göstermiyor |
| Kuşak × cinsiyet hücre ortalamaları | Z: K 5,12 / E 4,68; Diğer: K 4,87 / E 5,21 | Z: K 4,97 / E 4,73; Diğer: K 4,90 / E 5,16 | Makas deseni (çizgilerin kesişmesi) korunuyor |
| Kontrol sorusu adı | KON21 | KONT14 | Ankette kontrol sorusu 14. madde |

## Raporda olmayan ek bulgular

- **Z kuşağı yalnızca alışkanlıkta değil, duygusal değer (p = ,009) ve fiyat değeri (p = ,027) algısında da diğer kuşaklardan anlamlı derecede düşük.** Performans ve çaba beklentisinde fark yok.
- **18 yaş altı yanıtlar:** Yanıt tablosuyla eşleştirmede, son veri setindeki 10 yanıtın 18 yaş altı katılımcılara ait olduğu görüldü (araştırma evreni 18+). Bu yanıtlar çıkarıldığında kuşak farkları anlamlı kalıyor (alışkanlık p = ,021; duygusal değer p = ,018; fiyat değeri p = ,038).
- **Kovaryans tabanlı SEM (R, lavaan):** Model uyumu sınırda (CFI = 0,85, RMSEA = 0,087, SRMR = 0,097). Yolların yönü PLS-SEM ile aynı; ancak performans/çaba → fiyat değeri yolları CB-SEM'de anlamlı değil.
- **Ölçme değişmezliği:** Metrik değişmezlikte ΔCFI = −0,012 ile eşiğin çok az dışında; kuşak ortalamalarının karşılaştırılması temkinli yorumlanmalı.
