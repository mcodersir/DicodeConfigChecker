from pathlib import Path
import re


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


replace_once('private const val VERSION = "1.4.0"', 'private const val VERSION = "1.4.1"', "version")
replace_once(
    '    val clean = value.trim().removePrefix("https://").removePrefix("http://").removePrefix("t.me/").removePrefix("s/").substringBefore(\'/\')',
    '    val clean = value.trim().removePrefix("https://").removePrefix("http://").removePrefix("t.me/").removePrefix("telegram.me/").removePrefix("s/").substringBefore(\'/\')',
    "telegram.me channel normalization",
)

helper = r'''private fun fetchTelegramPreview(channel: String): Pair<String, String> {
    var primaryError: Throwable? = null
    for (host in listOf("t.me", "telegram.me")) {
        var conn: HttpURLConnection? = null
        try {
            conn = URL("https://$host/s/$channel").openConnection() as HttpURLConnection
            conn.connectTimeout = 15000; conn.readTimeout = 15000
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 DicodeConfigChecker/$VERSION")
            val html = conn.inputStream.bufferedReader().use { it.readText() }.replace("&amp;", "&")
            if (html.isBlank()) throw IllegalStateException("empty Telegram preview")
            return html to host
        } catch (error: Throwable) {
            if (host == "t.me") primaryError = error
            else throw IllegalStateException("t.me unavailable (${primaryError?.javaClass?.simpleName}); telegram.me also failed", error)
        } finally { conn?.disconnect() }
    }
    throw IllegalStateException("Telegram preview unavailable")
}

'''
replace_once("private suspend fun collectAll(", helper + "private suspend fun collectAll(", "preview fallback helper")
replace_once(
    '''                    val conn = URL("https://t.me/s/$channel").openConnection() as HttpURLConnection
                    try {
                        conn.connectTimeout = 8000; conn.readTimeout = 8000
                        conn.setRequestProperty("User-Agent", "Mozilla/5.0 DicodeConfigChecker/$VERSION")
                        val html = conn.inputStream.bufferedReader().use { it.readText() }.replace("&amp;", "&")''',
    '''                    val (html, previewHost) = fetchTelegramPreview(channel)''',
    "preview request fallback",
)
replace_once('''                        "[FETCH] @$channel • +$count • کل ${found.size}"
                    } finally { conn.disconnect() }''', '''                        "[FETCH] @$channel • +$count • کل ${found.size} • $previewHost"''', "preview request finally")

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 141", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.4.1"', gradle, count=1)
gradle_path.write_text(gradle, encoding="utf-8")

if 'private const val VERSION = "1.4.1"' not in text or "fetchTelegramPreview" not in text:
    raise SystemExit("Android v1.4.1 Telegram fallback markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.4.1 Telegram preview fallback applied")
