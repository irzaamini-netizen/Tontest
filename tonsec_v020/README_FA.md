# TON Security Engine 0.2.0

این نسخه یک تحلیل‌گر ایستای محافظه‌کار و مستقل است. توکن‌سازی، استخراج توابع با آکولادهای متوازن، قواعد تابع‌محور، شواهد مکانی و گزارش خام JSON/Markdown دارد. هنوز parser رسمی/کامل Tolk، FunC یا Tact، تحلیل بین‌تابعی، call graph، type resolution، state/dataflow یا اثبات exploitability ندارد.

## نصب در Termux
پس از استخراج ZIP:
```bash
pkg install python
cd مسیر/پوشه/استخراج‌شده
bash install_termux.sh
tonsec doctor
```

## اسکن فقط‌خواندنی
```bash
tonsec scan "$HOME/path-to-source" --out "$HOME/tonsec-report-01"
```
از مسیر خروجی جدید استفاده کن؛ پوشه غیرخالی بازنویسی نمی‌شود. خروجی شامل `ton_raw.json` و `ton_raw.md` است.

## مقایسه بعد از اتمام مستقل دو موتور
```bash
tonsec compare --sentinel /path/to/sentinel_raw.json --ton /path/to/ton_raw.json --out "$HOME/dual-comparison-01"
```
این نسخه فقط گزارش‌های خام آماده‌شده را مقایسه می‌کند. اتصال به API واقعی Sentinel هنوز پیاده‌سازی نشده است.

## قواعد
- TON-AUTH-001: ارسال پیام بدون guard قابل‌شناسایی در همان تابع
- TON-REPLAY-001: منطق امضا بدون نشانه محلی کنترل replay
- TON-TIME-001: valid_until بدون مقایسه زمانی قابل‌شناسایی
- TON-REPLAY-002: seqno بدون الگوی مقایسه/افزایش قابل‌شناسایی
- TON-EXT-001: extension/plugin همراه ارسال پیام بدون guard محلی
- TON-ASSET-001/002: نشانگر opcode Jetton/NFT، صرفاً INFO
- TON-CLIENT-001: نشانگر TON Connect/signData، صرفاً INFO

## تست توسعه‌دهنده
```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

## محدودیت و تفسیر
تمام یافته‌های امنیتی با classification=`UNKNOWN` صادر می‌شوند. HIGH به معنی شدت بالقوه مسیر بررسی است، نه اثبات آسیب‌پذیری. guardهای داخل helper/modifier/caller ممکن است دیده نشوند؛ بنابراین خروجی نیازمند بازبینی مهندسی است. این ابزار فقط فایل محلی را می‌خواند و هیچ شبکه، کیف‌پول، کلید، امضا یا تراکنشی را لمس نمی‌کند.
