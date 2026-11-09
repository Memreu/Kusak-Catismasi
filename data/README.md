# Veri

## Neden gerçek veri burada yok?

Ankette katılımcılara verilerin **yalnızca bilimsel amaçla kullanılacağı ve kimlik bilgilerinin gizli tutulacağı** taahhüt edildi. Ham yanıt tablosu e-posta adresi, yaş ve şehir gibi kişisel bilgiler içerdiği için repoda paylaşılmaz. `.gitignore`, `data/private/` klasörünü ve tüm `.sav`, `.xlsx`, `.spv` dosyalarını GitHub'a gönderilmekten korur.

## `sentetik_veri.csv`

Kodun herkes tarafından çalıştırılabilmesi için gerçek veriden **Gauss kopula** yöntemiyle üretilmiş 236 satırlık sentetik bir veri seti ([`analysis/python/sentetik_veri.py`](../analysis/python/sentetik_veri.py)):

- Her değişkenin dağılımı ve değişkenler arası korelasyonlar yaklaşık olarak korunur (madde korelasyonlarındaki ortalama mutlak fark: 0,06).
- Hiçbir satır gerçek bir katılımcıya karşılık gelmez; betik, üretilen 21 maddelik yanıt örüntülerinin hiçbirinin gerçek veride birebir bulunmadığını kontrol eder.
- Yaş ve şehir gibi tanımlayıcı bilgiler yer almaz (şehir yalnızca "Büyükşehir / Diğer" olarak).

> ⚠️ Sentetik veriyle elde edilen sonuçlar **araştırma bulgusu değildir**; yalnızca kodun çalıştığını göstermek içindir. Gerçek sonuçlar [`results/`](../results) klasöründedir.

## Değişken sözlüğü

| Değişken | Açıklama | Değerler |
|---|---|---|
| `kusak` | Kuşak | Z (1999–2012 doğumlu), Diğer (1999 öncesi) |
| `cinsiyet` | Cinsiyet | Kadın, Erkek |
| `egitim` | Eğitim durumu | 1 Lise ve altı · 2 Üniversite öğrencisi · 3 Ön lisans · 4 Lisans · 5 Yüksek lisans · 6 Doktora |
| `meslek` | Meslek | 1 Öğrenci · 2 Tam zamanlı · 3 Yarı zamanlı · 4 Serbest meslek · 5 Emekli · 6 İşsiz |
| `eko_durum` | Ekonomik durum algısı | Kötü, Orta, İyi |
| `sehir_grup` | Yaşanılan şehir | Büyükşehir, Diğer |
| `uygulama` | En sık kullanılan uygulama | 1 Yemeksepeti · 2 Getir · 3 Trendyol · 4 TıklaGelsin · 5 Diğer |
| `uygulama_sayisi` | Kullanılan uygulama sayısı | 1, 2, 3, 4+ |
| `siparis_sikligi` | Aylık sipariş sıklığı | 1: 0-2 · 2: 3-5 · 3: 6-8 · 4: 9-11 · 5: 12+ |
| `SIN1` | Kampanya/indirim belirleyiciliği | 1–7 Likert |
| `PERF2–4` | Performans beklentisi | 1–7 Likert |
| `CABA5–7` | Çaba beklentisi | 1–7 Likert |
| `DUYG8–10` | Duygusal değer | 1–7 Likert |
| `FIY11–13` | Fiyat değeri | 1–7 Likert |
| `KONT14` | Dikkat kontrol sorusu (doğru yanıt: 2) | 2 |
| `SAD15–17` | Sadakat | 1–7 Likert |
| `ALS18–21` | Alışkanlık | 1–7 Likert |

Gerçek veride ayrıca `yas_18_alti` (araştırma evreni dışındaki yanıtları işaretleyen mantıksal değişken) bulunur; sentetik veriye dahil edilmez.

## Ham veriden analiz verisine (yalnızca araştırmacılar için)

```bash
python analysis/python/veri_hazirla.py --sav Genel_Spss.sav --xlsx "Yanıt Tablosu.xlsx"
# → data/private/analiz_verisi.csv (git'e eklenmez)
```

Bu adım, SPSS dosyasında aynı kodla kaydedilmiş "3-5" ve "9-11 Kez" sipariş sıklığı yanıtlarını yanıt tablosuyla ayrıştırır.
