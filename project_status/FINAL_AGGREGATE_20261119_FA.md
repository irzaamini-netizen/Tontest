# گزارش جامع نشست 2026-11-19

شاخه: `grok-benchmark-engine`  
موتور: `tonsec_v020` 0.2.0  
آخرین commit موتور مرتبط: `3a3d14eb` (AUTH camelCase Tolk)

## خلاصه اجرایی

| هدف | فایل | توابع | یافته | partial | diagnostic |
|---|---:|---:|---:|---:|---:|
| wallet-contract @ 68b56dc | 3 | 17 | 4 | 0 | 0 |
| token-contract @ 1182ad9 | 31 | 88 | 10 | 12 | 0 |
| tolk-bench @ 57e1009 | 47 | 253 | 9 | 0 | 0 |
| **جمع** | **81** | **358** | **23** | **12** | **0** |

Diagnostic پارسر/lexer روی هر سه هدف: **صفر**.

## یافته‌ها بر اساس rule (جمع)

| Rule | تعداد | توضیح کوتاه |
|---|---:|---|
| TON-AUTH-001 | 18 | مسیر send بدون guard محلی شناخته‌شده یا caller محافظت‌شده |
| TON-ASSET-001 | 1 | opcode Jetton (INFO) |
| TON-ASSET-002 | 4 | opcode NFT (INFO) |
| REPLAY / TIME / EXT | 0 | پس از اصلاحات این نشست |

## AUTH باقی‌مانده (طبقه‌بندی)

### wallet-contract (4)
- `simple-subscription-plugin.fc`: forward_funds / request_payment / self_destruct
- تفسیر: مسیرهای عملیاتی plugin بدون الگوی owner/admin متعارف

### token-contract (9 AUTH)
- `jetton-discovery.fc` recv_internal
- `jetton-minter-ICO.fc` mint_tokens (caller/الگو با minter استاندارد فرق دارد)
- `send_royalty_params` در collection (عمومی)
- `nft-item-editable-DRAFT` send_msg (caller مختلط)
- `nft-sale.fc` buy ×4 (خرید عمومی با پرداخت)

### tolk-bench FunC (5 AUTH)
- `send_royalty_params`
- vesting: return_excess / send_message
- telemint: send_msg helper

### contracts_Tolk/*.tolk
- **AUTH: 0** پس از پشتیبانی senderAddress/ownerAddress/adminAddress

## اصلاحات موتور در این مسیر (شاخه)

1. نقطه در lexer FunC — LEX003
2. REPLAY: msg_seqno / stored_seqno / valid_since / valid_till
3. TIME/REPLAY: نادیده size:: و getter و save_data
4. AUTH: نقش پسوند، wallet-proof، plugin dict_get، nft roles
5. AUTH: caller هم‌فایل
6. AUTH: camelCase Tolk + calcAddressOfJettonWallet
7. pipeline: اسکن تک‌فایل

## محدودیت‌های شناخته‌شده
- تحلیل lexical + caller هم‌فایل؛ CFG/dataflow/TVM نیست
- partial روی JS/TS (legacy_heuristic) عمدی است
- baseline آرشیوی Termux با engine نهایی هنوز می‌تواند برای مقایسه تاریخی یک‌بار گرفته شود

## فایل همراه
- `project_status/final_aggregate_20261119.json`
