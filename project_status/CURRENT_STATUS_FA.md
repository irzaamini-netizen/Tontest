# وضعیت فعلی پروژه

آخرین به‌روزرسانی: 2026-11-19
شاخه: grok-benchmark-engine

## سه پیشنهاد تکمیل‌شده
1. **Baseline آرشیوی:** اسکریپت `tonsec_v020/scripts/run_baseline_archive.sh` + اعداد sandbox زیر
2. **گسترش شاهد vesting/telemint:** `equal_slices(sender, owner|vesting_sender)` به‌عنوان guard
3. **Tact structural parser:** `tonsec/tact_parser.py` (fun / get fun / receive) و اتصال به engine

## اعداد پس از equal_slices
| هدف | یافته | AUTH | diag |
|---|---:|---:|---:|
| wallet | 4 | 4 | 0 |
| token | 6 | 5 | 0 |
| tolk-bench | 6 | 2 | 0 |
| جمع | 16 | 11 | 0 |

### نسبت به قبل از این دور
- token: 10 → 6
- tolk-bench: 9 → 6 (vesting AUTH حذف شد)
- AUTH کل: 18 → 11

## AUTH باقی‌مانده
- wallet subscription plugin (4)
- discovery / minter-ICO / royalty / nft-item-draft send_msg
- telemint send_msg helper
- nft-collection royalty
