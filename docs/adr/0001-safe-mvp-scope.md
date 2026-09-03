# ADR-0001: Güvenli MVP kapsamı

- Durum: Kabul edildi
- Tarih: 2026-09-03

## Bağlam

Araştırma raporu on-chain, SMC, ML, pair trading, Kelly ve DEX yürütmesini aynı
mimaride ele alıyor. Bunların tamamını ilk sürüme eklemek hata yüzeyini ve geçmişe
aşırı uyum riskini büyütür.

## Karar

MVP, BTC/USDT ve ETH/USDT spot `long/flat` stratejileriyle sınırlıdır. Önce paper,
sonra testnet çalışır. Temel strateji ve maliyet duyarlı backtest doğrulanmadan ML,
kaldıraç, short veya DEX yürütmesi eklenmez.

## Sonuçlar

- Daha az çalışma zamanı ve sermaye riski
- Basit benchmarklarla açık karşılaştırma
- CEX ve DEX risklerinin birbirine karışmaması
- İleri özelliklerin ölçülebilir kabul kapılarına bağlanması
