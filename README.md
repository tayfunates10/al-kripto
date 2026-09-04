# al-kripto

`al-kripto`, kripto piyasa verileri üzerinde güvenlik öncelikli araştırma, backtest ve paper-simulation çalışmaları için geliştirilen bir Python projesidir.

> Güncel tamamlanma: **%49** — Aşama 0–4 tamamlandı.

## Kapsam

- BTC/USDT ve ETH/USDT spot piyasa verileri
- `long/flat` araştırma hedefleri
- Varsayılan çalışma biçimi paper/simulation
- Gerçek para ile emir yürütmesi bu aşamalarda etkin değildir
- Kaldıraç, futures, short ve para çekme kapsam dışıdır

## Yol haritası

| Aşama | Ağırlık | Durum | Çıktı |
|---|---:|---|---|
| 0. Kapsam ve kanıt kaydı | %5 | ✅ Tamamlandı | Araştırma iddiaları, kabul ölçütleri |
| 1. Repo ve güvenlik temeli | %7 | ✅ Tamamlandı | Python iskeleti, CI, güvenli ayarlar |
| 2. Veri altyapısı | %12 | ✅ Tamamlandı | Doğrulamalı mum, işlem ve order-book adaptörleri |
| 3. Backtest motoru | %15 | ✅ Tamamlandı | Olay tabanlı, maliyet ve gecikme duyarlı test |
| 4. Temel strateji | %10 | ✅ Tamamlandı | VWAP, trend ve oynaklık rejimi |
| 5. On-chain rejim motoru | %8 | ⏳ Bekliyor | MVRV, SOPR, Puell ve NVT filtreleri |
| 6. SMC motoru | %8 | ⏳ Bekliyor | Swing, sweep, BOS/CHoCH, FVG ve bloklar |
| 7. Risk motoru | %12 | ⏳ Bekliyor | Risk sınırları, korelasyon ve kill-switch |
| 8. Testnet yürütmesi | %8 | ⏳ Bekliyor | Tekrarlanabilir test-environment iletimi |
| 9. ML araştırma katmanı | %5 | ⏳ Bekliyor | OOS doğrulamalı deneyler |
| 10. İzleme ve panel | %5 | ⏳ Bekliyor | PnL, drawdown, veri ve sistem alarmları |
| 11. Paper-to-production kapısı | %5 | ⏳ Bekliyor | Stres testi ve manuel dış onay |
| **Toplam** | **%100** | **%49 tamamlandı** | |

## Tamamlanan teknik temel

Aşama 2, `Candle`, `Trade`, `OrderBookLevel` ve `OrderBookSnapshot` doğrulamalarını; sağlayıcıdan bağımsız `MarketDataSource` sözleşmesini ve yalnızca public/read-only Binance Spot market-data adaptörünü içerir. Hesaplamalarda `Decimal` kullanılır ve birim testleri gerçek ağa çıkmadan çalışır.

Aşama 3 backtest motoru yalnızca kapanmış mum geçmişini stratejiye verir, sinyali en erken bir sonraki mum açılışında uygular, komisyon/kayma modelini içerir ve equity, drawdown ile tamamlanan round-trip sonuçlarını kaydeder.

Aşama 4 temel araştırma sinyali; kısa/uzun hareketli ortalama trend filtresi, hacim ağırlıklı fiyat filtresi ve ortalama mutlak close-to-close değişim tabanlı oynaklık filtresinden oluşur. Yetersiz geçmiş veya sıfır hacimde `flat` döner.

## Yerel geliştirme

Python 3.12 veya üzeri gerekir.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy src
```

Yalnızca standart kütüphaneyle temel testleri çalıştırmak için:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Dizin yapısı

```text
src/al_kripto/        Uygulama paketi
tests/                Birim testleri
docs/                 Mimari, kanıt ve risk belgeleri
.github/workflows/    CI kalite kapıları
```

## Güvenlik sınırı

Bu aşamalarda proje araştırma, backtest ve paper/simulation amacıyla tutulur. Gerçek para ile emir yürütmesi otomatik olarak açılmaz; üretim benzeri kullanımlar ayrı manuel kapılara tabidir.
