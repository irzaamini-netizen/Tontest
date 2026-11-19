# وضعیت فعلی پروژه

آخرین به‌روزرسانی: 2026-11-19 (ادامه شب)
شاخه: `grok-benchmark-engine`
موتور: `tonsec_v020` نسخه 0.2.0

## مسیرها
- مخزن: https://github.com/irzaamini-netizen/Tontest
- وضعیت: `project_status/`
- موتور: `tonsec_v020/`

## انجام‌شده
1. نصب/doctor
2. پروژه‌های پین wallet / token / tolk-bench
3. lexer نقطه FunC (گیت: fccbfcc5)
4. tolk asm body
5. AUTH نقش پسوند، wallet-proof، plugin، nft_owner/marketplace/collection
6. REPLAY msg_seqno/stored_seqno
7. pipeline اسکن تک‌فایل
8. اسکن wallet+token (جزئیات در SCAN_RESULTS_20261119_FA.md)
9. اسکن tolk-bench 47 فایل / 253 تابع / diagnostic 0
10. کاهش FP: TIME/REPLAY با نادیده گرفتن size:: و getter خالص (0b62edc9)

## نتایج کلیدی
| هدف | فایل | توابع | یافته | partial | diag |
|---|---:|---:|---:|---:|---:|
| wallet-contract | 3 | 17 | 4 | 0 | 0 |
| token-contract | 31 | 88 | 15 | 12 | 0 |
| tolk-bench (پس از اصلاح TIME/REPLAY) | 47 | 253 | 33 | 0 | 0 |

## اقدام بعدی
- baseline یک‌بار روی Termux با engine فعلی
- AUTH helper فقط با شاهد جدید
- بررسی REPLAY-001 telemint و REPLAY-002 باقی‌مانده با شاهد
