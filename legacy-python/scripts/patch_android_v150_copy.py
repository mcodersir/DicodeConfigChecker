from pathlib import Path


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


replace_once(
    '''    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE) }''',
    '''    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val prefs = remember { context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE) }
    fun copyValue(value: String, title: String) {
        clipboard.setText(AnnotatedString(value))
        Toast.makeText(context, "$title کپی شد", Toast.LENGTH_SHORT).show()
    }''',
    "subscription clipboard",
)
replace_once(
    '''            Text("لینک‌های آماده", color = Text, fontWeight = FontWeight.Bold)
            Text("$rawBase/sub.txt", color = Accent, fontSize = 11.sp)
            Text("$rawBase/proxy.txt", color = Accent, fontSize = 11.sp)''',
    '''            Text("لینک‌های آماده", color = Text, fontWeight = FontWeight.Bold)
            CopySubscriptionValue("ریپازیتوری", repo) { copyValue(repo, "لینک ریپازیتوری") }
            CopySubscriptionValue("sub.txt", "$rawBase/sub.txt") { copyValue("$rawBase/sub.txt", "لینک sub.txt") }
            CopySubscriptionValue("proxy.txt", "$rawBase/proxy.txt") { copyValue("$rawBase/proxy.txt", "لینک proxy.txt") }''',
    "copyable subscription links",
)

copy_row = r'''
@Composable
private fun CopySubscriptionValue(label: String, value: String, onCopy: () -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("$label: $value", color = Accent, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f).clickable { onCopy() })
        IconButton(onClick = onCopy) { Icon(Icons.Default.ContentCopy, contentDescription = "کپی $label", tint = Accent) }
    }
}

'''
replace_once("@Composable\nprivate fun ChannelsPage", copy_row + "@Composable\nprivate fun ChannelsPage", "copy row composable")

if "CopySubscriptionValue" not in text or "LocalClipboardManager.current" not in text:
    raise SystemExit("Android v1.5.0 copy-link markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.5.0 copyable subscription links applied")
