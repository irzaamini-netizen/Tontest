# گزارش پیشرفت AUTH-001

تاریخ: 2026-11-19
شاخه: grok-benchmark-engine
موتور: tonsec_v020/tonsec/engine.py (اندازه تأییدشده: 10540 بایت)

## هدف
کاهش مثبت کاذب قاعده TON-AUTH-001 روی قراردادهای Jetton استاندارد، بدون اسکن سه‌پروژه‌ای تکراری.

## شاهد

فایل: token-contract/ft/jetton-wallet.fc (commit پین 1182ad9)

توابع:
- send_tokens: قبل از send، equal_slices(owner_address, sender_address)
- burn_tokens: همان الگوی owner/sender
- receive_tokens: equal_slices با jetton_master_address یا کیف محاسبه‌شده و sender_address

مشکل قبلی:
- \bowner\b و \bjetton_master\b به‌خاطر پسوند _address مرز کلمه نداشتند و guard شناخته نمی‌شد.

## اصلاح

AUTH_GUARD_ROLE:
```
\\b(owner|admin|authorized|is_authorized|role|jetton_master|minter)(?:_[A-Za-z0-9_]+)?\\b
```

بکاپ معتبر محلی Termux:
tonsec/engine.py.bak-20261119-before-role-suffix-fix

بکاپ ناقص روی گیت (استفاده نشود):
tonsec/engine.py.bak-20261118-before-master-guard (711 بایت)

## نتیجه شاهد

پس از اصلاح روی Termux:
AUTH-001 روی send_tokens / burn_tokens / receive_tokens = 0 → PASS

اسکن کامل سه‌پروژه برای این اصلاح تکرار نشد.
عدد قدیمی AUTH-001=90 دیگر معیار جاری نیست.

## محدودیت

- قاعده همچنان lexical prefix است؛ CFG و شاخه‌ها حل نمی‌شوند.
- فقط نقش‌های فهرست‌شده (+ پسوند اختیاری) شناخته می‌شوند.
- نصب Termux با clone خام جایگزین نشود؛ فقط فایل موتور همگام شود.

## اقدام بعدی پیشنهادی

1. شاهد جدید روی فایل/قاعده دیگر (مثلاً REPLAY یا TIME روی یک فایل مشخص).
2. یا در صورت درخواست صریح کاربر: اندازه‌گیری اثر AUTH روی baseline بدون تکرار بی‌دلیل اسکن قبلی.
3. به‌روزرسانی این گزارش پس از هر شاهد تازه.
