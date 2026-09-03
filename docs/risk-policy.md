# Risk politikası

Bu belge, strateji performansından bağımsız zorunlu güvenlik sınırlarını tanımlar.
Sayısal limitler canlı kullanımdan önce ayrı bir ADR ile belirlenecektir.

## Değiştirilemez başlangıç kuralları

- Varsayılan işlem modu `paper`dır.
- İlk canlı ürün spot ve `long/flat` çalışır.
- Kaldıraç, borçlanma, futures, options ve para çekme desteklenmez.
- Martingale ve kayıp sonrası otomatik risk büyütme yasaktır.
- Günlük zarar, toplam drawdown, açık pozisyon ve korelasyon sınırları risk
  motorunda merkezi olarak uygulanır.
- Eski veri, saat farkı, bağlantı belirsizliği veya mutabakat hatasında yeni pozisyon
  açılmaz.
- Risk motoru devre dışı bırakılamaz; strateji yalnızca daha küçük risk isteyebilir.
- Manuel kill-switch her zaman kullanılabilir olmalıdır.

## Kelly kullanımı

Tam Kelly kullanılmaz. Kesirli Kelly ancak yeterli OOS örneklem, olasılık kalibrasyonu
ve paper trading sonrasında aday olabilir. Hesaplanan değer; işlem başına risk,
varlık tahsis ve toplam portföy sınırlarının tamamından daha düşük olmalıdır.

## Canlıya geçiş kapısı

- Gelecek bilgisi sızıntısı testleri geçmeli.
- Komisyon ve gerçekçi kayma sonrası OOS beklenen değer pozitif olmalı.
- İki kat işlem maliyeti stresinde tanımlanan kayıp sınırı aşılmamalı.
- Boğa, ayı ve yatay rejimler ayrı raporlanmalı.
- Parametrelerin küçük değişimi stratejiyi çökertmemeli.
- Testnet/paper emir ve bakiye mutabakatı hatasız çalışmalı.
- Kill-switch, tekrar gönderim ve kısmi dolum senaryoları test edilmeli.
- Canlı dağıtım için insan onayı alınmalı.
