# اقدامات بعدی

## روی Termux (baseline آرشیوی)
```bash
cd "$HOME/tonsec-upgrade01-independent-audit/repository/tonsec_v020"
for f in engine.py lexer.py pipeline.py tolk_parser.py tact_parser.py; do
  cp "tonsec/$f" "tonsec/${f}.bak-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  curl -fsSL "https://raw.githubusercontent.com/irzaamini-netizen/Tontest/grok-benchmark-engine/tonsec_v020/tonsec/$f" -o "tonsec/$f"
done
cp tonsec/*.py /data/data/com.termux/files/usr/lib/tonsec/ 2>/dev/null || true
bash scripts/run_baseline_archive.sh "$HOME/tonsec-real-projects"
```

## تکرار نشود
- equal_slices / camelCase Tolk / نقطه lexer / asm body

## بعدی اختیاری
- شاهد تازه برای telemint send_msg و royalty عمومی
- غنی‌سازی Tact parser (contract body, init)
