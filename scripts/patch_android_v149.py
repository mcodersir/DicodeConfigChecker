from pathlib import Path
import re


main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


replace_once(
    "import androidx.compose.ui.text.TextStyle\n",
    "import androidx.compose.ui.text.TextStyle\nimport androidx.compose.ui.text.input.PasswordVisualTransformation\n",
    "password transformation import",
)
replace_once('private const val VERSION = "1.4.1"', 'private const val VERSION = "1.4.9"', "version")
replace_once(
    'private enum class SettingsTab(val title: String) { Fetch("دریافت"), Test("تست"), Output("خروجی") }',
    'private enum class SettingsTab(val title: String) { Fetch("دریافت"), Test("تست"), Output("خروجی"), Subscription("ساب") }',
    "settings tabs",
)

publisher = r'''
private const val SubscriptionPrefs = "dicode_personal_subscription"

private class GitHubRequestError(val status: Int, detail: String) : IllegalStateException("GitHub API $status: ${detail.take(220)}")

private fun githubJson(token: String, method: String, path: String, body: JSONObject? = null): JSONObject {
    val conn = (URL("https://api.github.com$path").openConnection() as HttpURLConnection)
    try {
        conn.requestMethod = method
        conn.connectTimeout = 20000; conn.readTimeout = 20000
        conn.setRequestProperty("Authorization", "Bearer ${token.trim()}")
        conn.setRequestProperty("Accept", "application/vnd.github+json")
        conn.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
        conn.setRequestProperty("User-Agent", "DicodeConfigChecker/$VERSION")
        if (body != null) {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        }
        val status = conn.responseCode
        val raw = (if (status in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (status !in 200..299) throw GitHubRequestError(status, raw)
        return if (raw.isBlank()) JSONObject() else JSONObject(raw)
    } finally { conn.disconnect() }
}

private fun putGithubFile(token: String, repo: String, filename: String, value: String) {
    val path = "/repos/$repo/contents/$filename"
    val sha = try { githubJson(token, "GET", path).optString("sha") } catch (error: GitHubRequestError) {
        if (error.status == 404) "" else throw error
    }
    val body = JSONObject()
        .put("message", "Update $filename from Dicode Config Checker")
        .put("content", Base64.encodeToString(value.toByteArray(Charsets.UTF_8), Base64.NO_WRAP))
        .put("branch", "main")
    if (sha.isNotBlank()) body.put("sha", sha)
    githubJson(token, "PUT", path, body)
}

private fun publishPersonalSubscription(context: Context, files: List<File>): String? {
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
    val byName = files.associateBy { it.name }
    putGithubFile(token, repo, "sub.txt", byName["sub.txt"]?.readText().orEmpty())
    putGithubFile(token, repo, "proxy.txt", byName["proxy.txt"]?.readText().orEmpty())
    return "https://raw.githubusercontent.com/$repo/refs/heads/main/sub.txt"
}

'''
replace_once("private fun writeOutputs(", publisher + "private fun writeOutputs(", "subscription publisher")

replace_once(
    '''                                runCatching {
                                    testAll(collected, settings) { done, total, msg ->
                                        progress = if (total == 0) 0f else done.toFloat() / total
                                        status = "تست واقعی: $done از $total"
                                        logs = (logs + msg).takeLast(160)
                                    }
                                }.onSuccess {
                                    results = it
                                    files = writeOutputs(context.getExternalFilesDir(null)!!, it, settings)
                                    status = "تست تمام شد؛ خروجی‌ها آماده‌اند"
                                    progress = 1f
                                }.onFailure {''',
    '''                                runCatching {
                                    val checked = testAll(collected, settings) { done, total, msg ->
                                        progress = if (total == 0) 0f else done.toFloat() / total
                                        status = "تست واقعی: $done از $total"
                                        logs = (logs + msg).takeLast(160)
                                    }
                                    val outputFiles = writeOutputs(context.getExternalFilesDir(null)!!, checked, settings)
                                    val rawUrl = withContext(Dispatchers.IO) { publishPersonalSubscription(context, outputFiles) }
                                    Triple(checked, outputFiles, rawUrl)
                                }.onSuccess { (checked, outputFiles, rawUrl) ->
                                    results = checked
                                    files = outputFiles
                                    status = if (rawUrl == null) "تست تمام شد؛ خروجی‌ها آماده‌اند" else "تست تمام شد؛ ساب اختصاصی به‌روز شد"
                                    if (rawUrl != null) logs = (logs + "[SUB] $rawUrl").takeLast(160)
                                    progress = 1f
                                }.onFailure {''',
    "automatic publish after test",
)

replace_once(
    """            SettingsTab.Output -> Panel {
                Text(\"خروجی\", color = Text, fontWeight = FontWeight.Bold)
                TextFieldRow(\"متن نام کانفیگ\", value.tagPrefix) { onChange(value.copy(tagPrefix = it)) }
                Toggle(\"بازنویسی نام کانفیگ\", value.renameNames) { onChange(value.copy(renameNames = it)) }
                Text(\"فایل ها و تب های خروجی فقط موارد سالم را نمایش می دهند.\", color = Muted, fontSize = 12.sp)
            }
""",
    """            SettingsTab.Output -> Panel {
                Text(\"خروجی\", color = Text, fontWeight = FontWeight.Bold)
                TextFieldRow(\"متن نام کانفیگ\", value.tagPrefix) { onChange(value.copy(tagPrefix = it)) }
                Toggle(\"بازنویسی نام کانفیگ\", value.renameNames) { onChange(value.copy(renameNames = it)) }
                Text(\"فایل ها و تب های خروجی فقط موارد سالم را نمایش می دهند.\", color = Muted, fontSize = 12.sp)
            }
            SettingsTab.Subscription -> SubscriptionSettingsPage()
""",
    "subscription tab body",
)

subscription_ui = r'''
@Composable
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
replace_once("@Composable\nprivate fun ChannelsPage", subscription_ui + "@Composable\nprivate fun ChannelsPage", "subscription settings UI")

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 149", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.4.9"', gradle, count=1)
gradle_path.write_text(gradle, encoding="utf-8")

if 'private const val VERSION = "1.4.9"' not in text or "publishPersonalSubscription" not in text:
    raise SystemExit("Android v1.4.9 subscription markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.4.9 personal subscription publishing applied")
