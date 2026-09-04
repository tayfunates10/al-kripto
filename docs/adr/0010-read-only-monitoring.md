# ADR-0010: Read-only izleme ve panel sınırı

- Durum: Kabul edildi
- Tarih: 2026-09-05

## Bağlam

Aşama 10; PnL, drawdown, veri tazeliği ve sistem sağlığını görünür kılmalıdır. İzleme
katmanının emir yürütme veya risk limitlerini değiştirme yetkisi olması güven sınırlarını
gereksiz yere genişletir.

## Karar

- İzleme girdisi immutable `MonitoringSnapshot` nesnesidir.
- Equity, günlük mark-to-market PnL, realized PnL, drawdown ve günlük kayıp raporlanır.
- Veri yaşı, heartbeat yaşı, mutabakat, kill-switch, açık emir sayısı ve işlenmemiş
  sistem hataları alarm üretir.
- Alarm eşikleri açıkça yapılandırılır; production yatırım değerleri varsayılan verilmez.
- Kritik alarm genel durumu `blocked`, yalnızca uyarı alarmı `degraded` yapar.
- Dashboard çıktısı JSON-safe ve read-only bir payload'dır; API anahtarı veya sır taşımaz.
- İzleme katmanı emir gönderemez, pozisyon boyutunu değiştiremez ve risk motorunu
  devre dışı bırakamaz.

## Sonuç

Panel veya başka bir gözlemleme arayüzü bu payload'ı tüketebilir. İleride HTTP/API
sunumu eklenirse aynı read-only sözleşme korunmalı ve yazma uçları ayrı güven sınırında
tasarlanmalıdır.
