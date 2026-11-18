# CONTINUE HERE

آخرین به‌روزرسانی: 2026-11-18 14:40 +04
مخزن: https://github.com/irzaamini-netizen/Tontest
شاخه: grok-benchmark-engine
مسیر Termux: /data/data/com.termux/files/home/tonsec-upgrade01-independent-audit/repository/tonsec_v020

## قانون ثبت
هر کار جدید، قبل از پایان همان نشست، باید در این فایل ثبت شود.
حساب دیگر فقط همین فایل را می‌خواند. گفتگو منتقل نمی‌شود.
کار انجام‌شده تکرار نشود. بدون بکاپ فایل هسته تغییر نکن.

## خطای ثبت

2026-11-18: دستور ادامه به حساب دیگر داده شد، اما نتیجه آن حساب روی گیت نبود.
بررسی همین روز: آخرین commit شاخه هنوز 72c5f3a بود. شاخه جدید هم نبود.
پس کار حساب دیگر، اگر انجام شده باشد، فقط محلی مانده و اینجا دیده نمی‌شود.

## انجام‌شده

1. نصب tonsec روی Termux. doctor = OK. نسخه 0.2.0
2. Ground truth فیکسچر: P=1.0 / R=1.0 روی 15 نمونه
3. سه پروژه پین:
   - wallet-contract 68b56dc0f7f6a9d41a190a4c91f6dc68b18f0600
   - token-contract 1182ad99413242f09925d50e70ccb7e0e09f94d4
   - tolk-bench 57e1009743bfc19748caa95d76180d9e9793e4c5
4. lexer: نقطه به عملگر FunC اضافه شد. بکاپ lexer.py.bak-20261116-before-dot-fix
   - unrecognized 1195 -> 0
   - پروژه ناقص 13 -> 2
5. parser: بدنه asm پذیرفته شد. بکاپ tolk_parser.py.bak-20261117-before-asm-body
   - موفق 18 / ناقص 1 / diagnostic 0 / توابع 472 / یافته 113
   - ناقص باقی فقط JS/TS در token-contract
6. نمونه AUTH: benchmark/reports/AUTH_SAMPLE_REVIEW_20261118_FA.md
7. بررسی قاعده در tonsec/engine.py:
   throw_unless که هم owner و هم sender داشته باشد از قبل guard است.
   send_tokens و burn_tokens را دوباره اصلاح نکن.

## اقدام بعدی

فقط receive_tokens: گارد فرستنده master یا کیف محاسبه‌شده را قاعده نمی‌بیند.
قبل از تغییر قاعده، یک یافته واقعی AUTH-001 از گزارش
/data/data/com.termux/files/home/tonsec-baseline-3proj-after-asmfix
خوانده شود. اگر همان الگو بود، بکاپ بگیر و فقط همان را اضافه کن.
اسکن کامل را بی‌دلیل تکرار نکن.
