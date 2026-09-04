# ADR-0007: Merkezi fail-closed risk kapısı

- Durum: Kabul edildi
- Tarih: 2026-09-04

## Amaç

Strateji, on-chain veya SMC katmanlarının hiçbiri kendi başına maruziyet artırmamalıdır.
Her exposure-increasing istek bağımsız ve devre dışı bırakılamayan merkezi risk
kapısından geçmelidir.

## Karar

- `RiskLimits` sayısal değerleri zorunlu girdidir; kütüphane canlı kullanım için
  gizli veya tavsiye niteliğinde varsayılan limitler seçmez.
- Kill-switch varsayılan olarak **engaged** oluşturulur. Devre dışı bırakılması diğer
  kontrolleri atlamaz; her değerlendirmede tekrar kontrol edilir.
- Mutabakat hatası, eski piyasa verisi, günlük kayıp sınırı, toplam drawdown sınırı,
  maksimum açık pozisyon ve korelasyon sınırı yeni/increased exposure için fail-closed
  `reject` üretir.
- İşlem başına stop riski, toplam maruziyet veya sembol maruziyeti istenen boyuttan
  daha küçük bir tutara izin veriyorsa motor yalnızca `reduce` edebilir; hiçbir koşulda
  stratejinin istediğinden daha büyük boyut üretemez.
- Risk bütçesi mevcut equity üzerinden hesaplanır; kayıp sonrası otomatik risk büyütme
  ve martingale davranışı yoktur.
- Kararlar `approve`, `reduce`, `reject` ve makine tarafından denetlenebilir nedenler
  ile kaydedilir.

## Sınırlar

Bu aşama gerçek emir iletmez ve herhangi bir borsa API anahtarı kullanmaz. Korelasyon
hesabının kendisi veri/portföy katmanının sorumluluğudur; risk motoru point-in-time
`max_abs_correlation` değerini sınırla karşılaştırır.

Canlıya özgü limitlerin seçimi bu ADR'nin kapsamı değildir ve insan onayı gerektirir.
