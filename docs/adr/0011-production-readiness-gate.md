# ADR-0011: Paper-to-production manuel inceleme kapısı

- Durum: Kabul edildi
- Tarih: 2026-09-05

## Bağlam

Roadmap'in son aşaması, paper/test ortamından production değerlendirmesine geçmeden önce
teknik kanıtların eksiksiz olmasını sağlamalıdır. Otomatik bir test sonucunun gerçek para
ile işlemi doğrudan etkinleştirmesi güven sınırını ihlal eder.

## Karar

Aşağıdaki kanıtların tamamı zorunludur:

1. Paper çalışma kanıtı tamamlandı.
2. Stres testleri geçti.
3. Test-environment yürütmesi geçti.
4. CI kalite kapıları yeşil.
5. Mutabakat doğrulandı.
6. İzleme sağlıklı.
7. Risk limitleri açıkça yapılandırıldı.
8. Kill-switch test edildi.
9. Secret/API anahtarı politikası doğrulandı.
10. Para çekme yetkilerinin kapalı olduğu doğrulandı.
11. Geri dönüş/rollback planı belgelendi.

Eksik veya başarısız tek bir kanıt sonucu `not_ready` yapar. Tüm teknik kanıtlar geçse
bile otomasyonun ulaşabileceği en ileri durum `ready_for_manual_review` olur.

`readiness_payload()` her durumda `live_trading_enabled: false` üretir. Bu aşama API
anahtarı istemez, borsaya bağlanmaz, gerçek emir göndermez ve `Settings` içindeki canlı
mod kilidini değiştirmez.

## Sonuç

Production/live aktivasyonu bu proje otomasyonunun çıktısı değildir. Ayrı insan güvenlik
incelemesi, dış ortam yapılandırması ve mevcut çoklu canlı-mod kilitleri korunmalıdır.
