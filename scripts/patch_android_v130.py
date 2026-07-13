from pathlib import Path
import re

main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")

text = text.replace('private const val VERSION = "1.2.0"', 'private const val VERSION = "1.3.0"', 1)

start_marker = "                        val linkRegex = Regex("
end_marker = "\n                        var count = 0"
start = text.find(start_marker)
if start < 0:
    raise SystemExit("linkRegex start marker not found")
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit("linkRegex end marker not found")
replacement = r'''                        val linkRegex = Regex("""(?:vmess|vless|trojan|ss|ssr|snell|hysteria2|hy2|tuic)://[^\s<>"'`]+|(?:tg://(?:proxy|socks)|https://t\.me/(?:proxy|socks))\?[^\s<>"'`]+""", RegexOption.IGNORE_CASE)'''
text = text[:start] + replacement + text[end:]

if 'private const val VERSION = "1.3.0"' not in text:
    raise SystemExit("Android app version was not updated to 1.3.0")
if 'val linkRegex = Regex("""' not in text:
    raise SystemExit("linkRegex was not converted to a Kotlin raw string")

main_path.write_text(text, encoding="utf-8")

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 130", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.3.0"', gradle, count=1)
gradle_path.write_text(gradle, encoding="utf-8")

print("Android v1.3.0 metadata and safe link regex applied")
