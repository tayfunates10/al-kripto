# ADR-0004: Temel araştırma sinyali

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Amaç

Aşama 4 için basit, deterministik ve açıklanabilir bir araştırma sinyali tanımlanır.
Bu bileşen yalnızca backtest ve paper ortamlarında kullanılmak üzere tasarlanmıştır.

## Karar

Bileşen yalnızca kapanmış mum geçmişini kullanır ve üç koşulu değerlendirir:

1. Kısa dönem basit hareketli ortalama uzun dönem ortalamanın üzerinde olmalıdır.
2. Son kapanış seçilen pencerenin hacim ağırlıklı kapanış fiyatının üzerinde olmalıdır.
3. Yakın dönem ortalama mutlak close-to-close değişim belirlenen tavanı aşmamalıdır.

Tüm koşullar sağlanırsa araştırma hedefi `long`, aksi halde `flat` olur. Yetersiz geçmiş
ve sıfır hacimli pencerelerde fail-closed davranışıyla `flat` döndürülür. Hesaplamalarda
`Decimal` kullanılır.

## Kapsam sınırı

Bu bileşen gerçek borsa emri göndermez, API anahtarı gerektirmez ve canlı işlem açmaz.
Amacı yalnızca backtest motoru için tekrar edilebilir bir karşılaştırma noktası sağlamaktır.
