# اقدامات بعدی

## انجام نشود (تکرار ممنوع)
- اصلاح دوباره نقطه lexer / asm body / camelCase Tolk همین الگوها
- اسکن بی‌دلیل همان سه هدف بدون تغییر موتور

## پیشنهادی
1. روی Termux: همگام‌سازی engine از گیت و یک baseline آرشیوی
2. فقط با شاهد جدید: گسترش AUTH برای الگوهای خاص (vesting whitelist، telemint)
3. Tact structural parser
4. محصول‌سازی batch در مقیاس

## همگام‌سازی Termux
```bash
cd "$HOME/tonsec-upgrade01-independent-audit/repository/tonsec_v020"
for f in engine.py lexer.py pipeline.py tolk_parser.py; do
  cp "tonsec/$f" "tonsec/${f}.bak-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  curl -fsSL "https://raw.githubusercontent.com/irzaamini-netizen/Tontest/grok-benchmark-engine/tonsec_v020/tonsec/$f" -o "tonsec/$f"
done
cp tonsec/engine.py tonsec/lexer.py tonsec/pipeline.py tonsec/tolk_parser.py /data/data/com.termux/files/usr/lib/tonsec/ 2>/dev/null || true
tonsec doctor
```
