# ADR-0008: Test-environment execution boundary

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Amaç

Aşama 8, gerçek para veya canlı borsa yetkisi kullanmadan emir yaşam döngüsünü tekrar edilebilir biçimde doğrular.

## Karar

- Yürütme katmanı varsayılan olarak bellek içi test motorudur ve dış borsaya emir göndermez.
- Her emir kullanıcı/strateji dışından üretilen benzersiz `client_order_id` ile tanımlanır.
- Aynı kimlikle aynı emir tekrar gönderilirse idempotent olarak aynı kayıt döner; farklı parametreler reddedilir.
- Kısmi dolum, tam dolum ve iptal durumları açık bir durum makinesiyle izlenir.
- Kalan miktarı aşan dolum, iptal edilmiş emre dolum ve dolmuş emri iptal etme fail-closed reddedilir.
- Fiyat ve miktarlar `Decimal` ile taşınır.
- Bu aşama API anahtarı, testnet hesabı veya canlı sermaye gerektirmez.

## Sonuç

Bu sözleşme daha sonra gerçek testnet adaptörüne bağlanabilir; ancak dış bağlantı eklendiğinde risk motoru onayı, kimlik bilgisi izolasyonu ve mutabakat kapıları ayrıca zorunlu olacaktır. Canlı yürütme bu ADR ile etkinleştirilmez.
