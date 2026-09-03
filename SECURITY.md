# Güvenlik politikası

## API anahtarı kuralları

- Anahtarlarda para çekme yetkisi kesinlikle açılmamalıdır.
- Yalnızca gerekli spot işlem ve okuma izinleri verilmelidir.
- Borsa destekliyorsa IP izin listesi kullanılmalıdır.
- Anahtarlar Git, ekran görüntüsü, log, hata mesajı veya test fixture'ına yazılmamalıdır.
- Üretim sırları ortam değişkeni yerine mümkün olduğunda bir secret yöneticisinden
  kısa ömürlü olarak alınmalıdır.
- Testnet ve canlı ortam anahtarları birbirinden tamamen ayrılmalıdır.

## Canlı işlem kilidi

`live` modu tek bir yanlış ayarla açılamaz. Uygulama aşağıdakilerin tamamını ister:

1. `AL_KRIPTO_TRADING_MODE=live`
2. `AL_KRIPTO_ENABLE_LIVE=true`
3. `AL_KRIPTO_LIVE_ACK=I_UNDERSTAND_LIVE_TRADING_RISK`
4. API anahtarı ve API sırrı

Bu kontroller risk motorunun, borsa izinlerinin veya manuel dağıtım onayının
yerine geçmez.

## Güvenlik açığı bildirme

Anahtar, kişisel veri veya istismar ayrıntısı içeren sorunlar herkese açık issue
olarak paylaşılmamalıdır. Repo sahibiyle özel kanal veya GitHub Private
Vulnerability Reporting etkinleştirildiğinde özel güvenlik bildirimi kullanılmalıdır.
