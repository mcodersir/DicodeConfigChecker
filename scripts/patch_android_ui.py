from pathlib import Path
import re

path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = path.read_text(encoding="utf-8")
channels = "\n".join(
    line.strip() for line in Path("channels.txt").read_text(encoding="utf-8").splitlines() if line.strip()
)


def once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: source block changed")
    text = text.replace(old, new, 1)


def regex(pattern: str, replacement: str, name: str) -> None:
    global text
    # Replacement blocks include Kotlin regexes (for example `\\s`), so pass
    # them through a callable and keep Python's regex engine from interpreting
    # their backslashes as replacement escapes.
    text, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{name}: source block changed")


once(
    "import androidx.compose.foundation.background",
    """import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateIntAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background""",
    "animation imports",
)
once(
    "import androidx.compose.foundation.rememberScrollState",
    """import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState""",
    "lazy imports",
)
once("import androidx.compose.ui.unit.dp", "import androidx.compose.ui.unit.dp\nimport androidx.compose.ui.unit.sp", "sp import")
once(
    "import kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.launch\nimport kotlinx.coroutines.withContext",
    """import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit""",
    "coroutine imports",
)
once("import java.util.concurrent.ConcurrentHashMap", "import java.util.concurrent.ConcurrentHashMap\nimport java.util.concurrent.atomic.AtomicInteger", "atomic import")

palette = {
    "private val Bg = Color(0xFF090D12)": "private val Bg = Color(0xFF070B10)",
    "private val Card = Color(0xFF111821)": "private val Card = Color(0xFF0D141D)",
    "private val Card2 = Color(0xFF0D141D)": "private val Card2 = Color(0xFF111A24)",
    "private val Accent = Color(0xFF3B82F6)": "private val Accent = Color(0xFF2A9FFF)",
    "private val Text = Color(0xFFEAF1FA)": "private val Text = Color(0xFFEAF5FF)",
    "private val Muted = Color(0xFF9CAABC)": "private val Muted = Color(0xFF8FA3B8)",
    "private val Good = Color(0xFF22C55E)": "private val Good = Color(0xFF34D399)",
    "private val Bad = Color(0xFFEF4444)": "private val Bad = Color(0xFFFB7185)",
}
for old, new in palette.items():
    once(old, new, "palette")

once(
    "private val Bad = Color(0xFFFB7185)",
    f'''private val Bad = Color(0xFFFB7185)
private val Warn = Color(0xFFFBBF24)
private val DefaultChannels = """
{channels}
""".trimIndent()''',
    "default channels",
)
once(
    "    val fetchWorkers: Int = 8,\n    val attempts: Int = 2,",
    "    val fetchWorkers: Int = 12,\n    val pingWorkers: Int = 12,\n    val tcpTimeoutMs: Int = 2200,\n    val attempts: Int = 2,",
    "worker settings",
)
once(
    "Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)",
    "Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 14.dp, vertical = 8.dp)",
    "status inset",
)
once(
    "NavigationBar(containerColor = Card) {",
    "NavigationBar(containerColor = Card, modifier = Modifier.navigationBarsPadding()) {",
    "nav inset",
)
once(
    "Modifier.size(42.dp).background(Card2, RoundedCornerShape(13.dp))",
    "Modifier.size(36.dp).background(Card2, RoundedCornerShape(10.dp))",
    "header icon",
)
regex(
    r'''    var priority2 by rememberSaveable \{\n        mutableStateOf\("t\.me/PrivateVPNs.*?"\)\n    \}''',
    "    var priority2 by rememberSaveable { mutableStateOf(DefaultChannels) }",
    "channel defaults",
)
once(
    '            NumberField("Fetch workers", value.fetchWorkers) { onChange(value.copy(fetchWorkers = it)) }',
    '''            NumberField("دریافت همزمان کانال ها", value.fetchWorkers) { onChange(value.copy(fetchWorkers = it.coerceIn(1, 24))) }
            NumberField("تست همزمان پینگ", value.pingWorkers) { onChange(value.copy(pingWorkers = it.coerceIn(1, 24))) }
            NumberField("مهلت TCP برحسب ms", value.tcpTimeoutMs) { onChange(value.copy(tcpTimeoutMs = it.coerceIn(800, 10000))) }''',
    "worker controls",
)

# Compact responsive metrics and actions.
old_metrics = '''        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("دریافت", collected.size, Muted, Modifier.weight(1f))
            Metric("سالم", results.count { it.ok }, Good, Modifier.weight(1f))
            Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f))
            Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
        }'''
new_metrics = '''        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("دریافت", collected.size, Muted, Modifier.weight(1f))
            Metric("سالم", results.count { it.ok }, Good, Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f))
            Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
        }'''
once(old_metrics, new_metrics, "metrics")
old_actions = '''            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.weight(1f)) { Text("شروع از ابتدا") }
                OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.weight(1f)) { Text("اشتراک خروجی") }
            }'''
new_actions = '''            OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("شروع از ابتدا") }
            OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("اشتراک خروجی") }'''
once(old_actions, new_actions, "actions")

# Better live log rendering with semantic highlighting and animated progress.
once(
    '            LinearProgressIndicator(progress = { progress.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth().height(8.dp))',
    '''            val animatedProgress by animateFloatAsState(progress.coerceIn(0f, 1f), tween(260), label = "progress")
            AnimatedVisibility(visible = busy || animatedProgress > 0f, enter = fadeIn(), exit = fadeOut()) {
                LinearProgressIndicator(progress = { animatedProgress }, modifier = Modifier.fillMaxWidth().height(5.dp), color = Accent, trackColor = Card2)
            }''',
    "progress animation",
)
once(
    '            Text(if (logs.isEmpty()) "هنوز عملیاتی اجرا نشده" else logs.joinToString("\\n"), color = Muted, style = MaterialTheme.typography.bodySmall)',
    '''            if (logs.isEmpty()) Text("هنوز عملیاتی اجرا نشده", color = Muted, fontSize = 11.sp)
            else logs.takeLast(14).asReversed().forEach { LogLine(it) }''',
    "log list",
)
once(
    '''@Composable private fun NumberField(label: String, value: Int, onChange: (Int) -> Unit) {''',
    '''@Composable private fun LogLine(message: String) {
    val color = when {
        message.startsWith("[OK]") -> Good
        message.startsWith("[FAIL]") || message.startsWith("[ERROR]") -> Bad
        message.startsWith("[WARN]") -> Warn
        message.startsWith("[FETCH]") -> Accent
        else -> Muted
    }
    Surface(color = color.copy(alpha = .08f), shape = RoundedCornerShape(9.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 9.dp, vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(6.dp).background(color, RoundedCornerShape(99.dp)))
            Spacer(Modifier.width(7.dp))
            Text(message, color = color, fontSize = 10.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable private fun NumberField(label: String, value: Int, onChange: (Int) -> Unit) {''',
    "log helper",
)

# Lazy output list prevents UI stalls on hundreds of results.
regex(
    r'''@Composable\nprivate fun OutputPage\(.*?\n\}\n\n@Composable private fun PageHeader''',
    '''@Composable
private fun OutputPage(title: String, rows: List<CheckResult>, file: File?, context: Context) {
    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { PageHeader(title, "${rows.count { it.ok }} سالم از ${rows.size} مورد") }
        if (file != null) item { Button(onClick = { share(context, file) }, modifier = Modifier.fillMaxWidth()) { Text("اشتراک گذاری ${file.name}") } }
        items(rows, key = { "${it.item.raw}-${it.tester}" }) { row ->
            Surface(color = Card, shape = RoundedCornerShape(12.dp)) {
                Column(Modifier.fillMaxWidth().padding(12.dp)) {
                    Text("${if (row.ok) "سالم" else "ناموفق"} • ${row.item.protocol.uppercase()} • ${row.ping ?: "-"} ms", color = if (row.ok) Good else Bad, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Text("${row.item.host}:${row.item.port} • ${row.tester}", color = Muted, fontSize = 10.sp)
                    Text(row.item.raw, color = Text, fontSize = 9.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
            }
        }
        if (rows.isEmpty()) item { Text("هنوز خروجی ساخته نشده است.", color = Muted) }
    }
}

@Composable private fun PageHeader''',
    "lazy output",
)

# Fetch all channels concurrently with a bounded worker pool.
regex(
    r'''private suspend fun collectAll\(.*?\n\}\n\nprivate suspend fun testAll''',
    '''private suspend fun collectAll(
    priority1: String,
    priority2: String,
    settings: SettingsState,
    update: (Int, Int, String) -> Unit,
): List<Candidate> = coroutineScope {
    val first = priority1.lines().mapNotNull(::normalizeChannel).distinctBy { it.lowercase() }
    val second = priority2.lines().mapNotNull(::normalizeChannel).distinctBy { it.lowercase() }.filterNot { c -> first.any { it.equals(c, true) } }
    val channels = first.map { it to settings.priorityLimit } + second.map { it to settings.perChannelLimit }
    val found = ConcurrentHashMap<String, Candidate>()
    val completed = AtomicInteger(0)
    val semaphore = Semaphore(settings.fetchWorkers.coerceIn(1, 24))
    channels.map { (channel, limit) ->
        async(Dispatchers.IO) {
            val message = semaphore.withPermit {
                runCatching {
                    val conn = URL("https://t.me/s/$channel").openConnection() as HttpURLConnection
                    try {
                        conn.connectTimeout = 8000; conn.readTimeout = 8000
                        conn.setRequestProperty("User-Agent", "Mozilla/5.0 DicodeConfigChecker/$VERSION")
                        val html = conn.inputStream.bufferedReader().use { it.readText() }.replace("&amp;", "&")
                        val linkRegex = Regex("(?:vmess|vless|trojan|ss|ssr|snell|hysteria2|hy2|tuic)://[^\\s<>\\\"'`]+|(?:tg://(?:proxy|socks)|https://t\\.me/(?:proxy|socks))\\?[^\\s<>\\\"'`]+", RegexOption.IGNORE_CASE)
                        var count = 0
                        linkRegex.findAll(html).map { it.value.trimEnd(')', ']', '}', ',', '.', ';') }.take(limit).forEach { raw ->
                            parseCandidate(raw, channel)?.let {
                                val key = if (it.protocol == "vmess") it.raw else it.raw.substringBefore('#')
                                if (found.putIfAbsent(key.lowercase(), it) == null) count++
                            }
                        }
                        "[FETCH] @$channel • +$count • کل ${found.size}"
                    } finally { conn.disconnect() }
                }.getOrElse { "[ERROR] @$channel • ${it.javaClass.simpleName}" }
            }
            val done = completed.incrementAndGet()
            withContext(Dispatchers.Main) { update(done, channels.size, message) }
        }
    }.awaitAll()
    found.values.toList()
}

private suspend fun testAll''',
    "parallel fetch",
)

# Parallel ping pipeline: fast TCP prefilter, bounded Xray workers, explicit timeouts.
regex(
    r'''private suspend fun testAll\(.*?\n\}\n\nprivate fun parseCandidate''',
    '''private suspend fun testAll(items: List<Candidate>, settings: SettingsState, update: (Int, Int, String) -> Unit): List<CheckResult> = coroutineScope {
    val filtered = items.filter { if (it.proxy) settings.checkProxies else settings.checkConfigs }
    val completed = AtomicInteger(0)
    val xrayPool = Semaphore(settings.pingWorkers.coerceIn(1, 6))
    val tcpPool = Semaphore((settings.pingWorkers * 2).coerceIn(2, 24))
    filtered.map { item ->
        async(Dispatchers.IO) {
            val result = if (!item.proxy && item.xrayJson != null) {
                val prefilter = if (settings.tcpPrefilter) tcpDelay(item, settings.tcpTimeoutMs.coerceIn(800, 10000)) else 0
                if (settings.tcpPrefilter && prefilter == null) CheckResult(item, false, null, "tcp-prefilter", "unreachable")
                else xrayPool.withPermit {
                    val samples = mutableListOf<Int>(); var error = "xray_failed"
                    repeat(settings.attempts.coerceIn(1, 4)) {
                        val measured = withTimeoutOrNull(9000L) { runCatching { Libv2ray.measureOutboundDelay(item.xrayJson, settings.checkUrl).toInt() } }
                        when {
                            measured == null -> error = "timeout"
                            measured.isSuccess && measured.getOrThrow() >= 0 -> samples += measured.getOrThrow()
                            measured.isSuccess -> error = "negative_delay"
                            else -> error = measured.exceptionOrNull()?.javaClass?.simpleName ?: "xray_failed"
                        }
                    }
                    val ok = samples.size >= settings.minSuccess.coerceAtLeast(1)
                    CheckResult(item, ok, if (ok) median(samples) else null, "xray", if (ok) "" else error)
                }
            } else tcpPool.withPermit {
                val samples = mutableListOf<Int>()
                repeat(settings.attempts.coerceIn(1, 4)) { tcpDelay(item, settings.tcpTimeoutMs.coerceIn(800, 10000))?.let(samples::add) }
                val ok = samples.size >= settings.minSuccess.coerceAtLeast(1)
                CheckResult(item, ok, if (ok) median(samples) else null, if (item.proxy) "telegram-tcp" else "tcp-fallback", if (ok) "" else "timeout_or_refused")
            }
            val done = completed.incrementAndGet()
            val prefix = if (result.ok) "[OK]" else "[FAIL]"
            withContext(Dispatchers.Main) { update(done, filtered.size, "$prefix ${item.protocol.uppercase()} • ${item.host}:${item.port} • ${result.ping ?: "-"}ms • ${result.tester}") }
            result
        }
    }.awaitAll().sortedWith(compareBy<CheckResult> { !it.ok }.thenBy { it.ping ?: Int.MAX_VALUE })
}

private fun tcpDelay(item: Candidate, timeoutMs: Int): Int? {
    val started = System.nanoTime()
    return runCatching {
        Socket().use { it.connect(InetSocketAddress(item.host, item.port), timeoutMs) }
        ((System.nanoTime() - started) / 1_000_000).toInt()
    }.getOrNull()
}

private fun median(values: List<Int>): Int {
    val sorted = values.sorted(); val mid = sorted.size / 2
    return if (sorted.size % 2 == 1) sorted[mid] else (sorted[mid - 1] + sorted[mid]) / 2
}

private fun parseCandidate''',
    "parallel ping",
)

path.write_text(text, encoding="utf-8")
print(f"Android performance patch applied with {len(channels.splitlines())} channels")
