from pathlib import Path


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


preview_helper = r'''private fun isUsableTelegramPreview(html: String): Boolean {
    val lower = html.lowercase()
    return html.isNotBlank() && (lower.contains("tgme_widget_message") || lower.contains("tgme_channel_info") || linkRegex.containsMatchIn(html))
}

'''
replace_once("private fun fetchTelegramPreview", preview_helper + "private fun fetchTelegramPreview", "preview validation helper")
replace_once(
    '            if (html.isBlank()) throw IllegalStateException("empty Telegram preview")',
    '            if (!isUsableTelegramPreview(html)) throw IllegalStateException("unusable Telegram preview")',
    "t.me preview validation",
)

if "isUsableTelegramPreview" not in text:
    raise SystemExit("Android v1.5.0 Telegram preview validation marker is missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.5.0 Telegram preview validation applied")
