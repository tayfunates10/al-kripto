# Kullanım Testi ve Hata Tespit Raporu — 2. Tur

**Tarih:** 2026-09-05
**Denetlenen sürüm:** `main` üzerindeki `a230bcf` commit'i
**Önceki tur:** [`kullanim-testi-raporu.md`](kullanim-testi-raporu.md) — 23 bulgu, tamamı kapatıldı
**Yöntem:** Kalite kapıları + 7 senaryo grubu (63 kontrol), kombinasyon taramaları ve ölçekleme testleri

---

## 1. Yönetici özeti

Bu tur, ilk denetimin 23 bulgusu kapatıldıktan ve `orchestration` katmanı eklendikten sonra
yapıldı. Yeniden yazılan kodun **kendisi** hedef alındı.

Otomatik kalite kapılarının tamamı temiz: 145 test, satır kapsamı %90, `ruff`,
`ruff format`, `mypy --strict` ve `pip-audit` hatasız. Buna rağmen **1 yüksek, 6 orta ve
3 düşük öncelikli olmak üzere 10 yeni bulgu** tespit edildi.

İlk turun bulguları tekrar kontrol edildi; **hiçbiri geri gelmemiş.** Bu turdaki bulgular
tamamen yeni kodda.

### Bulguların örüntüsü

Üç tekrar eden tema var:

1. **Hata sözleşmesi delikleri (Y-01, Y-02, Y-07).** İç katman istisnaları — `ValueError`,
   `decimal.InvalidOperation`, `BacktestValidationError` — dış katmanın kendi hata türüne
   sarılmadan çağırana ulaşıyor. Çağıran tek bir istisna türü yakalayamıyor.
2. **Opsiyonel alana dayanan koruma (Y-03, Y-04, Y-07).** Bir güvenlik kontrolü, varsayılanı
   `None` olan ya da yalnızca tek bir uygulamada bulunan bir alana bağlanınca, korumanın
   kendisi opsiyonel hale geliyor.
3. **Sessizce kullanılamaz yapılandırma (Y-05).** Doğrulamayı geçen ama motoru işlevsiz
   bırakan ayar. İlk turdaki B-08 ile aynı sınıf.

### Öncelik dağılımı

| Öncelik | Adet | Konu |
|---|---:|---|
| Yüksek | 1 | Boru hattı ikinci kez çalıştırılamıyor |
| Orta | 6 | Decimal taşması, interval koruması, uzlaşı ayarı, kill-switch çelişkisi, sağlayıcı sözleşmesi |
| Düşük | 3 | Kanıt referans formatı, girdi zaman tutarlılığı, private import |

---

## 2. Otomatik kalite kapıları

Python 3.12.3, temiz sanal ortam.

| Kapı | Sonuç |
|---|---|
| `ruff check .` | ✅ Temiz |
| `ruff format --check .` | ✅ 70 dosya biçimli |
| `mypy src tests` (strict) | ✅ 53 dosyada sorun yok |
| `pytest --cov` | ✅ 145 test + 18 subtest, %90 kapsam |
| `pip-audit . --skip-editable` | ✅ Bilinen zafiyet yok |

---

## 3. Yüksek öncelikli bulgu

### Y-01 — `PaperValidationPipeline` aynı planla ikinci kez çalıştırılamıyor

**Dosya:** `src/al_kripto/orchestration/pipeline.py:217`

`client_order_id` `PaperValidationPlan`'a sabitlenmiş. İkinci döngüde fiyat ya da onaylanan
büyüklük değiştiğinde hesaplanan miktar da değişir; `TestExecutionEngine.submit` aynı
kimlikle farklı parametre görünce ham `ValueError` fırlatır ve bu istisna
`PipelineValidationError`'a sarılmadan çağırana ulaşır.

```
1. dongu: onay=1000 emir miktari=9.708
2. dongu: ValueError: client_order_id already exists with different order parameters
```

Gerçek bir günlük paper doğrulama döngüsünde fiyat her tur değişir, dolayısıyla **ikinci tur
pratikte her zaman çöker.** Tek turluk kullanımda sorun görünmediği için paketin kendi
testleri bunu yakalamıyor.

İkinci dal da sorunlu: miktar tesadüfen aynı çıkarsa `submit` idempotentlik gereği **birinci
döngünün emrini** döndürür — yani yeni döngünün kararı sessizce yok sayılır.

**Yeniden üretim:**

```python
pipe = PaperValidationPipeline(...)  # tek bir TestExecutionEngine ile
pipe.run(plan, inputs_with_notional("1000"))
pipe.run(plan, inputs_with_notional("500"))
# ValueError: client_order_id already exists with different order parameters
```

**Önerilen düzeltme:** `client_order_id`'yi plana sabitlemek yerine döngü başına türetin
(örneğin `f"{plan.client_order_id}-{inputs.decision_time_ms}"`), ya da `PaperValidationInputs`
alanı yapın. Ayrıca `submit` çağrısını `PipelineValidationError`'a sarın; boru hattı kendi
hata türü dışında bir istisna sızdırmamalı.

---

## 4. Orta öncelikli bulgular

### Y-02 — `_round_down_to_step` ham `decimal.InvalidOperation` sızdırıyor

**Dosya:** `src/al_kripto/backtest/engine.py:212-214`

`(quantity / step).to_integral_value(...)` işlemi, sonuç Decimal'in 28 haneli varsayılan
duyarlığını aşınca `DivisionImpossible` fırlatır. `BacktestConfig` bu değerleri kabul ediyor
(`quantity_step` yalnızca sonlu ve > 0 olmak zorunda), dolayısıyla doğrulamayı geçen bir
yapılandırma çalışma anında domain dışı bir istisnayla düşüyor.

| Sermaye | Lot adımı | Sonuç |
|---|---|---|
| 10.000 | `1E-20` | ✅ miktar `99.85017481269355332323` |
| 10.000 | `1E-27` | ❌ `InvalidOperation: [DivisionImpossible]` |
| `1E+20` | `1E-8` | ✅ miktar `998501748126935533.23238480` |
| `1E+25` | `1E-8` | ❌ `InvalidOperation: [DivisionImpossible]` |

**Önerilen düzeltme:** `BacktestConfig.__post_init__` içinde `initial_cash / quantity_step`
oranının duyarlık sınırını aşıp aşmadığını kontrol edin, ya da `_round_down_to_step` içinde
yerel bir `decimal.localcontext()` ile daha geniş duyarlık kullanıp taşmayı
`BacktestValidationError`'a çevirin.

---

### Y-03 — Interval tutarlılık kontrolü `interval=None` ile atlatılabiliyor

**Dosya:** `src/al_kripto/backtest/engine.py:196`, `src/al_kripto/market_data/models.py:48`

`Candle.interval` varsayılanı `None`. `_validate_series` yalnızca **etiketler farklıysa**
hata veriyor; hepsi `None` ise seri geçiyor. Binance adaptörü mumları etiketliyor, ancak elle
üretilen, dosyadan okunan ya da üçüncü taraf bir kaynaktan gelen mumlar varsayılan olarak
etiketsiz kalıyor.

```python
c_1m = Candle(..., open_time_ms=0, close_time_ms=59_999, interval=None)
c_1h = Candle(..., open_time_ms=60_000, close_time_ms=3_659_999, interval=None)
BacktestEngine(cfg).run((c_1m, c_1h), strategy)  # KABUL EDILIYOR
```

Etiketli mumlarda koruma çalışıyor (`All candles must use the same interval metadata.`),
yani düzeltme kısmi: kullanıcının etiketlemeyi hatırlamasına bağlı.

**Önerilen düzeltme:** Seride etiketli ve etiketsiz mumların karışmasını yasaklayın; ya da
`_validate_series` içinde etiket yokken ardışık mumların süresini karşılaştırın.

---

### Y-04 — `interval` etiketi mumun gerçek süresiyle hiç karşılaştırılmıyor

**Dosya:** `src/al_kripto/market_data/models.py:48-53`

`Candle` yalnızca etiketin biçimini (`^[1-9]\d*[smhdwM]$`) doğruluyor, etiketin mumun
kapsadığı süreye uygun olup olmadığını denetlemiyor.

```python
Candle(..., open_time_ms=0, close_time_ms=3_599_999, interval="1m")
# "1m" etiketli, gercek suresi 3600 saniye -> KABUL EDILIYOR
```

Bu, Y-03'ün korumasını zayıflatıyor: etiketli mumlarda bile koruma doğrulanmamış bir
etikete dayanıyor. Yanlış etiketlenmiş iki farklı zaman dilimi aynı etiketi taşıyorsa
`_validate_series` hiçbir şey fark etmez.

**Önerilen düzeltme:** Etiket verildiğinde `close_time_ms - open_time_ms + 1` değerini
etiketin ima ettiği süreyle karşılaştırın.

---

### Y-05 — `consensus_metrics` ulaşılamaz ayarlanabiliyor

**Dosya:** `src/al_kripto/onchain/regime.py:28`, `:39-40`

`consensus_metrics` yalnızca `1..len(MetricName)` aralığında doğrulanıyor; `minimum_metrics`
ile ya da gerçekte mevcut metrik sayısıyla karşılaştırılmıyor. `consensus_metrics`
kullanılabilir metrik sayısından büyük olursa `overheated`/`underheated` **asla** üretilemez
ve motor sessizce her zaman `neutral` döner.

```python
cfg = OnChainRegimeConfig(minimum_metrics=2, consensus_metrics=4)  # KABUL EDILIYOR
# 3 metrik, hepsi %99 yuzdelikte:
engine.classify(snapshot, decision_time_ms=now).regime  # -> "neutral"
```

Fail-closed olduğu için tehlikeli değil, ancak ilk turdaki B-08 (`max_abs_correlation=0`) ile
birebir aynı sınıf: doğrulamayı geçen ama motoru işlevsiz bırakan yapılandırma.

**Önerilen düzeltme:** `consensus_metrics <= minimum_metrics` şartını doğrulayın.

---

### Y-06 — Kill-switch durumu iki ayrı kaynaktan geliyor ve çelişebiliyor

**Dosya:** `src/al_kripto/orchestration/pipeline.py`

Boru hattında kill-switch iki yerde temsil ediliyor: risk motorunun tuttuğu gerçek
`KillSwitch` nesnesi ve `MonitoringSnapshot.kill_switch_engaged` alanı. Boru hattı bunların
uyuştuğunu denetlemiyor.

```
izleme durumu = healthy        (kill_switch_engaged=False bildirildi)
risk karari   = reject         (gercek KillSwitch acik)
emir          = yok
```

Emir üretilmediği için **fail-closed davranış korunuyor** — sorun güvenlikte değil,
raporlamada: panel sistemi "sağlıklı" gösterirken risk motoru her talebi reddediyor.
Operatör neden işlem olmadığını izleme çıktısından anlayamaz.

**Önerilen düzeltme:** `PaperValidationInputs.__post_init__` içinde equity gibi bunu da
çapraz doğrulayın; ya da izleme anlık görüntüsünü risk motorunun kill-switch durumundan
türetin.

---

### Y-07 — Kapanmamış mum garantisi sözleşmede değil, tek bir uygulamada

**Dosya:** `src/al_kripto/market_data/base.py:13-21`, `src/al_kripto/orchestration/pipeline.py`

İlk turun B-02 düzeltmesi `BinanceSpotMarketData.fetch_candles`'a `only_closed=True`
parametresi ekledi. Ancak `MarketDataSource` protokolü bu parametreyi **tanımlamıyor**:

```
protokol       : ['self', 'symbol', 'interval', 'limit', 'start_time_ms', 'end_time_ms']
Binance adaptoru: [..., 'only_closed']
```

Boru hattı `MarketDataSource` kabul ediyor ve `only_closed` geçirmiyor; yalnızca Binance
adaptörünün varsayılanına güveniyor. Sözleşmeye uyan farklı bir sağlayıcı takıldığında
garanti kayboluyor:

```
ThirdPartySource (kapanmamis mumu filtrelemiyor)
-> BacktestValidationError: Backtest requires fully closed candles...
```

İki sorun bir arada: garanti sağlayıcıya özel, ve ortaya çıkan hata boru hattının kendi
hata türüne sarılmıyor (Y-01 ile aynı sözleşme deliği).

**Önerilen düzeltme:** `only_closed`'ı protokole taşıyın, ya da boru hattı mumları aldıktan
sonra `close_time_ms <= decision_time_ms` kontrolünü kendi yapıp `PipelineValidationError`
üretsin.

---

## 5. Düşük öncelikli bulgular

| Kod | Bulgu | Dosya |
|---|---|---|
| Y-08 | Hazırlık kanıtı referansı **herhangi bir URI şemasını** kabul ediyor: `javascript://alert` ve `file:///etc/passwd` geçiyor. `readiness_payload` referansı olduğu gibi taşıdığı için, bunu bağlantı olarak render eden bir panelde depolanmış XSS vektörü olur. | `readiness/models.py:9` |
| Y-09 | Boru hattı girdilerinin aynı ana ait olduğu yalnızca `equity` üzerinden denetleniyor. `monitoring_snapshot.observed_at_ms=1` ile `decision_time_ms=1700000000000` birlikte kabul ediliyor. | `orchestration/pipeline.py:106-112` |
| Y-10 | `binance.py`, `models`'tan `_validate_symbol` **private** adını import ediyor. Doğrulama paylaşılacaksa açık bir API olmalı. | `market_data/binance.py:19` |

---

## 6. Doğrulanan olumlu davranışlar

Bu turda aşağıdakiler ölçülerek doğrulandı:

- **`_HistoryView` sağlam.** Yeni prefix görünümü 20 sözleşme kontrolünün tamamını geçti:
  negatif indeks, adımlı ve ters dilim, `tuple()`, `list()`, `reversed()`, `in`, `index()`,
  `count()`. Sınır dışı erişim `IndexError` veriyor, `append`/`pop`/`__setitem__`
  `AttributeError` ile reddediliyor.
- **Gelecek verisi sızıntısı yok.** 10 mumluk seride her çağrıda stratejiye verilen geçmiş
  tam olarak o ana kadarki mumlar; prefix sınırı aşılamıyor.
- **Backtest O(n²) değil.** 8.000 → 32.000 mumda süre 0,019 s → 0,066 s (doğrusal).
  Pencere dilimi alan strateji de doğrusal.
- **Para korunumu birebir.** 200 mumluk, 50 dolumlu, 25 round-trip'li koşuda bağımsız
  yeniden hesap `final_cash`, `final_position_quantity` ve `final_equity` ile **tam olarak**
  eşleşti.
- **İzleme hiçbir kombinasyonda çökmüyor.** 8 bayrağın 640 geçerli kombinasyonunda istisna
  yok; `paused` (güvenli bekleme) ile `blocked` (arıza) doğru ayrışıyor, uyarı varken
  `degraded` önceliği doğru.
- **Risk motoru maruziyeti asla büyütmüyor.** 6.000 rastgele vakada `approved_notional >
  requested_notional` ihlali, gerekçeli `APPROVE` veya sıfır olmayan `REJECT` gözlenmedi.
- **Veri katmanı sertleşmiş.** Geçersiz semboller **istek gönderilmeden** reddediliyor;
  duplike/ters sıralı mum yakalanıyor; aynı milisaniyeli işlemler (meşru durum) kabul
  ediliyor; bozuk payload'lar `MarketDataPayloadError` veriyor; `base_url` HTTPS zorunlu.
- **Yürütme katmanı değişmez.** Emir `frozen`; aşırı dolum, negatif, sıfır, `float`, `NaN`
  ve `Infinity` denemelerinin hiçbiri motor durumunu bozmadı.
- **Hazırlık kapısı zaman sınırlı.** Süresi geçmiş ve gelecekte kaydedilmiş kanıtlar
  `not_ready` üretiyor; `live_trading_enabled` her koşulda `False`.
- **Gizli değer sızıntısı yok.** `Settings` `repr`/`str`/`redacted()` çıktılarında API
  anahtarı geçmiyor; `dashboard_payload` yalnızca operasyonel alanlar taşıyor.
- **İlk turun 23 bulgusunun hiçbiri geri gelmemiş.**

---

## 7. Önerilen çalışma sırası

1. **Y-01** — boru hattı ikinci turda çöküyor; "günlük doğrulama döngüsü" iddiasını
   doğrudan geçersiz kılıyor.
2. **Y-07** ve **Y-02** — hata sözleşmesi delikleri. Boru hattı ve backtest yalnızca kendi
   hata türlerini sızdırmalı.
3. **Y-03** + **Y-04** birlikte — interval koruması ancak etiket doğrulanırsa anlamlı.
4. **Y-05** ve **Y-06** — yapılandırma ve durum tutarlılığı.
5. **Y-08**, **Y-09**, **Y-10**.

---

## 8. Test kapsamı

| Senaryo grubu | Kontrol | İçerik |
|---|---:|---|
| T1 | 20 + 8 | `_HistoryView` sözleşmesi, sızıntı, değişmezlik, ölçekleme |
| T2 | 9 | Para korunumu, lot yuvarlaması, Decimal taşması, interval, determinizm |
| T3 | 7 | İzleme 640 kombinasyon taraması, risk 6.000 vakalık tarama, gizli değer |
| T4 | 11 | On-chain uzlaşı/tazelik, hazırlık referans ve süre, yürütme değişmezliği |
| T5 | 9 | Binance adaptörü, bozuk payload, HTTPS, config, gizli değer |
| T6 | 7 | Orkestrasyon: tekrarlı döngü, REDUCE, kill-switch çelişkisi, zaman tutarlılığı |
| T7 | 2 | `MarketDataSource` sözleşmesi ve üçüncü taraf sağlayıcı |

**Toplam:** 63 kontrol + 6.640 kombinasyon/rastgele girdi vakası.
