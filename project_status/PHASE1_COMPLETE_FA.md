# فاز ۱ — موتور عملیاتی (تکمیل‌شده)

تاریخ: 2026-11-19
شاخه: grok-benchmark-engine

## تعریف تکمیل فاز ۱
موتور READ_ONLY قابل‌اجرا برای FunC/Tolk (و اسکلت Tact) با diagnostic صفر روی اهداف پین، قواعد AUTH/REPLAY/TIME/EXT مبتنی بر شاهد، و گزارش‌دهی پایدار.

## اعداد نهایی فاز ۱
| هدف | فایل | توابع | یافته | AUTH | diag |
|---|---:|---:|---:|---:|---:|
| wallet-contract | 3 | 17 | 4 | 4 | 0 |
| token-contract | 31 | 88 | 4 | 3 | 0 |
| tolk-bench | 47 | 253 | 5 | 1 | 0 |
| **جمع** | **81** | **358** | **13** | **8** | **0** |

## AUTH باقی‌مانده — بسته به‌عنوان یافتهٔ معنادار (نه باگ موتور)
1. wallet subscription plugin (4): طراحی plugin؛ مسیر external/payment بدون owner کلاسیک
2. jetton-discovery recv_internal: پاسخ عمومی provide_wallet_address
3. jetton-minter-ICO mint_tokens: مسیر خرید عمومی عمدی
4. nft-item-editable DRAFT send_msg: caller مختلط
5. telemint send_msg: caller مختلط (حراج/عمومی/مالک)

## اقلام خارج از فاز ۱ (فاز بعد — عمداً باز)
- CFG / dataflow کامل
- تحلیل TVM bytecode
- مقیاس صدها مخزن production
- Tact compiler-grade

این اقلام مسیر جدا هستند و در تعریف فاز ۱ ناقص محسوب نمی‌شوند.
