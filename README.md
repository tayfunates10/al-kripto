# al-kripto

`al-kripto`, kripto piyasalarında **garantili kazanç iddiası taşımayan**, ölçülebilir
stratejiler geliştirmek için tasarlanan güvenlik öncelikli bir araştırma ve işlem
otomasyonu projesidir.

> Güncel tamamlanma: **%12** — Aşama 0 ve Aşama 1 tamamlandı.

## İlk ürün kapsamı

- BTC/USDT ve ETH/USDT
- Spot piyasa, yalnızca `long/flat`
- Varsayılan olarak `paper` işlem modu
- Ardından testnet; canlı işlem ayrı ve manuel bir onay kapısına bağlı
- Kaldıraç, vadeli işlem, para çekme ve martingale kapsam dışı
- Yapay zekâ/ML modelleri doğrudan emir gönderemez; bütün emirler bağımsız risk
  motorundan geçer

## Araştırma temeli

Başlangıç araştırması olarak
[Gemini kripto raporu](https://gemini.google.com/share/26b86d378a26?skid=1edc5653-e3ff-49fa-b763-c6e83b9263cf)
incelenmiştir. Rapordaki MVRV, SOPR, Puell Multiple, NVT, SMC, FVG, Kelly ve
backtest önerileri doğrudan doğru kabul edilmez; her biri test edilebilir hipotez
olarak ele alınır. Kaynak ve kabul kayıtları
[`docs/evidence-register.md`](docs/evidence-register.md) dosyasındadır.

## Yol haritası

| Aşama | Ağırlık | Durum | Çıktı |
|---|---:|---|---|
| 0. Kapsam ve kanıt kaydı | %5 | ✅ Tamamlandı | Araştırma iddiaları, kabul ölçütleri |
| 1. Repo ve güvenlik temeli | %7 | ✅ Tamamlandı | Python iskeleti, CI, güvenli ayarlar |
| 2. Veri altyapısı | %12 | ⏳ Bekliyor | Mum, işlem ve order-book adaptörleri |
| 3. Backtest motoru | %15 | ⏳ Bekliyor | Olay tabanlı, maliyet ve gecikme duyarlı test |
| 4. Temel strateji | %10 | ⏳ Bekliyor | VWAP, trend ve oynaklık rejimi |
| 5. On-chain rejim motoru | %8 | ⏳ Bekliyor | MVRV, SOPR, Puell ve NVT filtreleri |
| 6. SMC motoru | %8 | ⏳ Bekliyor | Swing, sweep, BOS/CHoCH, FVG ve bloklar |
| 7. Risk motoru | %12 | ⏳ Bekliyor | Risk sınırları, korelasyon ve kill-switch |
| 8. Testnet yürütmesi | %8 | ⏳ Bekliyor | Güvenli ve tekrar edilebilir emir iletimi |
| 9. ML araştırma katmanı | %5 | ⏳ Bekliyor | OOS doğrulamalı deneyler |
| 10. İzleme ve panel | %5 | ⏳ Bekliyor | PnL, drawdown, veri ve sistem alarmları |
| 11. Paper-to-live kapısı | %5 | ⏳ Bekliyor | Stres testi ve manuel canlı onayı |
| **Toplam** | **%100** | **%12 tamamlandı** | |

## Güvenlik modeli

Uygulama hiçbir ayar verilmediğinde `paper` modunda açılır. `live` modu için aynı
anda API anahtarı, API sırrı, açık etkinleştirme bayrağı ve sabit bir bilinçli onay
ifadesi gerekir. Gizli değerler uygulama çıktısına veya nesne temsiline yazılmaz.

API anahtarlarında para çekme yetkisi kapalı olmalı; mümkünse IP kısıtlaması ve
yalnızca gerekli spot işlem yetkileri kullanılmalıdır. Ayrıntılar
[`SECURITY.md`](SECURITY.md) ve [`docs/risk-policy.md`](docs/risk-policy.md)
dosyalarındadır.

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

Güvenli varsayılan yapılandırmayı görmek için:

```bash
PYTHONPATH=src python -m al_kripto
```

## Dizin yapısı

```text
src/al_kripto/        Uygulama paketi
tests/                Birim testleri
docs/                 Mimari, kanıt ve risk belgeleri
.github/workflows/    CI kalite kapıları
```

## Sorumluluk reddi

Bu proje eğitim ve araştırma amaçlıdır; yatırım tavsiyesi veya kâr garantisi
değildir. Canlı işlem, sermaye kaybı dahil ciddi finansal risk taşır.
