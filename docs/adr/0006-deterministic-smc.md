# ADR-0006: Deterministik SMC araştırma motoru

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Bağlam

Swing, liquidity sweep, BOS/CHoCH, fair value gap ve order block kavramları manuel
yorumlandığında aynı grafik için farklı sonuçlar üretebilir. Araştırmada yeniden
üretilebilirlik ve look-ahead kontrolü gerekir.

## Karar

- Swing high/low, `swing_strength` kadar sol ve sağ komşuya karşı **strict** yerel
  ekstremum olarak tanımlanır.
- Bir swing, sağındaki doğrulama mumları kapanmadan kullanılabilir sayılmaz;
  `confirmed_index` ve `confirmed_at_ms` olay kaydında tutulur.
- Liquidity sweep, teyit edilmiş swing seviyesinin wick ile aşılması fakat mumun
  seviyenin tekrar içinde kapanmasıdır.
- BOS, teyit edilmiş swing seviyesinin kapanışla ilk kez aşılmasıdır. Son teyitli
  break yönünün tersindeki ilk break `CHoCH` olarak etiketlenir.
- Bullish FVG, üçüncü mumun low değerinin ilk mumun high değerinden yüksek olması;
  bearish FVG bunun tersidir.
- Order block, yapı kırılımından önceki ayarlanabilir lookback içindeki son ters renkli
  mum olarak tanımlanır. Bu tanım araştırma için deterministiktir; piyasa gerçeği veya
  kârlılık iddiası değildir.
- Aynı swing için ilk sweep ve ilk kapanış kırılımı kaydedilir; tekrar eden olaylar
  çoğaltılmaz.

## Bilimsel sınır

Bu motor, E-005 SMC hipotezini doğrulanmış kabul etmez. Üretilen olaylar yalnızca
test edilebilir özelliklerdir; stratejiye eklenmeleri out-of-sample ve maliyet duyarlı
karşılaştırmadan sonra değerlendirilecektir.

## Güvenlik

Motor yalnızca mum verisi okur. Borsa kimlik bilgisi, emir iletimi veya gerçek para
kullanımı içermez.
