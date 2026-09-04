# ADR-0005: On-chain araştırma rejimi

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Amaç

Aşama 5, MVRV, SOPR, Puell Multiple ve NVT verilerini doğrudan al-sat kuralına
dönüştürmeden, point-in-time güvenli bir araştırma rejimi katmanı oluşturur.

## Karar

- Ham metrik değerleri sabit piyasa eşikleriyle "doğru sinyal" kabul edilmez.
- Her gözlem, yalnızca geçmiş veriden hesaplandığı varsayılan 0–1 tarihsel yüzdelikle
  birlikte taşınır; yüzdeliğin üretim yöntemi veri sağlayıcısı adaptörünün sorumluluğudur.
- `available_at_ms`, gerçek yayın/kullanılabilirlik zamanını temsil eder. Karar anından
  sonra yayımlanan veri rejim hesabına giremez.
- Eski veri `max_age_ms` sınırını aşarsa kullanılamaz ve yeterli güncel metrik yoksa
  motor `unknown` döner.
- İlk rejim motoru en az üç metrikte yüzdelik uzlaşısı arar: düşük uzlaşı
  `underheated`, yüksek uzlaşı `overheated`, aksi durum `neutral` olarak adlandırılır.
- Bu adlar betimleyici araştırma etiketleridir; `long`, `flat`, emir veya kâr beklentisi
  anlamına gelmez.
- Puell Multiple yalnızca BTC için kabul edilir; diğer varlıklara genellenmez.

## Bilimsel sınır

Bu katman E-002, E-003 ve E-004 hipotezlerini doğrulanmış kabul etmez. Metriklerin
öngörü gücü ancak kronolojik out-of-sample, maliyet duyarlı ve çoklu test düzeltmeli
deneylerden sonra değerlendirilebilir.

## Güvenlik

Bu bileşen API anahtarı gerektirmez, borsaya bağlanmaz ve gerçek para ile emir göndermez.
