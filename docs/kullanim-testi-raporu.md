# Kullanım Testi ve Hata Tespit Raporu

**Tarih:** 2026-09-05
**Denetlenen sürüm:** `main` üzerindeki `713d236` commit'i (Aşama 0–11)
**Yöntem:** Kalite kapılarının çalıştırılması + kütüphanenin son kullanıcı gibi uçtan uca
kullanıldığı 10 senaryo grubu (57 ayrı kontrol), rastgele girdi taramaları ve ölçekleme testleri

> **Bu rapor bir denetim kaydıdır.** Aşağıdaki bölümler `713d236` sürümünde tespit edilen
> durumu anlatır ve olduğu gibi korunmuştur. Bulguların tamamı bu dal üzerinde daha sonra
> düzeltilmiştir; her bulgunun güncel durumu ve düzeltmenin ölçümle doğrulanması
> [§3 Düzeltme sonrası doğrulama](#3-düzeltme-sonrası-doğrulama) bölümündedir.

---

## 1. Yönetici özeti

Otomatik kalite kapılarının tamamı temiz geçiyor: 107 test başarılı, satır kapsamı %91,
`ruff`, `ruff format`, `mypy --strict` ve `pip-audit` hatasız. Buna rağmen kütüphaneyi
gerçek bir kullanıcı gibi uçtan uca kullandığımızda **6 yüksek, 8 orta ve 8 düşük öncelikli
sorun** tespit edildi.

Bulguların tamamı raporlandıktan sonra bu dal üzerinde düzeltilmiş ve her biri yeniden
ölçülerek doğrulanmıştır — ayrıntı için [§3](#3-düzeltme-sonrası-doğrulama). Aşağıdaki
değerlendirme denetim anındaki (`713d236`) durumu anlatır.

Bulguların kök nedeni tek bir yapısal boşlukta toplanıyor: **modüller birbirine hiç
bağlanmamış.** `onchain`, `smc`, `risk`, `execution`, `ml_research`, `monitoring` ve
`readiness` modüllerinin hiçbiri depodaki başka bir modül tarafından çağrılmıyor. Her aşama
kendi içinde iyi test edilmiş ancak aşamalar arası hiçbir entegrasyon testi yok. Yüksek
öncelikli hataların çoğu tam olarak bu sınırlarda ortaya çıkıyor — örneğin veri katmanının
ürettiği çıktı, backtest motorunun kabul ettiği girdi değil.

Güvenlik sınırı iddiası doğrulandı: depoda gerçek emir gönderen bir yürütme yolu yok,
fail-closed varsayılanlar (kill-switch açık, canlı mod kilitli) çalışıyor, hazırlık kapısı
otomatik olarak canlı işlemi açamıyor.

### Öncelik dağılımı

| Öncelik | Adet | Konu |
|---|---:|---|
| Yüksek | 6 | Entegrasyon kopukluğu, SMC olay üretimi, izleme dayanıklılığı, ML veri bölme, yürütme kapsüllemesi, ölçekleme |
| Orta | 8 | Risk/izleme uç durumları, on-chain tazelik, girdi doğrulama tutarsızlıkları, kanıt kalitesi |
| Düşük | 8 | Raporlama netliği, tip/enum karışıklığı, eksik alanlar |

---

## 2. Otomatik kalite kapıları

Python 3.12.3 ile temiz bir sanal ortamda çalıştırıldı.

| Kapı | Sonuç |
|---|---|
| `ruff check .` | ✅ Temiz |
| `ruff format --check .` | ✅ 64 dosya biçimli |
| `mypy src tests` (strict) | ✅ 48 dosyada sorun yok |
| `pytest --cov` | ✅ 107 test + 11 subtest, %91 kapsam |
| `pip-audit . --skip-editable` | ✅ Bilinen zafiyet yok |

Kapsamın düşük olduğu yerler doğrudan aşağıdaki bulgularla örtüşüyor:
`market_data/binance.py` %75, `backtest/models.py` %88, `monitoring/models.py` %88,
`smc/models.py` %89 — yani kaçırılan satırların büyük kısmı hata ve uç durum yolları.

---

## 3. Düzeltme sonrası doğrulama

Bulgular raporlandıktan sonra aynı dal üzerinde düzeltmeler yapıldı. Aşağıdaki tablo, her
bulgunun **güncel koda karşı yeniden ölçülmüş** durumudur: commit mesajlarına güvenilmemiş,
her satır için raporun orijinal senaryosu/saldırısı `073e6b7` kod durumunda yeniden çalıştırılmıştır.

**Sonuç: 23 bulgunun 23'ü kapandı.**

| Kod | Bulgu | Ölçüm sonucu | Düzeltme |
|---|---|---|---|
| B-01 | SMC bayat swing kırılımları | 3 kırılım + aynı OB 3 kez → **1 kırılım, 1 OB** | `f2e7843` |
| B-02 | Veri katmanı ↔ backtest uyumu | `run(fetch_candles(...))` doğrudan geçiyor; kapanmamış mum 0 | `f65b4fc` |
| B-03 | İzleme `equity=0` / bayat peak | İstisna yerine `blocked` + `account_depleted` alarmı | `be928f0`, `f381f1f` |
| B-04 | ML bölme en yeni veriyi kullanıyor mu | Test seti `950..999` — en yeni örnek dahil | `dc6da05` |
| B-05 | Yürütme kapsülleme / terminal koruma | Emir `frozen`; iptal koruması aşılamıyor | `b24aa43`, `6ec70f3` |
| B-06 | Backtest ölçekleme | 4× veri → 16× yerine **5,0×** süre | `90d039e` |
| B-07 | Risk kapısı tükenmiş hesap | `equity=0` → `reject` / `account_depleted` | `abfa59e`, `9cbf357` |
| B-08 | `max_abs_correlation=0` | Artık reddediliyor | `abfa59e` |
| B-09 | On-chain ölçüm tazeliği | 90 günlük ölçüm → `unknown`, 3 metrik de dışlanıyor | `05df6ad` |
| B-10 | Binance sembol doğrulaması | Geçersiz semboller istek gönderilmeden reddediliyor | `f65b4fc` |
| B-11 | Duplike mum | `MarketDataPayloadError: candles must be strictly chronological` | `f65b4fc` |
| B-12 | Yürütme sembol doğrulaması | Sembol deseni yürütme katmanında da uygulanıyor | `b24aa43` |
| B-13 | `float` miktar | `ValueError: quantity must be Decimal` | `b24aa43` |
| B-14 | Hazırlık kanıtı kalitesi | Referans formatı zorunlu, kanıt zaman sınırlı | `a00611b`, `c7a9f60` |
| B-15 | Modül orkestrasyonu | `orchestration.PaperValidationPipeline` 8 modülü bağlıyor | `0fa530b`, `2f04ed0` |
| B-16 | Kill-switch açıkken durum | Güvenli bekleme `paused`, gerçek arıza `blocked` — ayrışıyor | `5677f37`, `23a8471` |
| B-17 | Interval karışımı | 1m + 1h aynı seride → `BacktestValidationError` | `e19ad45`, `088b6fe` |
| B-18 | Lot/step-size yuvarlaması | 26 ondalık → **3 ondalık**; `quantity_step` yoksa fail-closed | `600aeed`, `088b6fe` |
| B-19 | Açık pozisyonda `win_rate` | `0` yerine `None` (hesaplanamaz) | `b6af9d3` |
| B-20 | Desteklenmeyen borsa | `Unsupported exchange: 'kraken'. Supported exchanges: binance.` | `448a095` |
| B-21 | İki `Side` enum'unun eşitliği | `execution.Side.BUY == backtest.Side.BUY` artık `False` | `57c4e39`, `b6af9d3` |
| B-22 | On-chain uzlaşı eşiği | Ayrı uzlaşı alanı eklendi | `05df6ad` |
| B-23 | `OnChainRegimeAssessment` doğrulaması | `__post_init__` eklendi | `05df6ad` |

Düzeltme sonrası kalite kapıları (`073e6b7`): `ruff check`, `ruff format --check`,
`mypy src tests` (53 dosya, strict), `pytest` (140 test) ve `pip-audit` — tamamı temiz.

### Doğrulamanın kapsamadıkları

Bu tablo yalnızca **bu raporda listelenen bulguların** kapandığını gösterir; düzeltmelerin
kendi başına yeni kusur getirmediğinin bağımsız bir denetimi değildir. Özellikle
`orchestration` paketi bu rapordan sonra eklenmiştir ve hiç kullanım testinden geçmemiştir;
ayrıca §6'daki mimari gözlemin (aşamalar arası entegrasyon testi eksikliği) ne ölçüde
kapandığı ayrı bir değerlendirme gerektirir.

---

## 4. Yüksek öncelikli bulgular

### B-01 — SMC motoru bayat swing seviyelerini tekrar tekrar "kırıyor"

**Dosya:** `src/al_kripto/smc/engine.py:127-200`, `src/al_kripto/smc/engine.py:211-220`

Bir yapı kırılımı gerçekleştiğinde motor yalnızca **o anda kullandığı** swing'i
`broken_highs` kümesine ekliyor (`smc/engine.py:168`). Daha eski ve daha düşük seviyeli
swing'ler "kırılmamış" olarak kalıyor. `_latest_available` bir sonraki mumda bu eski
swing'i buluyor ve fiyat zaten çok önce o seviyenin üstüne çıktığı için **yeni bir BOS
olayı** üretiyor. Sonuç: her mumda bir eski seviye "kırılıyor".

Yükselen trend serisinde gözlenen çıktı:

```
mum=13 kapanis=139 bullish/bos seviye=132 (swing idx=10)   <- gerçek kırılım
mum=14 kapanis=141 bullish/bos seviye=126 (swing idx=6)    <- hayalet
mum=15 kapanis=143 bullish/bos seviye=120 (swing idx=2)    <- hayalet
```

Üç yan etki:

1. **Hayalet olaylar:** Fiyatın çok önce aştığı seviyeler için yeni kırılım olayı üretiliyor.
2. **Order block tekrarı:** Aynı mum (idx 12) üç ayrı order block olarak üretiliyor —
   `_find_order_block` her kırılımda yeniden çalışıyor ve aynı sonucu buluyor.
3. **BOS/CHoCH etiketi bozuluyor:** `last_break_direction` hayalet olaylarla güncelleniyor,
   dolayısıyla sonraki gerçek kırılımın CHoCH mu BOS mu olduğu yanlış hesaplanıyor.

**Yeniden üretim:**

```python
from decimal import Decimal as D
from al_kripto.market_data import Candle
from al_kripto.smc.engine import SMCEngine


def c(i, o, h, l, cl):
    t = i * 60_000
    return Candle(
        symbol="BTCUSDT",
        open_time_ms=t,
        close_time_ms=t + 59_999,
        open=D(str(o)),
        high=D(str(h)),
        low=D(str(l)),
        close=D(str(cl)),
        volume=D("10"),
        quote_volume=D("1000"),
        trade_count=5,
        taker_buy_base_volume=D("5"),
        taker_buy_quote_volume=D("500"),
    )


seq = [
    (100, 105, 99, 104),
    (104, 112, 103, 111),
    (111, 120, 110, 112),
    (112, 114, 108, 109),
    (109, 111, 105, 106),
    (106, 118, 105, 117),
    (117, 126, 116, 118),
    (118, 120, 112, 113),
    (113, 116, 110, 111),
    (111, 124, 110, 123),
    (123, 132, 122, 124),
    (124, 126, 118, 119),
    (119, 122, 116, 117),
    (117, 140, 116, 139),
    (139, 142, 138, 141),
    (141, 144, 140, 143),
    (143, 146, 142, 145),
    (145, 148, 144, 147),
    (147, 150, 146, 149),
    (149, 152, 148, 151),
]
a = SMCEngine().analyze(tuple(c(i, *v) for i, v in enumerate(seq)))
for b in a.breaks:
    print(b.index, b.direction.value, b.kind.value, b.level)
for ob in a.order_blocks:
    print("OB", ob.index, ob.confirmed_by_index)
```

**Önerilen düzeltme:** Bir kırılım gerçekleştiğinde, kırılan seviyeden **daha düşük** (bearish
için daha yüksek) tüm önceki swing'leri de `broken_highs`/`broken_lows` kümesine ekleyin.
Ek olarak, aynı order block mumunun birden fazla kez üretilmesini engelleyen bir tekilleştirme
gerekiyor.

---

### B-02 — Veri katmanının çıktısı backtest motorunun girdisi değil

**Dosya:** `src/al_kripto/market_data/binance.py:95-125` ↔ `src/al_kripto/backtest/engine.py:162-165`

Binance `/api/v3/klines` uç noktası her zaman **oluşmakta olan (kapanmamış) son mumu** da
döndürür. `fetch_candles` bu mumu filtrelemiyor. `BacktestEngine._validate_series` ise
`close_time_ms > now` olan mumları haklı olarak reddediyor. Sonuç: kütüphanenin en doğal
ilk kullanım yolu çalışmıyor.

```python
src = BinanceSpotMarketData()
candles = src.fetch_candles("BTCUSDT", "1h")
BacktestEngine().run(candles, BaselineStrategy())
# BacktestValidationError: Backtest requires fully closed candles;
# in-progress candles are not allowed.
```

Kullanıcının kapanmamış mumu elle ayıklaması gerekiyor ancak kütüphanede ne bir yardımcı
fonksiyon, ne bir `only_closed=True` parametresi, ne de README'de bir uyarı var. Bu senaryo
depodaki hiçbir testte yer almıyor — `tests/test_binance_market_data.py` ile
`tests/test_backtest_engine.py` birbirinden tamamen bağımsız.

**Önerilen düzeltme:** `fetch_candles`'a `only_closed: bool = True` parametresi ekleyin
(veya `drop_unclosed_candles(candles, as_of_ms)` yardımcısı) ve iki katmanı birlikte
çalıştıran bir entegrasyon testi yazın.

---

### B-03 — İzleme katmanı en kritik anda istisna fırlatıyor

**Dosya:** `src/al_kripto/monitoring/models.py:117`, `src/al_kripto/monitoring/models.py:120-121`

`MonitoringSnapshot`, `equity > 0` ve `peak_equity >= equity` şartlarını **zorunlu** kılıyor.
Bunlar sağlanmadığında `MonitoringValidationError` fırlatılıyor. Yani:

- **Hesap tamamen tükendiğinde (`equity = 0`)** izleme motoru hiçbir alarm üretemiyor,
  panel çöküyor. Alarm üretmesi gereken tek an tam olarak budur.
- **`peak_equity` güncellenmeden equity artarsa** (çağıranın zirveyi geç güncellemesi gibi
  sıradan bir durum) izleme yine çöküyor.

```python
MonitoringSnapshot(
    observed_at_ms=1,
    equity=D("0"),
    start_of_day_equity=D("10000"),
    peak_equity=D("10000"),
    realized_pnl=D("-10000"),
    market_data_age_ms=0,
    heartbeat_age_ms=0,
    reconciliation_ok=True,
    kill_switch_engaged=False,
    open_orders=0,
)
# MonitoringValidationError: equity must be finite and > 0.
```

İzleme, sistemin son savunma hattı olan salt-okunur gözlem katmanı. Bir veri anomalisinde
istisna fırlatmak yerine anomaliyi **kritik alarm olarak raporlaması** gerekir.

**Önerilen düzeltme:** `equity` ve `peak_equity` için `>= 0` kabul edin; `equity = 0` ve
`peak_equity < equity` durumlarını yeni `AlertCode` değerleriyle (`ACCOUNT_DEPLETED`,
`INCONSISTENT_EQUITY_STATE`) `CRITICAL` alarma dönüştürün.

---

### B-04 — `chronological_split` en güncel verinin büyük kısmını sessizce atıyor

**Dosya:** `src/al_kripto/ml_research/validation.py:59-75`

Fonksiyon serinin **başından** itibaren dilimliyor ve `test_end` sonrasındaki her şeyi
sessizce düşürüyor. Zaman serisi OOS doğrulamasında test setinin serinin **sonunda** olması
beklenir; burada tam tersi oluyor.

```python
samples = list(range(1000))  # 999 = en yeni gözlem
sp = chronological_split(samples, train_size=100, validation_size=50, test_size=50, purge_size=5)
# train 0..99 | val 105..154 | test 160..209
# 790 en güncel örnek sessizce atıldı; model en eski %21'lik dilimde test edildi.
```

Ne bir uyarı, ne bir dönüş değeri, ne de docstring'de bir not var. Kullanıcı 1000 mumla
çalıştığını sanırken aslında 210 mumla çalışıyor ve en güncel rejimi hiç görmüyor.

**Önerilen düzeltme:** Varsayılan olarak serinin sonuna hizalayın (test seti son
`test_size` örnek olacak şekilde geriye doğru dilimleyin) veya fazla örnek olduğunda
açıkça hata verin. Mevcut davranış korunacaksa `dropped_count` döndürün ve docstring'de
belirtin.

---

### B-05 — Yürütme motoru iç durumunu dışarıya sızdırıyor, terminal durum koruması aşılabiliyor

**Dosya:** `src/al_kripto/execution/engine.py:24-42`, `src/al_kripto/execution/models.py:32`

`ExecutionOrder` `frozen` değil (`@dataclass(slots=True)`) ve `submit()`/`get()` motorun
sözlüğündeki **nesnenin ta kendisini** döndürüyor. Çağıran taraf motorun tüm değişmezlerini
serbestçe bozabiliyor:

```python
e = TestExecutionEngine()
o = e.submit(client_order_id="c1", symbol="BTCUSDT", side=Side.BUY, quantity=D("1"))
o.status = ExecutionStatus.FILLED
o.quantity = D("999999")
e.get("c1").quantity  # -> Decimal('999999')  motor kaydı bozuldu
```

Daha ciddisi, iptal koruması dışarıdan aşılabiliyor:

```python
e.cancel("c2")
e.apply_fill("c2", quantity=D("1"), price=D("100"))  # ValueError (doğru)
o2.status = ExecutionStatus.NEW  # korumayı sıfırla
e.apply_fill("c2", quantity=D("1"), price=D("100"))  # geçti — iptal edilmiş emre dolum
```

Aşama 8'in iddiası "idempotent istemci emir kimlikleri, kısmi/tam dolum, iptal ve terminal
durum korumaları". Koruma, çağıranın iyi niyetine bağlı olduğu sürece koruma değil.

**Önerilen düzeltme:** `ExecutionOrder`'ı `frozen=True` yapın ve motor durumu güncellerken
`dataclasses.replace` ile yeni nesne üretsin; ya da dışarıya salt-okunur bir görünüm
(`ExecutionOrderView`) döndürün.

---

### B-06 — Backtest motoru O(n²); gerçekçi veri hacminde kullanılamıyor

**Dosya:** `src/al_kripto/backtest/engine.py:88`

Motor her mumda `strategy.target_position(tuple(history))` çağırıyor ve `tuple(history)`
tüm geçmişin **tam kopyasını** çıkarıyor. Maliyet mum sayısının karesiyle büyüyor.

Ölçüm (hiçbir şey yapmayan strateji ile):

| Mum sayısı | Süre | Kat artışı |
|---:|---:|---:|
| 2.000 | 0,010 s | |
| 4.000 | 0,036 s | ×3,5 |
| 8.000 | 0,126 s | ×3,5 |
| 16.000 | 0,689 s | ×5,5 |
| 32.000 | 3,356 s | ×4,9 |

Kök neden doğrulandı: 32.000 mumda sadece `tuple(history)` kopyaları 3,35 saniye,
kopyasız aynı döngü 0,0014 saniye — maliyetin tamamı bu tek satırdan geliyor.

Bu eğriyle **1 yıllık 1 dakikalık veri (525.600 mum) tek sembol için ~15 dakika** sürer.
Parametre taraması veya çoklu sembol pratik olarak imkânsız hale gelir.

**Önerilen düzeltme:** `BacktestStrategy` protokolünü `Sequence[Candle]` alacak şekilde
gevşetin ve motor büyüyen listeyi salt-okunur bir görünüm olarak geçsin; ya da önceden
oluşturulmuş `series` üzerinde `series[: i + 1]` yerine indeksli erişim sunun. Değişmezliği
korumak isteniyorsa hafif bir `ReadOnlySequence` sarmalayıcısı O(1) maliyetle aynı garantiyi
verir.

---

## 5. Orta öncelikli bulgular

### B-07 — Risk kapısı hesap tükendiğinde karar veremiyor

**Dosya:** `src/al_kripto/risk/models.py:124`

`RiskContext` `equity > 0` şartını zorunlu kılıyor. `equity = 0` veya negatifken
`RiskValidationError` fırlatılıyor, dolayısıyla risk motoru **reddetme kararı bile
üretemiyor**. Fail-closed tasarım tam olarak en kötü anda kırılıyor; çağıranın her
`evaluate` çağrısını `try/except` ile sarmalaması gerektiği hiçbir yerde yazmıyor.

```python
RiskContext(equity=D("0"), start_of_day_equity=D("10000"), peak_equity=D("10000"), ...)
# RiskValidationError: equity must be finite and > 0.
```

**Öneri:** `equity >= 0` kabul edin ve `equity == 0` durumunu doğrudan
`REJECT` + yeni bir `ACCOUNT_DEPLETED` gerekçesine bağlayın.

---

### B-08 — `max_abs_correlation = 0` kabul ediliyor ama motoru kalıcı olarak kilitliyor

**Dosya:** `src/al_kripto/risk/models.py:78`, `src/al_kripto/risk/engine.py:103`

`RiskLimits` bu alanı `allow_zero=True` ile doğruluyor, yani `0` geçerli bir yapılandırma.
Motor ise `context.max_abs_correlation >= self._limits.max_abs_correlation` karşılaştırmasını
kullanıyor. Limit `0` olduğunda korelasyonu tamamen sıfır olan bir portföyde bile
`0 >= 0` doğru olduğu için **her talep reddediliyor**.

```python
limits = RiskLimits(..., max_abs_correlation=D("0"))  # kabul ediliyor
engine.evaluate(request, ctx(max_abs_correlation=D("0")))
# -> reject / ['correlation_limit']  (hiçbir talep asla geçmez)
```

Davranış fail-closed olduğu için tehlikeli değil, ancak sessizce kullanılamaz hale gelen
bir yapılandırma. Ya `0` reddedilmeli ya da karşılaştırma `>` olmalı.

---

### B-09 — On-chain tazelik denetimi ölçüm zamanına değil yayın zamanına bakıyor

**Dosya:** `src/al_kripto/onchain/regime.py:72`

`age_ms = decision_time_ms - observation.available_at_ms` — yaş yalnızca **yayın zamanından**
hesaplanıyor. `observed_at_ms` (metriğin gerçekte ölçüldüğü an) hiçbir yerde denetlenmiyor.
Sağlayıcı 90 gün önce ölçülmüş bir MVRV değerini bugün yayınlarsa gözlem "taze" sayılıyor:

```python
obs = MetricObservation(
    metric=MetricName.MVRV,
    value=D("1.5"),
    percentile=D("0.95"),
    observed_at_ms=NOW - 90 * 86_400_000,  # 90 günlük ölçüm
    available_at_ms=NOW - 1000,  # az önce yayınlandı
)
# 3 metrik ile -> regime = "overheated"   (unknown bekleniyordu)
```

README "yayın zamanı **ve** veri tazeliği kontrol edilmeden bir gözlem rejim hesabına
girmez" diyor; pratikte yalnızca yayın zamanı kontrol ediliyor.

**Öneri:** `OnChainRegimeConfig`'e `max_observation_age_ms` ekleyip
`decision_time_ms - observed_at_ms` üzerinden ikinci bir tazelik kapısı uygulayın.

---

### B-10 — Binance adaptörü sembolü istek göndermeden önce doğrulamıyor

**Dosya:** `src/al_kripto/market_data/binance.py:95`, `:127`, `:145`

Sembol yalnızca cevap ayrıştırılırken `Candle`/`Trade` modelleri tarafından doğrulanıyor.
Boş, küçük harfli veya tamamen geçersiz semboller için borsaya gerçek HTTP isteği çıkıyor:

```
symbol=''                  -> istek gönderildi: /api/v3/klines?symbol=&interval=1m&limit=500
symbol='btcusdt'           -> istek gönderildi
symbol='../../etc/passwd'  -> istek gönderildi (URL-encode edilmiş)
symbol='A'*50              -> istek gönderildi
```

URL kodlaması sayesinde enjeksiyon riski yok, ancak: (a) gereksiz istekler rate-limit
yasağına yol açabilir, (b) kullanıcı sembol hatası yerine anlamsız bir transport/payload
hatası görür, (c) proje genelinde `[A-Z0-9]{5,20}` deseni kullanılırken istek yolunda hiç
uygulanmıyor. Doğrulama yalnızca cevap modelleri (`Candle`, `Trade`, `OrderBookSnapshot`)
kurulurken devreye giriyor — yani istek çoktan gönderilmiş oluyor. `fetch_candles` boş liste
döndüğünde hiç model kurulmadığı için geçersiz sembol tamamen sessiz kalıyor.

**Öneri:** Üç `fetch_*` metodunun başında `_validate_symbol` çağırın.

---

### B-11 — Yinelenen `open_time_ms` veri katmanında yakalanmıyor

**Dosya:** `src/al_kripto/market_data/binance.py:272`

`_ensure_chronological` `key(left) > key(right)` karşılaştırmasını kullanıyor, yani **eşit**
zaman damgaları geçerli sayılıyor. Sağlayıcı aynı mumu iki kez döndürdüğünde veri katmanı
bunu kronolojik kabul ediyor:

```python
dup = [kline(t, t + 59_999, ...), kline(t, t + 59_999, ...)]  # aynı open_time
BinanceSpotMarketData(transport=lambda u, s: dup).fetch_candles("BTCUSDT", "1m")
# 2 mum döndü, hata yok
```

Backtest ve SMC motorları bunu kendi doğrulamalarında yakalıyor, ancak göstergeleri veya
veri katmanını doğrudan kullanan her tüketici mumu iki kez sayar. "Doğrulamalı veri katmanı"
iddiasıyla çelişiyor.

**Öneri:** Mumlar için `>=` karşılaştırması kullanın (işlemler için `>` doğru — aynı
milisaniyede birden fazla işlem normaldir).

---

### B-12 — Yürütme katmanında sembol doğrulaması diğer katmanlarla tutarsız

**Dosya:** `src/al_kripto/execution/models.py:44-45`

`ExecutionOrder` sembol için yalnızca "boşluk olmayan bir şey" istiyor. Proje genelindeki
`[A-Z0-9]{5,20}` deseninden tamamen farklı:

```
symbol='x'                -> kabul
symbol='btc usdt'         -> kabul
symbol='  A  '            -> kabul
symbol="'; DROP TABLE--"  -> kabul
```

Ayrıca sembol `strip()` ile kontrol edilip **strip edilmeden** saklanıyor, dolayısıyla
`" BTCUSDT "` ve `"BTCUSDT"` iki farklı sembol gibi davranıyor.

---

### B-13 — `Decimal` tipi çalışma zamanında zorlanmıyor; float sessizce kabul edilip sonra patlıyor

**Dosya:** `src/al_kripto/execution/models.py:46`

`mypy` `Decimal` bekliyor ancak çalışma zamanında hiçbir tip kontrolü yok. `float` miktar
kabul ediliyor, hata ancak dolum uygulanırken ortaya çıkıyor:

```python
e.submit(client_order_id="f1", symbol="BTCUSDT", side=Side.BUY, quantity=0.1)  # kabul
e.apply_fill("f1", quantity=0.1, price=100.0)
# TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'
```

Emir motora kaydedildikten sonra patladığı için motor tutarsız bir durumda kalıyor.
Finansal hesaplamalarda `float` kullanımının tam olarak engellenmesi gereken senaryo bu.

---

### B-14 — Hazırlık kanıtları doğrulanabilir değil

**Dosya:** `src/al_kripto/readiness/models.py:47-49`

`ReadinessEvidence.reference` yalnızca boş olmama şartına tabi. On bir kanıtın tamamı için
tek karakterlik `"x"` referansı, otomatik değerlendirmenin ulaşabileceği en üst sonuca
yetiyor:

```python
fake = [ReadinessEvidence(check=c, passed=True, reference="x") for c in REQUIRED_READINESS_CHECKS]
assess_production_readiness(fake).status  # ready_for_manual_review
```

Kanıt modelinde zaman damgası, geçerlilik süresi veya doğrulanabilir referans formatı
(commit SHA, CI çalıştırma URL'si, rapor kimliği) yok. Altı ay önceki bir paper çalışması
bugünkü kanıttan ayırt edilemiyor.

Kapının fail-closed davranışı doğru çalışıyor (tek eksik/başarısız kanıt `not_ready`
üretiyor, `live_trading_enabled` her zaman `False`), sorun kanıtın **kalitesi**.

**Öneri:** `ReadinessEvidence`'a `recorded_at_ms` ve `valid_until_ms` alanları ile referans
için asgari bir format doğrulaması ekleyin.

---

## 6. Yapısal bulgu

### B-15 — Modüller birbirine bağlanmamış; orkestrasyon katmanı yok

Depo içi import grafiği:

```
market_data   <- backtest, strategy, smc          (5 referans)
backtest      <- strategy                         (1 referans)
strategy      <- (yalnızca testler)               (1 referans)
config        <- __main__                         (1 referans)
onchain       <- yok                              (0 referans)
smc           <- yok                              (0 referans)
risk          <- yok                              (0 referans)
execution     <- yok                              (0 referans)
ml_research   <- yok                              (0 referans)
monitoring    <- yok                              (0 referans)
readiness     <- yok                              (0 referans)
```

Yedi modül hiçbir yerden çağrılmıyor. Somut sonuçları:

- **Risk motoru backtest yolunda hiç devrede değil.** Backtest her girişte nakdin
  %100'ünü kullanıyor (`backtest/engine.py:108`); pozisyon boyutlandırma yok, risk limitleri
  simülasyona hiç yansımıyor.
- **SMC ve on-chain çıktıları hiçbir stratejiye girmiyor.** `BaselineStrategy` yalnızca
  SMA/VWAP/oynaklık kullanıyor.
- **`Settings` veri katmanına ulaşmıyor.** `Settings.symbols` ve `Settings.exchange`
  yalnızca `__main__`'de yazdırılıyor; `BinanceSpotMarketData` yapılandırmadan hiç
  beslenmiyor.
- **Aşamalar arası hiçbir entegrasyon testi yok.** B-02 tam olarak bu yüzden fark
  edilmemiş: `tests/test_binance_market_data.py` içinde `BacktestEngine` hiç geçmiyor.

README'nin "%100 tamamlandı" ifadesi modül bazında doğru, ancak çalışan bir uçtan uca
sistem anlamına gelmiyor. Bu ayrımın README'de açıkça belirtilmesi ve bir sonraki adımın
orkestrasyon katmanı + entegrasyon testleri olması öneriliyor.

---

## 7. Düşük öncelikli bulgular

| Kod | Bulgu | Dosya |
|---|---|---|
| B-16 | Kill-switch açıkken (güvenli varsayılan durum) izleme `blocked` raporluyor; normal bekleme durumu gerçek arızadan ayırt edilemiyor. | `monitoring/engine.py:23-30` |
| B-17 | `Candle` modelinde `interval` alanı yok; 1m ve 1h mumları aynı seride karıştırılabiliyor ve hiçbir katman yakalamıyor (doğrulandı). | `market_data/models.py:31` |
| B-18 | Backtest lot/step-size yuvarlaması uygulamıyor; 26 ondalık basamaklı miktarlarla işlem yapıyor (`99.85017481269355332323848066`). Gerçekte gerçekleşemeyecek dolumlar sonucu iyimser gösteriyor. | `backtest/engine.py:108` |
| B-19 | Açık pozisyonla biten backtest'te round-trip üretilmediği için `win_rate` `0` görünüyor — "işlem yok" ile "hepsi zarar" ayırt edilemiyor. | `backtest/models.py:145-149` |
| B-20 | `exchange` değeri desteklenen borsalara karşı doğrulanmıyor; `kraken` kabul ediliyor ama böyle bir adaptör yok. | `config.py:49-50` |
| B-21 | `backtest.Side` ve `execution.Side` ayrı `StrEnum`'lar ancak `==` ile eşit çıkıyor (`Side.BUY == BSide.BUY` → `True`). Katmanlar arası sessiz karışıklık riski. | `backtest/models.py:25`, `execution/models.py:10` |
| B-22 | `OnChainRegimeConfig.minimum_metrics` hem "yeterli veri" hem "uzlaşı eşiği" olarak kullanılıyor. 4 metrikten 3'ü %99 yüzdelikte olsa bile tek nötr metrik sonucu `neutral`'a düşürüyor; uzlaşı eşiği ayrı ayarlanamıyor. | `onchain/regime.py:80-100` |
| B-23 | `OnChainRegimeAssessment` projedeki diğer tüm modellerin aksine hiç `__post_init__` doğrulaması içermiyor. | `onchain/regime.py:41-48` |

---

## 8. Doğrulanan olumlu davranışlar

Kullanım testinde aşağıdakiler beklendiği gibi çalıştı:

- **Determinizm:** Aynı girdi ile arka arkaya çalıştırılan backtest bit düzeyinde aynı
  `fills`, `round_trips` ve `final_equity` üretti.
- **Risk motoru maruziyeti asla büyütmüyor:** 3.000 rastgele istek/portföy kombinasyonunda
  `approved_notional > requested_notional` ihlali gözlenmedi; `APPROVE` kararları her zaman
  tam talep edilen tutarla ve gerekçesiz döndü.
- **SMC kararlılığı:** 150 rastgele fiyat serisinde (60 mum) istisna veya model doğrulama
  hatası oluşmadı; sıfır menzilli (doji) mumlar order-block üretimini kırmadı.
- **Fail-closed varsayılanlar:** `KillSwitch()` varsayılan olarak açık; canlı mod
  yapılandırması dört ayrı kilit gerektiriyor; `readiness_payload` her koşulda
  `live_trading_enabled: False` döndürüyor.
- **Yapılandırma doğrulaması:** Boş sembol listesi, kısa sembol, geçersiz mod, eksik
  testnet anahtarı, tek başına API anahtarı ve paper modda canlı bayrağı senaryolarının
  tamamı doğru şekilde reddedildi. `.env.example` olduğu gibi yüklendiğinde geçerli.
- **Gizli değer sızıntısı yok:** `Settings.redacted()` ve `dashboard_payload` çıktılarında
  API anahtarı/parolası bulunmuyor; `api_key`/`api_secret` alanları `repr=False`.
- **Gerçek emir yolu yok:** Depoda imzalı/özel Binance uç noktasına istek atan hiçbir kod
  yok; `BinanceSpotMarketData` yalnızca public market-data uç noktalarını, sadece HTTPS
  üzerinden kullanıyor.
- **Backtest olay sıralaması:** Sinyal en erken bir sonraki mumun açılışında uygulanıyor;
  kapanmamış mum reddi ve "aynı sembol" kuralı çalışıyor; strateji geçmişi `tuple` olarak
  aldığı için motorun iç durumunu bozamıyor.

---

## 9. Önerilen çalışma sırası

> Bu bölüm denetim anındaki öneridir. Sıranın tamamı bu dal üzerinde uygulanmış ve
> [§3](#3-düzeltme-sonrası-doğrulama)'te ölçümle doğrulanmıştır; burada kayıt için korunuyor.

1. **B-02** ve **B-15** birlikte: kapanmamış mum filtresi + veri→strateji→backtest→risk→izleme
   zincirini çalıştıran bir entegrasyon testi. Diğer entegrasyon hatalarını da açığa çıkarır.
2. **B-03** ve **B-07**: izleme ve risk katmanlarının uç durumlarda istisna yerine alarm/ret
   üretmesi. Fail-closed iddiasının doğrudan gereği.
3. **B-01**: SMC kırılım durum yönetimi — araştırma çıktılarının doğruluğunu etkiliyor.
4. **B-04**: `chronological_split` hizalaması — sessiz veri kaybı, ML sonuçlarını geçersiz kılar.
5. **B-05** ve **B-13**: yürütme katmanı değişmezlikleri ve tip zorlaması.
6. **B-06**: backtest ölçekleme — düzeltme küçük, kazanç büyük.
7. Kalan orta/düşük öncelikli bulgular.

### Bundan sonrası

Bulgular kapandığına göre sıradaki iş, düzeltmelerin kendisini denetlemek:

1. `orchestration` paketi için kullanım testi — bu rapordan sonra eklendi, hiç uçtan uca
   senaryodan geçmedi.
2. Yeni zorunlu alanların (`quantity_step`, `Candle.interval`, zaman sınırlı hazırlık kanıtı)
   gerçek bir paper çalışmasında ergonomik olup olmadığının ölçülmesi.
3. Bu raporun senaryolarının kalıcı bir regresyon paketine dönüştürülmesi; şu an tek seferlik
   betikler hâlinde ve depoda değiller.

---

## 10. Test kapsamı

| Senaryo grubu | Kontrol | İçerik |
|---|---:|---|
| S1 | 6 | Uçtan uca boru hattı, determinizm, sıfır maliyet, yatay piyasa, tek mum |
| S2 | 5 | Gerçek Binance payload'ı, kapanmamış mum, sembol doğrulama, boş cevap, duplike mum |
| S3 | 7 | Risk kapısı: normal/kırpma/kill-switch/korelasyon/bayat veri/tükenmiş hesap + 3.000 vakalık tarama |
| S4 | 9 | Yürütme kapsülleme, sembol/tip doğrulama, izleme uç durumları, ML bölme |
| S5 | 9 | SMC kararlılık taraması, boş girdi, doji, backtest strateji sözleşmesi, hassasiyet |
| S6 | 2 | SMC zıt yönlü kırılım araması (4.000 seri — bulgu yok, temiz) |
| S7 | 2 | SMC bayat seviye kaskadı ve order-block tekrarı |
| S8 | 8 | On-chain tazelik/uzlaşı, CLI, `.env.example`, 11 yapılandırma hatası senaryosu |
| S9 | 5 | Ölçekleme ölçümü, hazırlık kapısı kanıt kalitesi ve fail-closed davranışı |
| S10 | 5 | O(n²) kök neden, geçmiş değişmezliği, pozisyon boyutlandırma, interval karışımı |

**Toplam:** 57 kontrol + 7.150 rastgele girdi vakası.
