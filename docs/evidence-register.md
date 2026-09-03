# Kanıt ve hipotez kaydı

Bu kayıt, araştırma raporundaki iddiaların doğrudan strateji kuralına dönüşmesini
engeller. Her iddia, birincil kaynak, veri testi ve örneklem dışı doğrulama olmadan
`kabul edildi` durumuna geçemez.

| ID | İddia / konu | İlk değerlendirme | Proje kararı | Durum |
|---|---|---|---|---|
| E-001 | Hiçbir strateji %100 kazanma garantisi veremez | Temel risk ilkesiyle uyumlu | Kâr garantisi ve kesin sinyal dili yasak | Kabul |
| E-002 | MVRV/SOPR makro rejim sinyali taşır | BTC için test edilebilir | Sabit eşik değil, geçmişe duyarlı özellik | Doğrulanacak |
| E-003 | Puell Multiple madenci stresini ölçer | PoW/BTC odaklıdır | Diğer tokenlere genellenmeyecek | Doğrulanacak |
| E-004 | NVT değerleme sinyalidir | Formül ve veri kapsamı sağlayıcıya bağlı | Koddan önce referans örnekleri yazılacak | Doğrulanacak |
| E-005 | SMC yapıları giriş zamanlamasını iyileştirir | Tanımlar öznel olabilir | Swing/sweep/BOS/FVG kuralları deterministik olacak | Hipotez |
| E-006 | Kelly optimum pozisyon büyüklüğü verir | Olasılık hatasına aşırı duyarlı | Yalnızca OOS sonrası, kesirli ve sert risk tavanlı | Kısıtlı |
| E-007 | ModSharpeLoss/GA performansı artırır | Araştırma adayı | Temel stratejiden sonra deneysel katman | Ertelendi |
| E-008 | OOS ve çoklu test düzeltmesi overfit'i azaltır | Güçlü yöntemsel dayanak | Walk-forward, DSR/PBO ve hassasiyet testi zorunlu | Kabul |
| E-009 | Flashbots sandviç saldırısını azaltır | Ethereum/DEX kapsamına özgü | CEX MVP'sine uygulanmayacak | Ertelendi |
| E-010 | Bazı enerji/altın tokenleri güvenli limandır | Likidite ve ihraççı riski taşır | Kanıtlanmadan hedge kabul edilmeyecek | Reddedildi |

## Başlangıç kaynakları

- [Gemini araştırma raporu](https://gemini.google.com/share/26b86d378a26?skid=1edc5653-e3ff-49fa-b763-c6e83b9263cf)
- [Binance Spot Testnet belgeleri](https://developers.binance.com/en/docs/products/spot/testnet/general-info)
- [Glassnode API belgeleri](https://docs.glassnode.com/basic-api/api)
- [CryptoQuant API belgeleri](https://docs.cryptoquant.com/)
- [Flashbots Protect belgeleri](https://docs.flashbots.net/flashbots-protect/overview)
- [Deflated Sharpe Ratio makalesi](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)

## Bir hipotezin kabul kapısı

1. Formül ve zaman damgası semantiği birincil kaynaktan doğrulanır.
2. Veri revizyonu, eksik veri ve yayın gecikmesi belgelenir.
3. Gelecek bilgisi sızıntısını engelleyen test fixture'ı yazılır.
4. Kronolojik train/validation/test ayrımı uygulanır.
5. Komisyon, kayma ve gecikme sonrası OOS sonuç raporlanır.
6. Basit benchmark ve buy-and-hold ile karşılaştırılır.
7. Parametre hassasiyeti, rejim ayrımı ve Monte Carlo testi geçilir.
