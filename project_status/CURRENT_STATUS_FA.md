# وضعیت فعلی پروژه

آخرین به‌روزرسانی: 2026-11-19
شاخه: `grok-benchmark-engine`
موتور: `tonsec_v020` نسخه 0.2.0

## مسیرها
- مخزن: https://github.com/irzaamini-netizen/Tontest
- شاخه کاری: `grok-benchmark-engine`
- موتور: `tonsec_v020/`
- وضعیت: `project_status/`
- پروژه‌های پین (محلی/Termux):
  - wallet-contract @ `68b56dc0f7f6a9d41a190a4c91f6dc68b18f0600`
  - token-contract @ `1182ad99413242f09925d50e70ccb7e0e09f94d4`
  - tolk-bench @ `57e1009743bfc19748caa95d76180d9e9793e4c5`

## انجام‌شده (تجمیع)
1. نصب و doctor روی Termux
2. بازگردانی ۳ پروژه واقعی با commit پین
3. اصلاح lexer: عملگر `.` در FunC (رفع LEX003)
4. اصلاح tolk_parser برای بدنه `asm`
5. AUTH: پسوند نقش (`owner_address` و مشابه)، wallet-proof، plugin dict_get، nft_owner/marketplace/collection
6. REPLAY: `msg_seqno` / `stored_seqno`
7. EXT: guard نصب plugin
8. pipeline: اسکن تک‌فایل
9. اسکن اجرایی wallet + token در نشست 2026-11-19

## نتایج اسکن نشست (پس از نقطه در lexer)

| هدف | فایل | توابع | یافته | partial | diagnostic |
|---|---:|---:|---:|---:|---:|
| wallet-contract | 3 | 17 | 4 | 0 | 0 |
| token-contract | 31 | 88 | 15 | 12 | 0 |

### wallet-contract — یافته‌ها
- فقط `TON-AUTH-001` روی `simple-subscription-plugin.fc` (۴ مورد: forward_funds, request_payment, self_destruct)
- `wallet-v4-code.fc`: بدون AUTH و بدون diagnostic

### token-contract — یافته‌ها
- `TON-AUTH-001`: ۱۴ (helperهای mint/deploy/send_msg و مسیر buy عمومی nft-sale)
- `TON-ASSET-002`: ۱
- partial=۱۲ عمدتاً فایل‌های JS/TS با legacy_heuristic
- diagnostic=۰

## انجام‌نشده / محدودیت شناخته‌شده
- تحلیل بین‌تابعی: helper بدون guard محلی هنوز AUTH می‌دهد حتی اگر caller guard داشته باشد
- مسیر buy در nft-sale (پرداخت عمومی) عمداً بدون owner-guard است
- tolk-bench در این نشست کامل اسکن نشد (مشکل unpack آرشیو در sandbox)
- baseline کامل ۱۹ زیرپروژه روی Termux پس از آخرین engine روی گیت باید یک‌بار تکرار شود برای مقایسه عددی نهایی

## قوانین
- بدون بکاپ فایل هسته تغییر نکند
- کار تکراری انجام نشود
- اصلاح فقط بر اساس شاهد
