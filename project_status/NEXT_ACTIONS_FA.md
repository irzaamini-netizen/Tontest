# اقدامات بعدی

## اولویت
1. یک‌بار baseline کامل روی Termux با engine فعلی گیت (شامل نقطه + AUTH/REPLAY/EXT)
2. مقایسه عددی با baseline قبل از نقطه (diagnostic و partial)
3. فقط با شاهد جدید: تصمیم درباره AUTH روی helper (mint_tokens/deploy/send_msg) و buy عمومی
4. اسکن tolk-bench پین در صورت نیاز

## تکرار نشود
- اصلاح دوباره نقطه lexer
- اصلاح دوباره asm body
- گسترش دوباره همان نقش‌های owner/admin/marketplace بدون شاهد تازه

## دستور همگام‌سازی Termux
```bash
cd "$HOME/tonsec-upgrade01-independent-audit/repository/tonsec_v020"
cp tonsec/engine.py "tonsec/engine.py.bak-$(date +%Y%m%d%H%M%S)"
cp tonsec/lexer.py "tonsec/lexer.py.bak-$(date +%Y%m%d%H%M%S)"
cp tonsec/pipeline.py "tonsec/pipeline.py.bak-$(date +%Y%m%d%H%M%S)"
curl -fsSL "https://raw.githubusercontent.com/irzaamini-netizen/Tontest/grok-benchmark-engine/tonsec_v020/tonsec/engine.py" -o tonsec/engine.py
curl -fsSL "https://raw.githubusercontent.com/irzaamini-netizen/Tontest/grok-benchmark-engine/tonsec_v020/tonsec/lexer.py" -o tonsec/lexer.py
curl -fsSL "https://raw.githubusercontent.com/irzaamini-netizen/Tontest/grok-benchmark-engine/tonsec_v020/tonsec/pipeline.py" -o tonsec/pipeline.py
# در صورت نصب site-package:
cp tonsec/engine.py tonsec/lexer.py tonsec/pipeline.py /data/data/com.termux/files/usr/lib/tonsec/ 2>/dev/null || true
```
