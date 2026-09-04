# ADR-0009: ML araştırmasında OOS doğrulama sınırı

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Bağlam

ML deneyleri kronolojik piyasa verisinde kolayca look-ahead, sınır sızıntısı ve aşırı uyum
üretebilir. Aşama 9'un amacı model seçmekten önce deney protokolünü güvenli ve tekrar
edilebilir hale getirmektir.

## Karar

- Veri rastgele karıştırılmaz; train/validation/test kronolojik ayrılır.
- Bölme sınırlarında yapılandırılabilir purge boşluğu bırakılır.
- OOS tahminleri sıkı artan zaman damgası taşır.
- İlk metrik seti accuracy, precision, recall ve Brier score'dur.
- Tahmin skoru `[0, 1]` aralığında ve sonlu olmak zorundadır.
- ML çıktısı işlem emri değildir; risk motorunu veya yürütme katmanını çağırmaz.
- Aşama 9 çalışma zamanı bağımlılığı eklemez; model kütüphaneleri ancak ayrıca gerekçelendirilirse eklenir.

## Sonuç

Bu sınır, gelecekte kurulacak modellerin aynı veri ayrımı ve OOS değerlendirme kurallarına
uymasını sağlar. Bir modelin iyi metrik üretmesi canlı kullanıma geçiş anlamına gelmez.
