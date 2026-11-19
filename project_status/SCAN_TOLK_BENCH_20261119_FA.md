# اسکن tolk-bench @ 57e1009 — 2026-11-19

## قبل از اصلاح size::/getter
- files: 47
- functions: 253
- findings: 37
- partial: 0
- diagnostics: 0
- by_rule: AUTH-001=25, ASSET-002=3, REPLAY-002=5, TIME-001=1, REPLAY-001=2, ASSET-001=1

## بعد از اصلاح engine (commit 0b62edc9)
- findings: 33
- TIME-001: 0 (حذف FP مربوط به size::valid_until)
- REPLAY-002: 2 (قبلاً 5؛ getterهای seqno حذف شدند)
- باقی‌مانده REPLAY-002:
  - wallet_v5.fc:verify_c5_actions
  - vesting_wallet.fc:save_data
- REPLAY-001: 2 (telemint signed cmd)
- AUTH-001: 25 (helperها و مسیرهای Tolk بدون guard محلی شناخته‌شده)

## تفسیر
- parser/lexer روی این مجموعه diagnostic صفر دارد.
- بخش عمده AUTH باقی‌مانده محدودیت تحلیل function-local است.
