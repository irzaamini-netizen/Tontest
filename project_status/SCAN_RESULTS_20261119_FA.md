# نتایج اسکن نشست 2026-11-19

منبع: اجرای `scan_project` روی آرشیوهای پین‌شده در محیط اجرایی، پس از اصلاح lexer (`.` در FunC).

## wallet-contract @ 68b56dc

| متریک | مقدار |
|---|---:|
| files_analyzed | 3 |
| functions_extracted | 17 |
| findings_total | 4 |
| files_partial | 0 |
| diagnostics_total | 0 |

### یافته‌ها
| rule | file | line | function |
|---|---|---:|---|
| TON-AUTH-001 | func/simple-subscription-plugin.fc | 67 | forward_funds |
| TON-AUTH-001 | func/simple-subscription-plugin.fc | 80 | forward_funds |
| TON-AUTH-001 | func/simple-subscription-plugin.fc | 95 | request_payment |
| TON-AUTH-001 | func/simple-subscription-plugin.fc | 109 | self_destruct |

### تفسیر کوتاه
- wallet-v4 پس از اصلاحات REPLAY/EXT/AUTH برای مسیرهای استاندارد بدون یافته AUTH است.
- plugin اشتراک هنوز مسیرهای send بدون guard نقش/هویت متعارف دارد.

## token-contract @ 1182ad9

| متریک | مقدار |
|---|---:|
| files_analyzed | 31 |
| functions_extracted | 88 |
| findings_total | 15 |
| files_partial | 12 |
| diagnostics_total | 0 |

### یافته‌ها بر اساس rule
- TON-AUTH-001: 14
- TON-ASSET-002: 1

### فهرست AUTH (خلاصه)
| file | function |
|---|---|
| ft/jetton-discovery.fc | recv_internal |
| ft/jetton-minter-ICO.fc | mint_tokens |
| ft/jetton-minter-discoverable.fc | mint_tokens |
| ft/jetton-minter.fc | mint_tokens |
| nft/nft-collection-editable.fc | deploy_nft_item, send_royalty_params |
| nft/nft-collection.fc | deploy_nft_item, send_royalty_params |
| nft/nft-item-editable-DRAFT.fc | send_msg |
| nft/nft-item.fc | send_msg |
| nft/nft-sale.fc | buy (۴ نقطه send) |

### partial
عمدتاً wrappers/scripts TypeScript با `legacy_heuristic` — diagnostic پارسر FunC/Tolk صفر است.

## فایل JSON همراه
- `project_status/session_scan_summary_20261119.json`
