# وضعیت فعلی پروژه

آخرین به‌روزرسانی: 2026-11-19
شاخه: grok-benchmark-engine
موتور: tonsec_v020 / 0.2.0
آخرین commit موتور: 36056a85

## اولویت‌های مهم انجام‌شده در این دور
1. AUTH هم‌فایل: اگر همه callerهای همان فایل قبل از فراخوانی guard داشته باشند، helper flag نمی‌شود
2. REPLAY: `valid_since` / `valid_till` به‌عنوان کنترل زمانی/replay
3. حذف FP کامنت و getter و `save_data`/`load_data` برای REPLAY-002
4. اسکن مجدد wallet / token / tolk-bench

## نتایج اسکن (پس از 36056a85)

| هدف | فایل | توابع | یافته | partial | diag |
|---|---:|---:|---:|---:|---:|
| wallet-contract | 3 | 17 | 4 | 0 | 0 |
| token-contract | 31 | 88 | 10 | 12 | 0 |
| tolk-bench | 47 | 253 | 21 | 0 | 0 |

### تغییرات نسبت به قبل از این دور
- token AUTH: 14 → 9 (mint/deploy/send_msg با caller محافظت‌شده حذف شدند)
- tolk یافته: 33 → 21
- REPLAY-001/002 روی tolk-bench: 0

### یافته‌های عمداً باقی‌مانده
- wallet subscription plugin (مسیرهای بدون guard نقش متعارف)
- nft-sale `buy` (خرید عمومی با پرداخت)
- send_royalty_params عمومی
- مسیرهای Tolk با الگوی guard متفاوت از FunC throw_unless

## باقی‌مانده غیرمسدودکننده
- baseline رسمی Termux یک‌بار با engine فعلی برای مقایسه عددی آرشیوی
- گسترش AUTH برای الگوی Tolk (assert/throw متفاوت)
- CFG / dataflow / TVM
