from pathlib import Path
import re

path = Path('android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt')
text = path.read_text(encoding='utf-8')

text = text.replace('import androidx.compose.ui.unit.dp', 'import androidx.compose.ui.unit.dp\nimport androidx.compose.ui.unit.sp')
text = text.replace('WindowCompat.setDecorFitsSystemWindows(window, false)', 'WindowCompat.setDecorFitsSystemWindows(window, true)')
text = text.replace('private val Bg = Color(0xFF090D12)', 'private val Bg = Color(0xFF070B10)')
text = text.replace('private val Card = Color(0xFF111821)', 'private val Card = Color(0xFF0D141D)')
text = text.replace('private val Card2 = Color(0xFF0D141D)', 'private val Card2 = Color(0xFF111A24)')
text = text.replace('private val Accent = Color(0xFF3B82F6)', 'private val Accent = Color(0xFF2A9FFF)')
text = text.replace('private val Text = Color(0xFFEAF1FA)', 'private val Text = Color(0xFFEAF5FF)')
text = text.replace('private val Muted = Color(0xFF9CAABC)', 'private val Muted = Color(0xFF8FA3B8)')
text = text.replace('private val Good = Color(0xFF22C55E)', 'private val Good = Color(0xFF34D399)')
text = text.replace('private val Bad = Color(0xFFEF4444)', 'private val Bad = Color(0xFFFB7185)')
text = text.replace('contentWindowInsets = WindowInsets.safeDrawing,', 'contentWindowInsets = WindowInsets(0, 0, 0, 0),')

old_top = '''            topBar = {
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
            },'''
new_top = '''            topBar = {
                Surface(color = Card, tonalElevation = 0.dp) {
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(38.dp).background(Card2, RoundedCornerShape(11.dp)), contentAlignment = Alignment.Center) {
                            Text("ϟ", color = Color(0xFF68E8FF), fontSize = 23.sp, fontWeight = FontWeight.Black)
                        }
                        Spacer(Modifier.width(9.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Dicode Config Checker", color = Text, fontSize = 15.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text("Android • Xray Core • v$VERSION", color = Muted, fontSize = 10.sp, maxLines = 1)
                        }
                        Surface(color = if (busy) Accent.copy(alpha = .18f) else Card2, shape = RoundedCornerShape(9.dp)) {
                            Text(if (busy) "در حال اجرا" else "آماده", color = if (busy) Color(0xFF68E8FF) else Muted, fontSize = 10.sp, modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp), maxLines = 1)
                        }
                    }
                }
            },'''
if old_top not in text:
    raise SystemExit('top bar block not found')
text = text.replace(old_top, new_top)

old_bottom = '''            bottomBar = {
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
            },'''
new_bottom = '''            bottomBar = {
                Surface(color = Card, tonalElevation = 0.dp) {
                    Row(Modifier.fillMaxWidth().height(62.dp).padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        Page.entries.forEach { item ->
                            val selected = page == item
                            TextButton(onClick = { page = item }, modifier = Modifier.weight(1f).fillMaxHeight(), contentPadding = PaddingValues(2.dp)) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                                    Text(when (item) { Page.Dashboard -> "⌂"; Page.Settings -> "⚙"; Page.Channels -> "≡"; Page.Configs -> "✓"; Page.Proxies -> "ϟ" }, color = if (selected) Color(0xFF68E8FF) else Muted, fontSize = 17.sp)
                                    Text(item.title, color = if (selected) Color(0xFF68E8FF) else Muted, fontSize = 9.sp, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            },'''
if old_bottom not in text:
    raise SystemExit('bottom bar block not found')
text = text.replace(old_bottom, new_bottom)

new_dashboard = '''@Composable
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
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val compact = maxWidth < 420.dp
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (compact) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Metric("دریافت", collected.size, Muted, Modifier.weight(1f)); Metric("سالم", results.count { it.ok }, Good, Modifier.weight(1f))
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f)); Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
                }
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Metric("دریافت", collected.size, Muted, Modifier.weight(1f)); Metric("سالم", results.count { it.ok }, Good, Modifier.weight(1f)); Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f)); Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
                }
            }
            Panel {
                Text("وضعیت اجرا", color = Text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(status, color = Muted, fontSize = 12.sp)
                LinearProgressIndicator(progress = { progress.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth().height(5.dp), color = Accent, trackColor = Card2)
                if (waitingDisconnect) Text("قبل از ادامه، VPN یا کانفیگ فعلی را کامل قطع کن.", color = Color(0xFFFBBF24), fontSize = 11.sp)
            }
            Panel {
                Text("کنترل عملیات", color = Text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Button(onClick = onCollect, enabled = !busy, modifier = Modifier.fillMaxWidth().height(47.dp), shape = RoundedCornerShape(11.dp)) { Text("۱. دریافت کانفیگ ها") }
                OutlinedButton(onClick = onTest, enabled = !busy && collected.isNotEmpty(), modifier = Modifier.fillMaxWidth().height(47.dp), shape = RoundedCornerShape(11.dp)) { Text("۲. تست واقعی و ساخت خروجی") }
                if (compact) {
                    OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("شروع از ابتدا") }
                    OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("اشتراک خروجی") }
                } else {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.weight(1f), shape = RoundedCornerShape(11.dp)) { Text("شروع از ابتدا") }
                        OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.weight(1f), shape = RoundedCornerShape(11.dp)) { Text("اشتراک خروجی") }
                    }
                }
            }
            Panel {
                Text("لاگ زنده", color = Text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(if (logs.isEmpty()) "هنوز عملیاتی اجرا نشده" else logs.joinToString("\\n"), color = Muted, fontSize = 11.sp, lineHeight = 17.sp)
            }
        }
    }
}

@Composable
private fun SettingsPage'''
text, count = re.subn(r'@Composable\nprivate fun DashboardPage\(.*?\n@Composable\nprivate fun SettingsPage', new_dashboard, text, flags=re.S)
if count != 1:
    raise SystemExit(f'dashboard replacement count={count}')

old_panel = '''@Composable private fun Panel(content: @Composable ColumnScope.() -> Unit) = Column(
    Modifier.fillMaxWidth().background(Card, RoundedCornerShape(18.dp)).padding(16.dp),
    verticalArrangement = Arrangement.spacedBy(10.dp), content = content,
)'''
new_panel = '''@Composable private fun Panel(content: @Composable ColumnScope.() -> Unit) = Surface(
    color = Card, shape = RoundedCornerShape(14.dp), tonalElevation = 0.dp,
) { Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp), content = content) }'''
if old_panel not in text:
    raise SystemExit('panel block not found')
text = text.replace(old_panel, new_panel)

old_metric = '''@Composable private fun Metric(label: String, value: Int, color: Color, modifier: Modifier = Modifier) = Column(
    modifier.background(Card, RoundedCornerShape(14.dp)).padding(vertical = 12.dp), horizontalAlignment = Alignment.CenterHorizontally,
) {
    Text(value.toString(), color = color, fontWeight = FontWeight.Black)
    Text(label, color = Muted, style = MaterialTheme.typography.labelSmall)
}'''
new_metric = '''@Composable private fun Metric(label: String, value: Int, color: Color, modifier: Modifier = Modifier) = Surface(
    modifier = modifier, color = Card, shape = RoundedCornerShape(13.dp), tonalElevation = 0.dp,
) { Column(Modifier.fillMaxWidth().padding(vertical = 12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
    Text(value.toString(), color = color, fontSize = 20.sp, fontWeight = FontWeight.Black)
    Text(label, color = Muted, fontSize = 10.sp)
} }'''
if old_metric not in text:
    raise SystemExit('metric block not found')
text = text.replace(old_metric, new_metric)

path.write_text(text, encoding='utf-8')
print('Android UI patched successfully')
