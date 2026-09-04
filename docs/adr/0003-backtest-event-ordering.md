# ADR-0003: Backtest olay sırası ve yürütme varsayımları

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Bağlam

Stratejinin kapanmamış veya gelecekteki mum bilgisini kullanması, gerçek dışı performans
ve look-ahead bias üretir. Komisyon ile kaymanın ihmal edilmesi de sonuçları sistematik
olarak iyimser gösterir.

## Karar

- Strateji yalnızca o ana kadar **kapanmış** mumların immutable geçmişini görür.
- Bir mum kapandıktan sonra üretilen `long/flat` hedefi, en erken bir sonraki mumun
  açılışında yürütülür.
- MVP backtest motoru spot `long/flat` ile sınırlıdır; short ve kaldıraç yoktur.
- Alışta kayma referans açılış fiyatını yukarı, satışta aşağı taşır.
- Komisyon fill notional değeri üzerinden ayrıca düşülür.
- Fiyat, miktar, PnL ve maliyet hesaplarında `Decimal` kullanılır.
- Equity her mum kapanışında mark-to-market edilir ve maksimum drawdown bu seri üzerinden
  hesaplanır.
- Açık pozisyon test sonunda zorla kapatılmaz; final equity son kapanış fiyatıyla
  mark-to-market edilir. Böylece görünmeyen bir ek fill varsayılmaz.
- Tamamlanan round-trip işlemler gross/net PnL ile ayrı kaydedilir.

## Sonuçlar

Bu motor strateji kârlılığını kanıtlamaz; yalnızca deterministik ve maliyet duyarlı bir
araştırma zemini sağlar. Aşama 4 ve sonraki stratejiler aynı olay sırasına uymak zorundadır.
OOS, walk-forward, DSR/PBO, maliyet stresi ve Monte Carlo kapıları sonraki araştırma
katmanlarında ayrıca uygulanacaktır.
