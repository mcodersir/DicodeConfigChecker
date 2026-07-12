package ir.dicode.configchecker

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.core.view.WindowCompat
import go.Seq
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import libv2ray.Libv2ray
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.net.URLDecoder
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

private const val VERSION = "1.1.0"
private val Bg = Color(0xFF090D12)
private val Card = Color(0xFF111821)
private val Card2 = Color(0xFF0D141D)
private val Accent = Color(0xFF3B82F6)
private val Text = Color(0xFFEAF1FA)
private val Muted = Color(0xFF9CAABC)
private val Good = Color(0xFF22C55E)
private val Bad = Color(0xFFEF4444)

private enum class Page(val title: String) {
    Dashboard("داشبورد"), Settings("تنظیمات"), Channels("کانال‌ها"), Configs("کانفیگ‌ها"), Proxies("پروکسی‌ها")
}

private data class SettingsState(
    val perChannelLimit: Int = 20,
    val priorityLimit: Int = 30,
    val fetchWorkers: Int = 8,
    val attempts: Int = 2,
    val minSuccess: Int = 1,
    val checkUrl: String = "http://www.gstatic.com/generate_204",
    val tagPrefix: String = "t.me/dicodeir",
    val renameNames: Boolean = true,
    val checkConfigs: Boolean = true,
    val checkProxies: Boolean = true,
    val tcpPrefilter: Boolean = true,
)

private data class Candidate(
    val raw: String,
    val source: String,
    val protocol: String,
    val host: String,
    val port: Int,
    val proxy: Boolean,
    val xrayJson: String? = null,
)

private data class CheckResult(
    val item: Candidate,
    val ok: Boolean,
    val ping: Int?,
    val tester: String,
    val error: String = "",
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        runCatching {
            Seq.setContext(applicationContext)
            Libv2ray.initCoreEnv(filesDir.absolutePath, "")
        }
        setContent { DicodeApp() }
    }
}

@Composable
private fun DicodeApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var page by rememberSaveable { mutableStateOf(Page.Dashboard) }
    var settings by remember { mutableStateOf(SettingsState()) }
    var priority1 by rememberSaveable { mutableStateOf("t.me/dicodeir\nt.me/persianvpnhub") }
    var priority2 by rememberSaveable {
        mutableStateOf("t.me/PrivateVPNs\nt.me/v2rayNG_Matsuri\nt.me/vmess_ir\nt.me/V2ray_Alpha\nt.me/DailyV2RY")
    }
    var collected by remember { mutableStateOf<List<Candidate>>(emptyList()) }
    var results by remember { mutableStateOf<List<CheckResult>>(emptyList()) }
    var files by remember { mutableStateOf<List<File>>(emptyList()) }
    var logs by remember { mutableStateOf(listOf<String>()) }
    var status by remember { mutableStateOf("آماده") }
    var progress by remember { mutableFloatStateOf(0f) }
    var busy by remember { mutableStateOf(false) }
    var waitingDisconnect by remember { mutableStateOf(false) }

    MaterialTheme(colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card)) {
        Scaffold(
            containerColor = Bg,
            contentWindowInsets = WindowInsets.safeDrawing,
            topBar = {
                Surface(color = Card, tonalElevation = 0.dp) {
                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            Modifier.size(42.dp).background(Card2, RoundedCornerShape(13.dp)),
                            contentAlignment = Alignment.Center,
                        ) { Text("ϟ", color = Color(0xFF68E8FF), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black) }
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Dicode Config Checker", color = Text, fontWeight = FontWeight.Black, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text("Android • Xray Core • v$VERSION", color = Muted, style = MaterialTheme.typography.labelMedium)
                        }
                        AssistChip(onClick = {}, label = { Text(if (busy) "در حال اجرا" else "آماده") })
                    }
                }
            },
            bottomBar = {
                NavigationBar(containerColor = Card) {
                    Page.entries.forEach { item ->
                        NavigationBarItem(
                            selected = page == item,
                            onClick = { page = item },
                            icon = { Text(when (item) {
                                Page.Dashboard -> "⌂"; Page.Settings -> "⚙"; Page.Channels -> "≡"; Page.Configs -> "✓"; Page.Proxies -> "ϟ"
                            }) },
                            label = { Text(item.title, maxLines = 1) },
                        )
                    }
                }
            },
        ) { padding ->
            Box(Modifier.fillMaxSize().padding(padding)) {
                when (page) {
                    Page.Dashboard -> DashboardPage(
                        status, progress, collected, results, logs, busy, waitingDisconnect,
                        onCollect = {
                            busy = true; waitingDisconnect = false; collected = emptyList(); results = emptyList(); files = emptyList(); logs = emptyList(); progress = 0f
                            scope.launch {
                                runCatching {
                                    collectAll(priority1, priority2, settings) { done, total, msg ->
                                        progress = if (total == 0) 0f else done.toFloat() / total
                                        status = "دریافت از تلگرام: $done از $total"
                                        logs = (logs + msg).takeLast(160)
                                    }
                                }.onSuccess {
                                    collected = it
                                    status = "اتصال فعلی را قطع کنید، سپس ادامه را بزنید"
                                    waitingDisconnect = true
                                    progress = 1f
                                }.onFailure {
                                    status = "خطا در دریافت: ${it.message}"
                                    logs = logs + "ERROR ${it.javaClass.simpleName}: ${it.message}"
                                }
                                busy = false
                            }
                        },
                        onTest = {
                            busy = true; waitingDisconnect = false; progress = 0f; results = emptyList()
                            scope.launch {
                                runCatching {
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
                                }.onFailure {
                                    status = "خطا در تست: ${it.message}"
                                    logs = logs + "ERROR ${it.javaClass.simpleName}: ${it.message}"
                                }
                                busy = false
                            }
                        },
                        onReset = {
                            collected = emptyList(); results = emptyList(); files = emptyList(); logs = emptyList(); status = "آماده"; progress = 0f; waitingDisconnect = false
                        },
                        onOpenOutputs = { files.firstOrNull()?.let { share(context, it) } },
                    )
                    Page.Settings -> SettingsPage(settings, onChange = { settings = it })
                    Page.Channels -> ChannelsPage(priority1, priority2, onPriority1 = { priority1 = it }, onPriority2 = { priority2 = it })
                    Page.Configs -> OutputPage("کانفیگ‌ها", results.filter { !it.item.proxy }, files.firstOrNull { it.name == "sub.txt" }, context)
                    Page.Proxies -> OutputPage("پروکسی‌ها", results.filter { it.item.proxy }, files.firstOrNull { it.name == "proxy.txt" }, context)
                }
            }
        }
    }
}

@Composable
private fun DashboardPage(
    status: String,
    progress: Float,
    collected: List<Candidate>,
    results: List<CheckResult>,
    logs: List<String>,
    busy: Boolean,
    waitingDisconnect: Boolean,
    onCollect: () -> Unit,
    onTest: () -> Unit,
    onReset: () -> Unit,
    onOpenOutputs: () -> Unit,
) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("دریافت", collected.size, Muted, Modifier.weight(1f))
            Metric("سالم", results.count { it.ok }, Good, Modifier.weight(1f))
            Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f))
            Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
        }
        Panel {
            Text("وضعیت اجرا", color = Text, fontWeight = FontWeight.Bold)
            Text(status, color = Muted)
            LinearProgressIndicator(progress = { progress.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth().height(8.dp))
            if (waitingDisconnect) Text("قبل از ادامه، VPN یا کانفیگ فعلی را کامل قطع کن.", color = Color(0xFFFBBF24))
        }
        Panel {
            Text("کنترل عملیات", color = Text, fontWeight = FontWeight.Bold)
            Button(onClick = onCollect, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("۱. دریافت کانفیگ‌ها") }
            Button(onClick = onTest, enabled = !busy && collected.isNotEmpty(), modifier = Modifier.fillMaxWidth()) { Text("۲. تست واقعی و ساخت خروجی") }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.weight(1f)) { Text("شروع از ابتدا") }
                OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.weight(1f)) { Text("اشتراک خروجی") }
            }
        }
        Panel {
            Text("لاگ زنده", color = Text, fontWeight = FontWeight.Bold)
            Text(if (logs.isEmpty()) "هنوز عملیاتی اجرا نشده" else logs.joinToString("\n"), color = Muted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun SettingsPage(value: SettingsState, onChange: (SettingsState) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PageHeader("تنظیمات", "همان گزینه‌های اصلی نسخه ویندوز")
        Panel {
            NumberField("تعداد از هر کانال رتبه دوم", value.perChannelLimit) { onChange(value.copy(perChannelLimit = it)) }
            NumberField("تعداد از هر کانال رتبه اول", value.priorityLimit) { onChange(value.copy(priorityLimit = it)) }
            NumberField("Fetch workers", value.fetchWorkers) { onChange(value.copy(fetchWorkers = it)) }
            NumberField("تعداد تلاش", value.attempts) { onChange(value.copy(attempts = it, minSuccess = value.minSuccess.coerceAtMost(it))) }
            NumberField("حداقل موفقیت", value.minSuccess) { onChange(value.copy(minSuccess = it.coerceAtMost(value.attempts))) }
        }
        Panel {
            TextFieldRow("URL تست واقعی", value.checkUrl) { onChange(value.copy(checkUrl = it)) }
            TextFieldRow("متن نام کانفیگ", value.tagPrefix) { onChange(value.copy(tagPrefix = it)) }
            Toggle("بازنویسی نام کانفیگ", value.renameNames) { onChange(value.copy(renameNames = it)) }
            Toggle("بررسی کانفیگ‌های Xray", value.checkConfigs) { onChange(value.copy(checkConfigs = it)) }
            Toggle("بررسی پروکسی‌های تلگرام", value.checkProxies) { onChange(value.copy(checkProxies = it)) }
            Toggle("پیش‌فیلتر سریع TCP", value.tcpPrefilter) { onChange(value.copy(tcpPrefilter = it)) }
        }
        Text("کانفیگ‌های VLESS، VMess و Trojan از داخل Xray Core تست می‌شوند؛ موارد پشتیبانی‌نشده با TCP مشخص می‌شوند.", color = Muted)
    }
}

@Composable
private fun ChannelsPage(p1: String, p2: String, onPriority1: (String) -> Unit, onPriority2: (String) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PageHeader("کانال‌ها", "رتبه اول و دوم، مشابه نسخه ویندوز")
        Panel {
            Text("کانال‌های رتبه اول", color = Text, fontWeight = FontWeight.Bold)
            OutlinedTextField(value = p1, onValueChange = onPriority1, modifier = Modifier.fillMaxWidth().heightIn(min = 150.dp), placeholder = { Text("هر خط یک کانال") })
        }
        Panel {
            Text("کانال‌های رتبه دوم", color = Text, fontWeight = FontWeight.Bold)
            OutlinedTextField(value = p2, onValueChange = onPriority2, modifier = Modifier.fillMaxWidth().heightIn(min = 220.dp), placeholder = { Text("هر خط یک کانال") })
        }
    }
}

@Composable
private fun OutputPage(title: String, rows: List<CheckResult>, file: File?, context: Context) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PageHeader(title, "${rows.count { it.ok }} سالم از ${rows.size} مورد")
        if (file != null) Button(onClick = { share(context, file) }, modifier = Modifier.fillMaxWidth()) { Text("اشتراک‌گذاری ${file.name}") }
        rows.forEach { row ->
            Surface(color = Card, shape = RoundedCornerShape(14.dp)) {
                Column(Modifier.fillMaxWidth().padding(12.dp)) {
                    Text("${if (row.ok) "سالم" else "ناموفق"} • ${row.item.protocol.uppercase()} • ${row.ping ?: "-"} ms", color = if (row.ok) Good else Bad, fontWeight = FontWeight.Bold)
                    Text("${row.item.host}:${row.item.port} • ${row.tester}", color = Muted, style = MaterialTheme.typography.bodySmall)
                    Text(row.item.raw, color = Text, style = MaterialTheme.typography.labelSmall, maxLines = 3, overflow = TextOverflow.Ellipsis)
                }
            }
        }
        if (rows.isEmpty()) Text("هنوز خروجی ساخته نشده است.", color = Muted)
    }
}

@Composable private fun PageHeader(title: String, subtitle: String) = Panel {
    Text(title, color = Text, fontWeight = FontWeight.Black, style = MaterialTheme.typography.headlineSmall)
    Text(subtitle, color = Muted)
}

@Composable private fun Panel(content: @Composable ColumnScope.() -> Unit) = Column(
    Modifier.fillMaxWidth().background(Card, RoundedCornerShape(18.dp)).padding(16.dp),
    verticalArrangement = Arrangement.spacedBy(10.dp), content = content,
)

@Composable private fun Metric(label: String, value: Int, color: Color, modifier: Modifier = Modifier) = Column(
    modifier.background(Card, RoundedCornerShape(14.dp)).padding(vertical = 12.dp), horizontalAlignment = Alignment.CenterHorizontally,
) {
    Text(value.toString(), color = color, fontWeight = FontWeight.Black)
    Text(label, color = Muted, style = MaterialTheme.typography.labelSmall)
}

@Composable private fun NumberField(label: String, value: Int, onChange: (Int) -> Unit) {
    OutlinedTextField(value = value.toString(), onValueChange = { it.toIntOrNull()?.let(onChange) }, label = { Text(label) }, modifier = Modifier.fillMaxWidth())
}

@Composable private fun TextFieldRow(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(value = value, onValueChange = onChange, label = { Text(label) }, modifier = Modifier.fillMaxWidth())
}

@Composable private fun Toggle(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = Text, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

private suspend fun collectAll(
    priority1: String,
    priority2: String,
    settings: SettingsState,
    update: (Int, Int, String) -> Unit,
): List<Candidate> = withContext(Dispatchers.IO) {
    val first = priority1.lines().mapNotNull(::normalizeChannel).distinctBy { it.lowercase() }
    val second = priority2.lines().mapNotNull(::normalizeChannel).distinctBy { it.lowercase() }.filterNot { c -> first.any { it.equals(c, true) } }
    val channels = first.map { it to settings.priorityLimit } + second.map { it to settings.perChannelLimit }
    val found = ConcurrentHashMap<String, Candidate>()
    channels.forEachIndexed { index, (channel, limit) ->
        val msg = runCatching {
            val conn = URL("https://t.me/s/$channel").openConnection() as HttpURLConnection
            conn.connectTimeout = 15000; conn.readTimeout = 15000
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 DicodeConfigChecker/$VERSION")
            val html = conn.inputStream.bufferedReader().use { it.readText() }.replace("&amp;", "&")
            val regex = Regex("(?:vmess|vless|trojan|ss|ssr|snell|hysteria2|hy2|tuic)://[^\\s<>\\\"'`]+|(?:tg://(?:proxy|socks)|https://t\\.me/(?:proxy|socks))\\?[^\\s<>\\\"'`]+", RegexOption.IGNORE_CASE)
            var count = 0
            regex.findAll(html).map { it.value.trimEnd(')', ']', '}', ',', '.', ';') }.take(limit).forEach { raw ->
                parseCandidate(raw, channel)?.let {
                    val key = if (it.protocol == "vmess") it.raw else it.raw.substringBefore('#')
                    if (found.putIfAbsent(key.lowercase(), it) == null) count++
                }
            }
            "@$channel | +$count | کل ${found.size}"
        }.getOrElse { "@$channel | خطا: ${it.javaClass.simpleName}" }
        update(index + 1, channels.size, msg)
    }
    found.values.toList()
}

private suspend fun testAll(items: List<Candidate>, settings: SettingsState, update: (Int, Int, String) -> Unit): List<CheckResult> = withContext(Dispatchers.IO) {
    val filtered = items.filter { if (it.proxy) settings.checkProxies else settings.checkConfigs }
    filtered.mapIndexed { index, item ->
        val result = if (!item.proxy && item.xrayJson != null) {
            val samples = mutableListOf<Int>(); var error = "xray_failed"
            repeat(settings.attempts.coerceIn(1, 8)) {
                runCatching { Libv2ray.measureOutboundDelay(item.xrayJson, settings.checkUrl).toInt() }
                    .onSuccess { if (it >= 0) samples += it else error = "negative_delay" }
                    .onFailure { error = it.javaClass.simpleName }
            }
            val ok = samples.size >= settings.minSuccess.coerceAtLeast(1)
            CheckResult(item, ok, if (ok) samples.average().toInt() else null, "xray", if (ok) "" else error)
        } else {
            val samples = mutableListOf<Int>(); var error = "unreachable"
            repeat(settings.attempts.coerceIn(1, 8)) {
                val started = System.nanoTime()
                runCatching { Socket().use { it.connect(InetSocketAddress(item.host, item.port), 3500) } }
                    .onSuccess { samples += ((System.nanoTime() - started) / 1_000_000).toInt() }
                    .onFailure { error = it.javaClass.simpleName }
            }
            val ok = samples.size >= settings.minSuccess.coerceAtLeast(1)
            CheckResult(item, ok, if (ok) samples.average().toInt() else null, if (item.proxy) "telegram-tcp" else "tcp-fallback", if (ok) "" else error)
        }
        update(index + 1, filtered.size, "${if (result.ok) "OK" else "FAIL"} ${item.protocol} ${item.host}:${item.port} ${result.ping ?: "-"}ms • ${result.tester}")
        result
    }.sortedWith(compareBy<CheckResult> { !it.ok }.thenBy { it.ping ?: Int.MAX_VALUE })
}

private fun parseCandidate(raw: String, source: String): Candidate? = runCatching {
    val lower = raw.lowercase()
    if (lower.startsWith("tg://") || lower.startsWith("https://t.me/proxy") || lower.startsWith("https://t.me/socks")) {
        val uri = Uri.parse(raw)
        val host = uri.getQueryParameter("server") ?: return@runCatching null
        val port = uri.getQueryParameter("port")?.toIntOrNull() ?: return@runCatching null
        val protocol = if (lower.contains("socks")) "telegram-socks" else "telegram-mtproto"
        return@runCatching Candidate(raw, source, protocol, host, port, true)
    }
    when {
        lower.startsWith("vmess://") -> parseVmess(raw, source)
        lower.startsWith("vless://") -> parseUrlConfig(raw, source, "vless")
        lower.startsWith("trojan://") -> parseUrlConfig(raw, source, "trojan")
        lower.startsWith("ss://") -> parseSs(raw, source)
        else -> {
            val uri = Uri.parse(raw)
            val host = uri.host ?: return@runCatching null
            val port = if (uri.port > 0) uri.port else 443
            Candidate(raw, source, uri.scheme ?: "unknown", host, port, false)
        }
    }
}.getOrNull()

private fun parseVmess(raw: String, source: String): Candidate? {
    val body = raw.substringAfter("vmess://").replace('-', '+').replace('_', '/')
    val padded = body + "=".repeat((4 - body.length % 4) % 4)
    val obj = JSONObject(String(Base64.decode(padded, Base64.DEFAULT)))
    val host = obj.optString("add").ifBlank { obj.optString("host") }
    val port = obj.optString("port").toIntOrNull() ?: 443
    val user = JSONObject().put("id", obj.optString("id")).put("alterId", obj.optInt("aid", 0)).put("security", obj.optString("scy", "auto"))
    val outbound = JSONObject().put("tag", "proxy").put("protocol", "vmess").put("settings", JSONObject().put("vnext", JSONArray().put(JSONObject().put("address", host).put("port", port).put("users", JSONArray().put(user))))).put("streamSettings", streamFromVmess(obj))
    return Candidate(raw, source, "vmess", host, port, false, rootConfig(outbound).toString())
}

private fun parseUrlConfig(raw: String, source: String, protocol: String): Candidate? {
    val uri = Uri.parse(raw)
    val host = uri.host ?: return null
    val port = if (uri.port > 0) uri.port else 443
    val userInfo = uri.userInfo ?: return null
    val decodedUser = URLDecoder.decode(userInfo.substringBefore(':'), "UTF-8")
    val q = { key: String -> uri.getQueryParameter(key).orEmpty() }
    val outbound = if (protocol == "vless") {
        val user = JSONObject().put("id", decodedUser).put("encryption", q("encryption").ifBlank { "none" })
        q("flow").takeIf { it.isNotBlank() }?.let { user.put("flow", it) }
        JSONObject().put("tag", "proxy").put("protocol", "vless").put("settings", JSONObject().put("vnext", JSONArray().put(JSONObject().put("address", host).put("port", port).put("users", JSONArray().put(user)))))
    } else {
        JSONObject().put("tag", "proxy").put("protocol", "trojan").put("settings", JSONObject().put("servers", JSONArray().put(JSONObject().put("address", host).put("port", port).put("password", decodedUser))))
    }
    outbound.put("streamSettings", streamFromUri(uri))
    return Candidate(raw, source, protocol, host, port, false, rootConfig(outbound).toString())
}

private fun parseSs(raw: String, source: String): Candidate? {
    val noFragment = raw.substringBefore('#')
    val body = noFragment.substringAfter("ss://").substringBefore('?')
    val decoded = if (body.contains('@')) body else {
        val normalized = body.replace('-', '+').replace('_', '/')
        String(Base64.decode(normalized + "=".repeat((4 - normalized.length % 4) % 4), Base64.DEFAULT))
    }
    val full = URLDecoder.decode(decoded, "UTF-8")
    val userInfo = full.substringBeforeLast('@')
    val hostPort = full.substringAfterLast('@')
    val method = userInfo.substringBefore(':')
    val password = userInfo.substringAfter(':')
    val host = hostPort.substringBeforeLast(':')
    val port = hostPort.substringAfterLast(':').toIntOrNull() ?: return null
    val outbound = JSONObject().put("tag", "proxy").put("protocol", "shadowsocks").put("settings", JSONObject().put("servers", JSONArray().put(JSONObject().put("address", host).put("port", port).put("method", method).put("password", password))))
    return Candidate(raw, source, "ss", host, port, false, rootConfig(outbound).toString())
}

private fun rootConfig(outbound: JSONObject) = JSONObject()
    .put("log", JSONObject().put("loglevel", "warning"))
    .put("outbounds", JSONArray().put(outbound).put(JSONObject().put("tag", "direct").put("protocol", "freedom")))

private fun streamFromVmess(obj: JSONObject): JSONObject {
    val fake = Uri.Builder().scheme("vmess").authority("x").appendQueryParameter("type", obj.optString("net", "tcp")).appendQueryParameter("security", obj.optString("tls", "none")).appendQueryParameter("host", obj.optString("host")).appendQueryParameter("path", obj.optString("path")).appendQueryParameter("sni", obj.optString("sni")).appendQueryParameter("alpn", obj.optString("alpn")).build()
    return streamFromUri(fake)
}

private fun streamFromUri(uri: Uri): JSONObject {
    val network = uri.getQueryParameter("type") ?: uri.getQueryParameter("net") ?: "tcp"
    val security = uri.getQueryParameter("security") ?: "none"
    val host = uri.getQueryParameter("host").orEmpty()
    val path = uri.getQueryParameter("path") ?: uri.getQueryParameter("serviceName") ?: ""
    val stream = JSONObject().put("network", if (network == "splithttp") "xhttp" else network)
    if (security != "none" && security.isNotBlank()) {
        stream.put("security", security)
        val sni = uri.getQueryParameter("sni") ?: uri.getQueryParameter("serverName") ?: ""
        val fp = uri.getQueryParameter("fp").orEmpty()
        if (security == "tls") stream.put("tlsSettings", JSONObject().apply { if (sni.isNotBlank()) put("serverName", sni); if (fp.isNotBlank()) put("fingerprint", fp); put("allowInsecure", uri.getQueryParameter("insecure") == "1") })
        if (security == "reality") stream.put("realitySettings", JSONObject().apply { if (sni.isNotBlank()) put("serverName", sni); if (fp.isNotBlank()) put("fingerprint", fp); uri.getQueryParameter("pbk")?.let { put("publicKey", it) }; uri.getQueryParameter("sid")?.let { put("shortId", it) }; uri.getQueryParameter("spx")?.let { put("spiderX", it) } })
    }
    when (network.lowercase()) {
        "ws" -> stream.put("wsSettings", JSONObject().apply { if (path.isNotBlank()) put("path", path); if (host.isNotBlank()) put("headers", JSONObject().put("Host", host)) })
        "grpc" -> stream.put("grpcSettings", JSONObject().apply { if (path.isNotBlank()) put("serviceName", path) })
        "xhttp", "splithttp" -> stream.put("xhttpSettings", JSONObject().apply { if (path.isNotBlank()) put("path", path); if (host.isNotBlank()) put("host", host); uri.getQueryParameter("mode")?.let { put("mode", it) } })
        "httpupgrade" -> stream.put("httpupgradeSettings", JSONObject().apply { if (path.isNotBlank()) put("path", path); if (host.isNotBlank()) put("host", host) })
    }
    return stream
}

private fun normalizeChannel(value: String): String? {
    val clean = value.trim().removePrefix("https://").removePrefix("http://").removePrefix("t.me/").removePrefix("s/").substringBefore('/')
    return clean.takeIf { it.matches(Regex("[A-Za-z0-9_]{4,}")) }
}

private fun writeOutputs(root: File, results: List<CheckResult>, settings: SettingsState): List<File> {
    val dir = File(root, "DicodeConfigChecker").apply { mkdirs() }
    val alive = results.filter { it.ok }
    val configs = alive.filter { !it.item.proxy }.mapIndexed { index, r -> if (settings.renameNames) renameConfig(r.item.raw, "${settings.tagPrefix}-${index + 1}") else r.item.raw }
    val proxies = alive.filter { it.item.proxy }.map { it.item.raw }
    val reportRows = JSONArray().also { array -> results.forEach { r -> array.put(JSONObject().put("raw", r.item.raw).put("source", r.item.source).put("protocol", r.item.protocol).put("host", r.item.host).put("port", r.item.port).put("alive", r.ok).put("ping_ms", r.ping ?: JSONObject.NULL).put("tester", r.tester).put("error", r.error)) } }
    val report = JSONObject().put("version", VERSION).put("platform", "android").put("generated_at", Instant.now().toString()).put("xray_version", runCatching { Libv2ray.checkVersionX() }.getOrDefault("unknown")).put("results", reportRows)
    fun file(name: String, value: String) = File(dir, name).apply { writeText(value) }
    return listOf(file("sub.txt", configs.joinToString("\n")), file("proxy.txt", proxies.joinToString("\n")), file("sub_base64.txt", Base64.encodeToString(configs.joinToString("\n").toByteArray(), Base64.NO_WRAP)), file("proxy_base64.txt", Base64.encodeToString(proxies.joinToString("\n").toByteArray(), Base64.NO_WRAP)), file("report.json", report.toString(2)))
}

private fun renameConfig(raw: String, name: String): String = raw.substringBefore('#') + "#" + Uri.encode(name)

private fun share(context: Context, file: File) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_STREAM, uri); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION) }, "اشتراک‌گذاری خروجی"))
}
