# ADR-0002: Piyasa veri sınırı

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Bağlam

Backtest ve strateji katmanının borsa JSON biçimine doğrudan bağlanması; veri tipi,
zaman damgası, sıralama ve bozuk order-book hatalarının stratejiye sızmasına yol açar.
Aşama 2, mum, aggregate trade ve order-book verisi için tek bir doğrulama sınırı ister.

## Karar

- Domain modelleri `Decimal` kullanır; fiyat ve miktar için `float` kullanılmaz.
- Harici payload, stratejiye ulaşmadan önce yapısal ve mantıksal doğrulamadan geçer.
- Mum ve işlem serilerinde kronolojik sıra zorunludur.
- Order-book snapshot'ında bid/ask sırası ve crossed-book durumu doğrulanır.
- Binance Spot public market data için `https://data-api.binance.vision` kullanılır.
- Public veri adaptörü API anahtarı istemez ve yalnızca GET/okuma yapar.
- Ağ çağrısı enjekte edilebilir transport arkasındadır; birim testleri ağa çıkmaz.
- Zaman damgaları sağlayıcının varsayılan milisaniye semantiğiyle tutulur.

## Sonuçlar

Aynı `MarketDataSource` sözleşmesi daha sonra CSV/replay, WebSocket veya başka borsa
adaptörleriyle uygulanabilir. Backtest motoru Binance'e bağımlı olmayacaktır.
