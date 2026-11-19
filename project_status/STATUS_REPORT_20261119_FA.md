# گزارش وضعیت پروژه — مراحل و نتایج

**تاریخ:** 2026-11-19  
**مخزن:** https://github.com/irzaamini-netizen/Tontest  
**شاخه:** `grok-benchmark-engine`  
**موتور:** `tonsec_v020` نسخه 0.2.0  
**حالت:** READ_ONLY_STATIC_ANALYSIS

---

## ۱. خلاصه اجرایی

فاز عملیاتی موتور (فاز ۱) روی سه هدف پین‌شده تکمیل شده است:

| متریک | مقدار |
|---|---:|
| فایل تحلیل‌شده | ۸۱ |
| تابع استخراج‌شده | ۳۵۸ |
| یافته کل | ۱۳ |
| diagnostic پارسر/lexer | **۰** |
| پروژه با partial (JS/TS) | ۱۲ فایل در token-contract |

یافته‌های باقی‌مانده AUTH عمدتاً مسیرهای عمومی یا طراحی خاص (plugin / ICO / discovery / telemint) هستند، نه باگ شناخته‌شدهٔ قواعد فعلی.

---

## ۲. مسیرها و پین‌ها

| منبع | مسیر / پین |
|---|---|
| موتور | `tonsec_v020/` |
| وضعیت | `project_status/` |
| wallet-contract | `68b56dc0f7f6a9d41a190a4c91f6dc68b18f0600` |
| token-contract | `1182ad99413242f09925d50e70ccb7e0e09f94d4` |
| tolk-bench | `57e1009743bfc19748caa95d76180d9e9793e4c5` |

---

## ۳. مراحل انجام‌شده (به ترتیب منطقی)

### ۳.۱ زیرساخت اجرایی
- نصب/doctor نسخه 0.2.0
- `scan` / `run` / batch و پشتیبانی اسکن **تک‌فایل**
- گزارش `ton_raw.json` / `ton_raw.md`

### ۳.۲ پارسر و lexer
| مورد | نتیجه |
|---|---|
| نقطه `.` در FunC lexer | unrecognized: ۱۱۹۵ → ۰ |
| بدنه `asm` در Tolk | diagnostic مربوط حذف |
| پارسر ساختاری FunC / Tolk | فعال |
| اسکلت Tact (`fun` / `get fun` / `receive` / `external`) | فعال + برچسب `tact_structural` |

### ۳.۳ قواعد امنیتی (مبتنی بر شاهد)
| قاعده | وضعیت |
|---|---|
| TON-AUTH-001 | نقش/پسوند، camelCase Tolk، equal_slices، slice_data_equal plugin، wallet-proof، caller هم‌فایل و same-project |
| TON-REPLAY-001/002 | seqno/msg_seqno/stored_seqno؛ کاهش FP روی getter و save_data |
| TON-TIME-001 | valid_until/since/till |
| TON-EXT-001 | plugin + dict_get?/success? |
| TON-ASSET-001/002 | INFO — opcode |
| TON-CLIENT-001 | INFO — TON Connect |

### ۳.۴ ارزیابی روی پروژه‌های واقعی
اسکن نهایی sandbox با موتور جاری:

| هدف | فایل | توابع | یافته | AUTH | partial | diag |
|---|---:|---:|---:|---:|---:|---:|
| wallet-contract | ۳ | ۱۷ | ۴ | ۴ | ۰ | ۰ |
| token-contract | ۳۱ | ۸۸ | ۴ | ۳ | ۱۲ | ۰ |
| tolk-bench | ۴۷ | ۲۵۳ | ۵ | ۱ | ۰ | ۰ |
| **جمع** | **۸۱** | **۳۵۸** | **۱۳** | **۸** | **۱۲** | **۰** |

### ۳.۵ interprocedural جزئی
- وضعیت pipeline: `PARTIAL_SAME_PROJECT_CALLERS`
- اگر همه callerهای یک تابع در کل پروژه قبل از فراخوانی guard داشته باشند، AUTH helper حذف می‌شود

---

## ۴. یافته‌های AUTH باقی‌مانده (مستند)

| محل | تفسیر |
|---|---|
| `simple-subscription-plugin.fc` (۴) | طراحی plugin؛ external/payment بدون owner کلاسیک |
| `jetton-discovery.fc` recv_internal | پاسخ عمومی provide_wallet_address |
| `jetton-minter-ICO.fc` mint_tokens | مسیر خرید عمومی عمدی |
| `nft-item-editable-DRAFT.fc` send_msg | caller مختلط / DRAFT |
| telemint `common.fc` send_msg | caller مختلط (حراج/عمومی/مالک) |

Royalty عمومی (`send_royalty_params`) از AUTH حذف شده است.

---

## ۵. commitهای کلیدی مرتبط

| موضوع | نمونه commit / یادداشت |
|---|---|
| نقطه lexer | مسیر قبلی شاخه |
| AUTH camelCase Tolk | `3a3d14eb` |
| equal_slices + tact wire | `4b55ff32` |
| pipeline interprocedural / tact label | `022710ad` |
| slice_data_equal + royalty skip | `0ebb7ca8` / اصلاح typo `9a3cbe87` |
| اسناد فاز ۱ | `PHASE1_COMPLETE_FA.md` |

---

## ۶. درصد پیشرفت تقریبی نسبت به مأموریت کامل

| لایه | درصد تقریبی |
|---|---:|
| زیرساخت اجرایی | ~۸۵٪ |
| FunC/Tolk عملیاتی | ~۷۵٪ |
| قواعد مبتنی بر شاهد | ~۷۰٪ |
| آزمون واقعی پین | ~۶۵٪ |
| Tact ساختاری اولیه | ~۳۰٪ |
| CFG / dataflow / TVM | ~۵–۱۰٪ |
| مقیاس سازمانی | ~۱۰٪ |
| **کل تا مأموریت نهایی** | **حدود ۵۰–۵۵٪** |

---

## ۷. فاز ۲ (باز — خارج از فاز ۱)

1. کنترل‌جریان و dataflow واقعی  
2. تحلیل bytecode TVM  
3. غنی‌سازی Tact تا نزدیک compiler-grade  
4. baseline آرشیوی روی Termux با موتور همگام  
5. مقیاس batch روی مخازن زیاد  

اسکریپت آماده baseline:  
`tonsec_v020/scripts/run_baseline_archive.sh`

---

## ۸. قوانین ادامه کار

- کار انجام‌شده تکرار نشود  
- بدون بکاپ فایل هسته تغییر نکند  
- اصلاح فقط با شاهد واقعی  
- قبل از کار جدید: این گزارش و `CURRENT_STATUS_FA.md` خوانده شود  

---

*این فایل منبع رسمی گزارش وضعیت مراحل و نتایج در تاریخ فوق است.*
