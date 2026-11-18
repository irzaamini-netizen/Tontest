# CONTINUE HERE

آخرین به‌روزرسانی: 2026-11-18

## حساب و مخزن

- GitHub: https://github.com/irzaamini-netizen/Tontest
- شاخه کار دستیار: `grok-benchmark-engine`
- مسیر محلی Termux: `/data/data/com.termux/files/home/tonsec-upgrade01-independent-audit/repository/tonsec_v020`
- پروژه‌های واقعی: `/data/data/com.termux/files/home/tonsec-real-projects`
- آخرین گزارش: `/data/data/com.termux/files/home/tonsec-baseline-3proj-after-asmfix`

نسخه محلی Termux از شاخه GitHub جلوتر است. موتور نصب‌شده روی Termux را با clone جدید جایگزین نکن.

## انجام‌شده (تکرار نشود)

1. نصب `tonsec` روی Termux و `tonsec doctor` = OK نسخه 0.2.0
2. Ground Truth فیکسچرها (P=1.0 / R=1.0 روی 15 نمونه)
3. بازگردانی 3 پروژه پین‌شده:
   - wallet-contract `68b56dc0f7f6a9d41a190a4c91f6dc68b18f0600`
   - token-contract `1182ad99413242f09925d50e70ccb7e0e09f94d4`
   - tolk-bench `57e1009743bfc19748caa95d76180d9e9793e4c5`
4. اصلاح lexer: افزودن `.` به عملگرهای FunC. بکاپ: `tonsec/lexer.py.bak-20261116-before-dot-fix`
   - unrecognized: 1195 → 0
   - پروژه ناقص: 13 → 2
5. اصلاح Tolk parser: پذیرش بدنه `asm`. بکاپ محلی: `tonsec/tolk_parser.py.bak-20261117-before-asm-body`
   - پروژه موفق: 18
   - پروژه ناقص: 1 (فقط JS/TS در token-contract)
   - diagnostic: 0
   - توابع: 472
   - یافته‌ها: 113 (بدون تغییر)
   - AUTH-001: 90
6. نمونه کیفی AUTH روی `ft/jetton-wallet.fc`:
   - `send_tokens` و `burn_tokens` اگر یافته بدهند مثبت کاذبند (قبل از send چک مالک دارند)
   - `receive_tokens` نامشخص تا مثبت کاذب (گارد master/کیف محاسبه‌شده)

## قوانین

- بدون بکاپ هیچ فایل هسته تغییر نشود
- کار تکراری انجام نشود
- اصلاح فقط بر اساس شواهد آزمون واقعی
- یافته heuristic را آسیب اثبات‌شده ندان

## اقدام بعدی

اگر قاعده AUTH روی `send_tokens` یا `burn_tokens` یافته می‌دهد، guard محلی `equal_slices(owner, sender)` قبل از send را به‌عنوان مثبت کاذب حذف کن. قبل از تغییر قاعده، یک یافته واقعی از گزارش محلی را بخوان.

مسیر گزارش نمونه: `tonsec_v020/benchmark/reports/AUTH_SAMPLE_REVIEW_20261118_FA.md` روی همین شاخه.
