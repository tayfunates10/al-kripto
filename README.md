# al-kripto

`al-kripto`, kripto piyasa verileri üzerinde güvenlik öncelikli araştırma, backtest ve paper-simulation çalışmaları için geliştirilen bir Python projesidir.

> Güncel tamamlanma: **%90** — Aşama 0–9 tamamlandı. Aşama 10 PR doğrulamasında.

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
| 5. On-chain rejim motoru | %8 | ✅ Tamamlandı | MVRV, SOPR, Puell ve NVT filtreleri |
| 6. SMC motoru | %8 | ✅ Tamamlandı | Swing, sweep, BOS/CHoCH, FVG ve bloklar |
| 7. Risk motoru | %12 | ✅ Tamamlandı | Risk sınırları, korelasyon ve kill-switch |
| 8. Testnet yürütmesi | %8 | ✅ Tamamlandı | Tekrarlanabilir test-environment iletimi |
| 9. ML araştırma katmanı | %5 | ✅ Tamamlandı | OOS doğrulamalı deneyler |
| 10. İzleme ve panel | %5 | 🚧 PR doğrulamasında | PnL, drawdown, veri ve sistem alarmları |
| 11. Paper-to-production kapısı | %5 | ⏳ Bekliyor | Stres testi ve manuel dış onay |
| **Toplam** | **%100** | **%90 tamamlandı** | |

## Tamamlanan teknik temel

Aşama 2, `Candle`, `Trade`, `OrderBookLevel` ve `OrderBookSnapshot` doğrulamalarını; sağlayıcıdan bağımsız `MarketDataSource` sözleşmesini ve yalnızca public/read-only Binance Spot market-data adaptörünü içerir. Hesaplamalarda `Decimal` kullanılır ve birim testleri gerçek ağa çıkmadan çalışır.

Aşama 3 backtest motoru yalnızca kapanmış mum geçmişini stratejiye verir, sinyali en erken bir sonraki mum açılışında uygular, komisyon/kayma modelini içerir ve equity, drawdown ile tamamlanan round-trip sonuçlarını kaydeder.

Aşama 4 temel araştırma sinyali; kısa/uzun hareketli ortalama trend filtresi, hacim ağırlıklı fiyat filtresi ve ortalama mutlak close-to-close değişim tabanlı oynaklık filtresinden oluşur. Yetersiz geçmiş veya sıfır hacimde `flat` döner.

Aşama 5 on-chain araştırma katmanı MVRV, SOPR, Puell Multiple ve NVT gözlemlerini tarihsel yüzdeliklerle normalleştirilmiş biçimde taşır. Yayın zamanı ve veri tazeliği kontrol edilmeden bir gözlem rejim hesabına girmez; yetersiz güncel veri durumunda fail-closed `unknown` döner. Rejim etiketleri betimleyicidir ve doğrudan işlem emri değildir.

Aşama 6 SMC araştırma motoru swing, liquidity sweep, BOS/CHoCH, FVG ve deterministik order-block olayları üretir. Swing olayları sağ taraf doğrulaması tamamlanmadan kullanılmaz; her olay indeks ve zaman bilgisi taşır. Bu olaylar araştırma özelliğidir, doğrudan işlem sinyali değildir.

Aşama 7 merkezi risk kapısı kill-switch, veri tazeliği, mutabakat, günlük kayıp, drawdown, açık pozisyon ve korelasyon kontrollerini uygular. İşlem başına risk ve maruziyet sınırları istek boyutunu yalnızca küçültebilir; risk motoru hiçbir zaman stratejinin istediğinden daha büyük maruziyet üretemez. Sayısal limitler zorunlu yapılandırmadır ve canlı kullanım için varsayılan yatırım ayarı seçilmez.

Aşama 8 test-environment yürütmesi gerçek borsaya bağlanmadan idempotent istemci emir kimlikleri, kısmi/tam dolum, iptal ve terminal durum korumalarını doğrular. Gerçek API anahtarı veya sermaye gerektirmez; canlı yürütmeyi etkinleştirmez.

Aşama 9 ML araştırma katmanı kronolojik train/validation/test ayrımı, sınır purge boşlukları ve yalnızca OOS tahmin metriklerini uygular. ML çıktıları işlem emri değildir ve risk/yürütme katmanlarını doğrudan çağıramaz.

Aşama 10 read-only izleme katmanı equity, günlük ve realized PnL, drawdown, günlük kayıp, veri yaşı, heartbeat, mutabakat, kill-switch, açık emir ve sistem hata durumlarını tek sağlık raporunda toplar. Kritik durumlar `blocked`, uyarılar `degraded` olarak raporlanır; dashboard payload'ı hiçbir gizli değer veya emir yetkisi taşımaz.

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
