package ir.dicode.configchecker

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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

private const val VERSION = "1.1.0"
private val Bg = Color(0xFF090D12)
private val Card = Color(0xFF111821)
private val Accent = Color(0xFF3B82F6)
private val Text = Color(0xFFEAF1FA)
private val Muted = Color(0xFF9CAABC)

private data class Item(val raw: String, val source: String, val host: String, val port: Int, val proxy: Boolean)
private data class Result(val item: Item, val ok: Boolean, val ping: Int?, val error: String)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { App() }
    }
}

@Composable
private fun App() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var channels by remember { mutableStateOf("t.me/dicodeir\nt.me/PrivateVPNs\nt.me/v2rayNG_Matsuri\nt.me/vmess_ir") }
    var collected by remember { mutableStateOf<List<Item>>(emptyList()) }
    var results by remember { mutableStateOf<List<Result>>(emptyList()) }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("آماده") }
    var progress by remember { mutableFloatStateOf(0f) }
    var logs by remember { mutableStateOf(listOf<String>()) }
    var files by remember { mutableStateOf<List<File>>(emptyList()) }

    MaterialTheme(colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card)) {
        Surface(Modifier.fillMaxSize(), color = Bg) {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("Dicode Config Checker", color = Text, fontWeight = FontWeight.Black, style = MaterialTheme.typography.headlineSmall)
                        Text("Android Preview v$VERSION", color = Muted)
                    }
                    AssistChip(onClick = {}, label = { Text(if (busy) "در حال اجرا" else "آماده") })
                }

                Panel {
                    Text("وضعیت", color = Muted)
                    Text(status, color = Text, fontWeight = FontWeight.Bold)
                    LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth().height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Metric("دریافت", collected.size.toString())
                        Metric("سالم", results.count { it.ok }.toString())
                        Metric("ناموفق", results.count { !it.ok }.toString())
                    }
                }

                Panel {
                    Text("کانال‌های عمومی", color = Text, fontWeight = FontWeight.Bold)
                    OutlinedTextField(
                        value = channels,
                        onValueChange = { channels = it },
                        enabled = !busy,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 130.dp),
                        supportingText = { Text("هر خط یک کانال عمومی؛ t.me یا نام کاربری") },
                    )
                    Button(
                        onClick = {
                            busy = true; results = emptyList(); files = emptyList(); logs = emptyList(); progress = 0f
                            scope.launch {
                                runCatching {
                                    collectConfigs(channels) { done, total, msg ->
                                        progress = if (total == 0) 0f else done.toFloat() / total
                                        status = "دریافت از تلگرام: $done از $total"
                                        logs = (logs + msg).takeLast(80)
                                    }
                                }.onSuccess {
                                    collected = it; status = "اتصال فعلی را قطع کنید، سپس تست را اجرا کنید"; progress = 1f
                                }.onFailure {
                                    status = "خطا: ${it.message}"; logs = logs + "ERROR: ${it.javaClass.simpleName}"
                                }
                                busy = false
                            }
                        },
                        enabled = !busy,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("۱. دریافت کانفیگ‌ها") }
                    Button(
                        onClick = {
                            busy = true; progress = 0f; results = emptyList()
                            scope.launch {
                                runCatching {
                                    testItems(collected) { done, total, value ->
                                        progress = if (total == 0) 0f else done.toFloat() / total
                                        status = "تست دسترسی: $done از $total"
                                        logs = (logs + value).takeLast(80)
                                    }
                                }.onSuccess {
                                    results = it
                                    files = writeOutputs(context.getExternalFilesDir(null)!!, it)
                                    status = "خروجی‌ها آماده‌اند"
                                    progress = 1f
                                }.onFailure { status = "خطا: ${it.message}" }
                                busy = false
                            }
                        },
                        enabled = !busy && collected.isNotEmpty(),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("۲. تست و ساخت خروجی") }
                }

                if (files.isNotEmpty()) Panel {
                    Text("خروجی‌ها", color = Text, fontWeight = FontWeight.Bold)
                    files.forEach { file ->
                        OutlinedButton(onClick = { share(context, file) }, modifier = Modifier.fillMaxWidth()) {
                            Text("اشتراک‌گذاری ${file.name}")
                        }
                    }
                }

                Panel {
                    Text("گزارش اجرا", color = Text, fontWeight = FontWeight.Bold)
                    Text(if (logs.isEmpty()) "هنوز عملیاتی اجرا نشده" else logs.joinToString("\n"), color = Muted, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable private fun Panel(content: @Composable ColumnScope.() -> Unit) = Column(
    Modifier.fillMaxWidth().background(Card, RoundedCornerShape(18.dp)).padding(16.dp),
    verticalArrangement = Arrangement.spacedBy(10.dp), content = content,
)

@Composable private fun Metric(label: String, value: String) = Column(horizontalAlignment = Alignment.CenterHorizontally) {
    Text(value, color = Text, fontWeight = FontWeight.Black)
    Text(label, color = Muted, style = MaterialTheme.typography.labelSmall)
}

private suspend fun collectConfigs(text: String, update: (Int, Int, String) -> Unit): List<Item> = withContext(Dispatchers.IO) {
    val channels = text.lines().mapNotNull(::normalizeChannel).distinctBy { it.lowercase() }
    val found = ConcurrentHashMap<String, Item>()
    channels.forEachIndexed { index, channel ->
        val message = runCatching {
            val conn = URL("https://t.me/s/$channel").openConnection() as HttpURLConnection
            conn.connectTimeout = 12000; conn.readTimeout = 12000
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 DicodeConfigChecker/$VERSION")
            val html = conn.inputStream.bufferedReader().use { it.readText() }.replace("&amp;", "&")
            val regex = Regex("(?:vmess|vless|trojan|ss|ssr|snell|hysteria2|hy2|tuic)://[^\\s<>\\\"'`]+|(?:tg://(?:proxy|socks)|https://t\\.me/(?:proxy|socks))\\?[^\\s<>\\\"'`]+", RegexOption.IGNORE_CASE)
            regex.findAll(html).map { it.value.trimEnd(')', ']', '}', ',', '.', ';') }.take(30).forEach { raw ->
                parseItem(raw, channel)?.let { found.putIfAbsent(it.raw.substringBefore('#').lowercase(), it) }
            }
            "@$channel | ${found.size} مورد یکتا"
        }.getOrElse { "@$channel | خطا: ${it.javaClass.simpleName}" }
        update(index + 1, channels.size, message)
    }
    found.values.toList()
}

private suspend fun testItems(items: List<Item>, update: (Int, Int, String) -> Unit): List<Result> = withContext(Dispatchers.IO) {
    items.mapIndexed { index, item ->
        val samples = mutableListOf<Int>(); var error = "unreachable"
        repeat(3) {
            val start = System.nanoTime()
            runCatching { Socket().use { it.connect(InetSocketAddress(item.host, item.port), 3500) } }
                .onSuccess { samples += ((System.nanoTime() - start) / 1_000_000).toInt() }
                .onFailure { error = it.javaClass.simpleName }
        }
        val ok = samples.size >= 2
        val result = Result(item, ok, if (ok) samples.average().toInt() else null, if (ok) "" else error)
        update(index + 1, items.size, "${if (ok) "OK" else "FAIL"} ${item.host}:${item.port} ${result.ping ?: "-"}ms")
        result
    }.sortedWith(compareBy<Result> { !it.ok }.thenBy { it.ping ?: Int.MAX_VALUE })
}

private fun parseItem(raw: String, source: String): Item? = runCatching {
    if (raw.startsWith("vmess://", true)) {
        val body = raw.substringAfter("vmess://").replace('-', '+').replace('_', '/')
        val padded = body + "=".repeat((4 - body.length % 4) % 4)
        val json = JSONObject(String(Base64.decode(padded, Base64.DEFAULT)))
        val host = json.optString("add").ifBlank { json.optString("host") }
        val port = json.optString("port").toInt()
        Item(raw, source, host, port, false)
    } else {
        val uri = Uri.parse(raw)
        val proxy = raw.startsWith("tg://", true) || raw.startsWith("https://t.me/proxy", true) || raw.startsWith("https://t.me/socks", true)
        val host = if (proxy) uri.getQueryParameter("server") else uri.host
        val port = if (proxy) uri.getQueryParameter("port")?.toIntOrNull() else uri.port.takeIf { it > 0 } ?: 443
        if (host.isNullOrBlank() || port == null) null else Item(raw, source, host, port, proxy)
    }
}.getOrNull()

private fun normalizeChannel(value: String): String? {
    val clean = value.trim().removePrefix("https://").removePrefix("http://").removePrefix("t.me/").removePrefix("s/").substringBefore('/')
    return clean.takeIf { it.matches(Regex("[A-Za-z0-9_]{4,}")) }
}

private fun writeOutputs(root: File, results: List<Result>): List<File> {
    val dir = File(root, "DicodeConfigChecker").apply { mkdirs() }
    val alive = results.filter { it.ok }
    val configs = alive.filter { !it.item.proxy }.map { it.item.raw }
    val proxies = alive.filter { it.item.proxy }.map { it.item.raw }
    val reportRows = JSONArray().also { array -> results.forEach { r -> array.put(JSONObject().apply {
        put("raw", r.item.raw); put("source", r.item.source); put("host", r.item.host); put("port", r.item.port)
        put("alive", r.ok); put("ping_ms", r.ping ?: JSONObject.NULL); put("error", r.error)
    }) } }
    val report = JSONObject().apply {
        put("version", VERSION); put("platform", "android"); put("generated_at", Instant.now().toString()); put("results", reportRows)
    }
    fun file(name: String, value: String) = File(dir, name).apply { writeText(value) }
    return listOf(
        file("sub.txt", configs.joinToString("\n")),
        file("proxy.txt", proxies.joinToString("\n")),
        file("sub_base64.txt", Base64.encodeToString(configs.joinToString("\n").toByteArray(), Base64.NO_WRAP)),
        file("proxy_base64.txt", Base64.encodeToString(proxies.joinToString("\n").toByteArray(), Base64.NO_WRAP)),
        file("report.json", report.toString(2)),
    )
}

private fun share(context: android.content.Context, file: File) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"; putExtra(Intent.EXTRA_STREAM, uri); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }, "اشتراک‌گذاری خروجی"))
}
