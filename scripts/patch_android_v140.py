from pathlib import Path

p = Path('android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt')
s = p.read_text(encoding='utf-8')
s = s.replace('private const val VERSION = "1.3.0"', 'private const val VERSION = "1.4.0"', 1)
# Keep stage buttons state-aware by disabling completed actions through existing busy/status state.
s = s.replace('Button(onClick = onCollect, enabled = !busy', 'Button(onClick = onCollect, enabled = !busy && collected.isEmpty()', 1)
s = s.replace('Button(onClick = onTest, enabled = !busy && collected.isNotEmpty()', 'Button(onClick = onTest, enabled = !busy && collected.isNotEmpty() && results.isEmpty()', 1)
p.write_text(s, encoding='utf