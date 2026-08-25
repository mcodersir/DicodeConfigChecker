from pathlib import Path
import re


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


def replace_regex(pattern: str, new: str, name: str) -> None:
    global text
    text, count = re.subn(pattern, lambda _: new, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {count}")


new_publisher = r'''private data class SubscriptionPublishResult(
    val repository: String,
    val subChanged: Boolean,
    val proxyChanged: Boolean,
) {
    val subUrl get() = "https://raw.githubusercontent.com/$repository/refs/heads/main/sub.txt"
}

private fun putGithubFile(token: String, repo: String, filename: String, value: String): Boolean {
    val path = "/repos/$repo/contents/$filename"
    val current = try { githubJson(token, "GET", path) } catch (error: GitHubRequestError) {
        if (error.status == 404) null else throw error
    }
    val sha = current?.optString("sha").orEmpty()
    val previous = current?.optString("content").orEmpty().replace("\n", "")
    if (previous.isNotBlank()) {
        val remoteValue = String(Base64.decode(previous, Base64.DEFAULT), Charsets.UTF_8)
        if (remoteValue == value) return false
    }
    val body = JSONObject()
        .put("message", "Update $filename from Dicode Config Checker")
        .put("content", Base64.encodeToString(value.toByteArray(Charsets.UTF_8), Base64.NO_WRAP))
        .put("branch", "main")
    if (sha.isNotBlank()) body.put("sha", sha)
    githubJson(token, "PUT", path, body)
    return true
}

private fun ensurePersonalSubscriptionRepository(context: Context): String? {
    val prefs = context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE)
    val token = prefs.getString("github_token", "").orEmpty().trim()
    if (token.isBlank()) return null
    var repo = prefs.getString("repository", "").orEmpty()
    if (!repo.contains('/')) {
        val owner = githubJson(token, "GET", "/user").optString("login")
        if (owner.isBlank()) throw IllegalStateException("GitHub account not found")
        val name = "dicode-${(1_000_000..9_999_999).random()}-DIC"
        val created = githubJson(token, "POST", "/user/repos", JSONObject()
            .put("name", name).put("description", "Personal Dicode Config Checker subscription output")
            .put("private", false).put("auto_init", true).put("has_issues", false).put("has_projects", false).put("has_wiki", false))
        repo = "${created.getJSONObject("owner").getString("login")}/${created.getString("name")}" 
        prefs.edit().putString("repository", repo).apply()
    }
    return repo
}

private fun publishPersonalSubscription(context: Context, files: List<File>): SubscriptionPublishResult? {
    val prefs = context.getSharedPreferences(SubscriptionPrefs, Context.MODE_PRIVATE)
    val token = prefs.getString("github_token", "").orEmpty().trim()
    val repo = ensurePersonalSubscriptionRepository(context) ?: return null
    val byName = files.associateBy { it.name }
    val subChanged = putGithubFile(token, repo, "sub.txt", byName["sub.txt"]?.readText().orEmpty())
    val proxyChanged = putGithubFile(token, repo, "proxy.txt", byName["proxy.txt"]?.readText().orEmpty())
    return SubscriptionPublishResult(repo, subChanged, proxyChanged)
}
'''
replace_regex(
    r'''private fun putGithubFile\(token: String, repo: String, filename: String, value: String\) \{.*?\n\}\n\nprivate fun publishPersonalSubscription\(context: Context, files: List<File>\): String\? \{.*?\n\}\n\n(?=private fun writeOutputs)''',
    new_publisher,
    "duplicate-aware publisher",
)

replace_once(
    '''                                    val rawUrl = withContext(Dispatchers.IO) { publishPersonalSubscription(context, outputFiles) }
                                    Triple(checked, outputFiles, rawUrl)
                                }.onSuccess { (checked, outputFiles, rawUrl) ->
                                    results = checked
                                    files = outputFiles
                                    status = if (rawUrl == null) "تست تمام شد؛ خروجی‌ها آماده‌اند" else "تست تمام شد؛ ساب اختصاصی به‌روز شد"
                                    if (rawUrl != null) logs = (logs + "[SUB] $rawUrl").takeLast(160)''',
    '''                                    val published = withContext(Dispatchers.IO) { publishPersonalSubscription(context, outputFiles) }
                                    Triple(checked, outputFiles, published)
                                }.onSuccess { (checked, outputFiles, published) ->
                                    results = checked
                                    files = outputFiles
                                    status = if (published == null) "تست تمام شد؛ خروجی‌ها آماده‌اند" else if (published.subChanged || published.proxyChanged) "تست تمام شد؛ ساب اختصاصی به‌روز شد" else "تست تمام شد؛ ساب تکراری بود"
                                    if (published != null) logs = (logs + "[SUB] ${published.subUrl}").takeLast(160)''',
    "automatic publish result",
)

replace_once(
    '''    var repo by rememberSaveable { mutableStateOf(prefs.getString("repository", "").orEmpty()) }
    val rawBase = if (repo.contains('/')) "https://raw.githubusercontent.com/$repo/refs/heads/main" else ""''',
    '''    var repo by rememberSaveable { mutableStateOf(prefs.getString("repository", "").orEmpty()) }
    val scope = rememberCoroutineScope()
    var creating by remember { mutableStateOf(false) }
    val rawBase = if (repo.contains('/')) "https://raw.githubusercontent.com/$repo/refs/heads/main" else ""''',
    "subscription state",
)
replace_once(
    '''        Button(onClick = {
            prefs.edit().putString("github_token", token.trim()).putString("repository", repo).apply()
            Toast.makeText(context, "ذخیره شد؛ پس از تست بعدی ساب منتشر می‌شود", Toast.LENGTH_LONG).show()
        }, enabled = token.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("۳. ذخیره و فعال‌سازی ساب") }''',
    '''        Button(onClick = {
            prefs.edit().putString("github_token", token.trim()).putString("repository", repo).apply()
            Toast.makeText(context, "ذخیره شد؛ اکنون ریپازیتوری را بساز یا متصل کن", Toast.LENGTH_LONG).show()
        }, enabled = token.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("۳. ذخیره توکن") }
        OutlinedButton(onClick = {
            prefs.edit().putString("github_token", token.trim()).putString("repository", repo).apply()
            creating = true
            scope.launch {
                runCatching { withContext(Dispatchers.IO) { ensurePersonalSubscriptionRepository(context) } }
                    .onSuccess { ready ->
                        if (ready == null) Toast.makeText(context, "ابتدا توکن را وارد کن", Toast.LENGTH_LONG).show()
                        else { repo = ready; Toast.makeText(context, "ریپازیتوری آماده و لینک‌ها ساخته شد", Toast.LENGTH_LONG).show() }
                    }
                    .onFailure { Toast.makeText(context, "اتصال GitHub ناموفق بود؛ بعداً دوباره امتحان کن", Toast.LENGTH_LONG).show() }
                creating = false
            }
        }, enabled = token.isNotBlank() && !creating, modifier = Modifier.fillMaxWidth()) { Text(if (creating) "در حال ساخت…" else "ساخت / اتصال ریپازیتوری ساب") }''',
    "manual repository button",
)

replace_once(
    '''private fun OutputPage(title: String, rows: List<CheckResult>, file: File?, context: Context, isProxy: Boolean, settings: SettingsState) {
    val clipboard = LocalClipboardManager.current''',
    '''private fun OutputPage(title: String, rows: List<CheckResult>, file: File?, context: Context, isProxy: Boolean, settings: SettingsState) {
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()''',
    "output publish scope",
)
replace_regex(
    r'''        item \{\n            Panel \{\n                Row\(Modifier\.fillMaxWidth\(\), horizontalArrangement = Arrangement\.spacedBy\(8\.dp\)\) \{.*?Text\("اشتراک فایل", fontWeight = FontWeight\.Bold\) \}\n                \}\n            \}\n        \}\n(?=        itemsIndexed)''',
    '''        item {
            Panel {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { clipboard.setText(AnnotatedString(lines.joinToString("\\n"))); Toast.makeText(context, "${lines.size} مورد کپی شد", Toast.LENGTH_SHORT).show() }, enabled = lines.isNotEmpty(), modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color.White)) { Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(7.dp)); Text("کپی همه", fontWeight = FontWeight.Bold) }
                    FilledTonalButton(onClick = { file?.let { share(context, it) } }, enabled = file != null, modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Card2, contentColor = Text)) { Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(7.dp)); Text("اشتراک فایل", fontWeight = FontWeight.Bold) }
                }
                OutlinedButton(onClick = {
                    scope.launch {
                        runCatching { withContext(Dispatchers.IO) { publishPersonalSubscription(context, file?.parentFile?.listFiles()?.toList().orEmpty()) } }
                            .onSuccess { published ->
                                val changed = if (isProxy) published?.proxyChanged else published?.subChanged
                                Toast.makeText(context, if (changed == true) "ساب با موفقیت منتشر شد" else "تکراری است؛ همین متن قبلاً روی ریپو بوده", Toast.LENGTH_LONG).show()
                            }
                            .onFailure { Toast.makeText(context, "اتصال GitHub ناموفق بود؛ دوباره امتحان کن", Toast.LENGTH_LONG).show() }
                    }
                }, enabled = file != null, modifier = Modifier.fillMaxWidth()) { Text(if (isProxy) "به‌روزرسانی ساب پروکسی" else "به‌روزرسانی ساب کانفیگ") }
            }
        }
''',
    "manual output publish button",
)

if "SubscriptionPublishResult" not in text or "ساخت / اتصال ریپازیتوری ساب" not in text:
    raise SystemExit("Android manual subscription markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.5.0 manual subscription actions applied")
