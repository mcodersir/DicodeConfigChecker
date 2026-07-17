from pathlib import Path
import re


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


replace_once('private const val VERSION = "1.4.9"', 'private const val VERSION = "1.5.0"', "version")

old_ui = r'''@Composable
private fun SubscriptionSettingsPage() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE) }
    var token by rememberSaveable { mutableStateOf(prefs.getString("github_token", "").orEmpty()) }
    var repo by rememberSaveable { mutableStateOf(prefs.getString("repository", "").orEmpty()) }
    val rawBase = if (repo.contains('/')) "https://raw.githubusercontent.com/$repo/refs/heads/main" else ""
    Panel {
        Text("ساب اختصاصی GitHub", color = Text, fontWeight = FontWeight.Bold)
        Text("یک Classic Personal Access Token با دسترسی public_repo بساز؛ برنامه اولین بار یک ریپازیتوری عمومی تصادفی با پایان DIC می سازد و بعد از هر تست sub.txt و proxy.txt را به‌روز می‌کند.", color = Muted, fontSize = 12.sp)
        OutlinedTextField(value = token, onValueChange = { token = it }, label = { Text("GitHub Classic PAT (public_repo)") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), shape = RoundedCornerShape(15.dp), colors = appFieldColors())
        Button(onClick = {
            prefs.edit().putString("github_token", token.trim()).putString("repository", repo).apply()
            Toast.makeText(context, "ذخیره شد؛ پس از تست بعدی ساب منتشر می‌شود", Toast.LENGTH_LONG).show()
        }, enabled = token.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("ذخیره و فعال‌سازی ساب") }
        if (rawBase.isNotBlank()) {
            Text("sub.txt", color = Text, fontWeight = FontWeight.Bold)
            Text("$rawBase/sub.txt", color = Accent, fontSize = 11.sp)
            Text("proxy.txt", color = Text, fontWeight = FontWeight.Bold)
            Text("$rawBase/proxy.txt", color = Accent, fontSize = 11.sp)
        } else Text("پس از اولین تست، لینک‌های raw اینجا نمایش داده می‌شوند.", color = Muted, fontSize = 12.sp)
    }
}
'''
new_ui = r'''@Composable
private fun SubscriptionSettingsPage() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE) }
    var token by rememberSaveable { mutableStateOf(prefs.getString("github_token", "").orEmpty()) }
    var repo by rememberSaveable { mutableStateOf(prefs.getString("repository", "").orEmpty()) }
    val rawBase = if (repo.contains('/')) "https://raw.githubusercontent.com/$repo/refs/heads/main" else ""
    Panel {
        Text("ساب اختصاصی GitHub", color = Text, fontWeight = FontWeight.Bold)
        Text("بدون نیاز به آشنایی با GitHub، این سه قدم را انجام بده. بعد از هر تست، sub.txt و proxy.txt سالم خودکار در حساب خودت به‌روز می‌شوند.", color = Muted, fontSize = 12.sp)
        Text("۱. ساخت توکن", color = Text, fontWeight = FontWeight.Bold)
        Text("دکمه زیر صفحه درست GitHub را باز می‌کند. وارد حساب شو، public_repo را انتخاب‌شده نگه دار، پایین صفحه Generate token را بزن و توکن را کپی کن.", color = Muted, fontSize = 12.sp)
        OutlinedButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/settings/tokens/new?scopes=public_repo&description=DicodeConfigChecker%20Personal%20Subscription"))) }, modifier = Modifier.fillMaxWidth()) { Text("باز کردن صفحه ساخت توکن GitHub") }
        Text("۲. چسباندن توکن", color = Text, fontWeight = FontWeight.Bold)
        OutlinedTextField(value = token, onValueChange = { token = it }, label = { Text("GitHub Classic PAT (public_repo)") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), shape = RoundedCornerShape(15.dp), colors = appFieldColors())
        Button(onClick = {
            prefs.edit().putString("github_token", token.trim()).putString("repository", repo).apply()
            Toast.makeText(context, "ذخیره شد؛ پس از تست بعدی ساب منتشر می‌شود", Toast.LENGTH_LONG).show()
        }, enabled = token.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("۳. ذخیره و فعال‌سازی ساب") }
        if (rawBase.isNotBlank()) {
            Text("لینک‌های آماده", color = Text, fontWeight = FontWeight.Bold)
            Text("$rawBase/sub.txt", color = Accent, fontSize = 11.sp)
            Text("$rawBase/proxy.txt", color = Accent, fontSize = 11.sp)
        } else Text("پس از اولین تست، لینک‌های raw اینجا نمایش داده می‌شوند.", color = Muted, fontSize = 12.sp)
    }
}
'''
replace_once(old_ui, new_ui, "guided subscription UI")

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 150", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.5.0"', gradle, count=1)
gradle_path.write_text(gradle, encoding="utf-8")

if 'private const val VERSION = "1.5.0"' not in text or "باز کردن صفحه ساخت توکن GitHub" not in text:
    raise SystemExit("Android v1.5.0 guided subscription markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.5.0 guided GitHub subscription setup applied")
