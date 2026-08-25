from pathlib import Path
import re

path = Path('android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt')
text = path.read_text(encoding='utf-8')

def once(old, new, name):
    global text
    if old not in text:
        raise SystemExit(f'{name}: source block changed')
    text = text.replace(old, new, 1)

def regex(pattern, replacement, name):
    global text
    text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{name}: source block changed')

once('private const val VERSION = "1.1.0"', 'private const val VERSION = "1.2.0"', 'version')

once('import android.content.Context\nimport android.content.Intent', '''import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.VpnService
import android.provider.Settings
import android.widget.Toast''', 'android imports')
once('import androidx.activity.compose.setContent', '''import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts''', 'activity imports')
once('import androidx.compose.foundation.background', '''import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable''', 'foundation imports')
once('import androidx.compose.ui.platform.LocalContext', '''import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext''', 'clipboard import')
once('import androidx.compose.ui.text.font.FontWeight', '''import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight''', 'annotated string')
once('import androidx.compose.ui.text.style.TextOverflow', '''import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.text.style.TextOverflow''', 'direction import')

once('private enum class Page(val title: String) {\n    Dashboard("داشبورد"), Settings("تنظیمات"), Channels("کانال‌ها"), Configs("کانفیگ‌ها"), Proxies("پروکسی‌ها")\n}', '''private enum class Page(val title: String) {
    Dashboard("خانه"), Configs("کانفیگ ها"), Proxies("پروکسی ها"), Channels("کانال ها"), Settings("تنظیمات")
}

private enum class SettingsTab(val title: String) { Fetch("دریافت"), Test("تست"), Output("خروجی") }''', 'page enums')

regex(r'''            bottomBar = \{.*?            \},\n        \) \{ padding ->''', '''            bottomBar = {
                Surface(color = Card, shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp), shadowElevation = 16.dp) {
                    Row(
                        Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 8.dp, vertical = 7.dp),
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Page.entries.forEach { item ->
                            val selected = page == item
                            Column(
                                Modifier.weight(1f).background(if (selected) Accent.copy(alpha = .16f) else Color.Transparent, RoundedCornerShape(15.dp))
                                    .clickable { page = item }.padding(vertical = 8.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(3.dp),
                            ) {
                                Text(
                                    when (item) { Page.Dashboard -> "⌂"; Page.Configs -> "✓"; Page.Proxies -> "ϟ"; Page.Channels -> "≡"; Page.Settings -> "⚙" },
                                    color = if (selected) Accent else Muted,
                                    fontSize = 19.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(item.title, color = if (selected) Text else Muted, fontSize = 10.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium)
                            }
                        }
                    }
                }
            },
        ) { padding ->''', 'bottom navigation')

once('if (waitingDisconnect) Text("قبل از ادامه، VPN یا کانفیگ فعلی را کامل قطع کن.", color = Color(0xFFFBBF24))', 'if (waitingDisconnect) VpnDisconnectCard()', 'vpn card')
once('Page.Configs -> OutputPage("کانفیگ‌ها", results.filter { !it.item.proxy }, files.firstOrNull { it.name == "sub.txt" }, context)', 'Page.Configs -> OutputPage("کانفیگ ها", results.filter { it.ok && !it.item.proxy }, files.firstOrNull { it.name == "sub.txt" }, context, false, settings)', 'config filter')
once('Page.Proxies -> OutputPage("پروکسی‌ها", results.filter { it.item.proxy }, files.firstOrNull { it.name == "proxy.txt" }, context)', 'Page.Proxies -> OutputPage("پروکسی ها", results.filter { it.ok && it.item.proxy }, files.firstOrNull { it.name == "proxy.txt" }, context, true, settings)', 'proxy filter')

regex(r'''@Composable\nprivate fun SettingsPage\(value: SettingsState, onChange: \(SettingsState\) -> Unit\) \{.*?\n\}\n\n@Composable\nprivate fun ChannelsPage''', '''@Composable
private fun SettingsPage(value: SettingsState, onChange: (SettingsState) -> Unit) {
    var tab by rememberSaveable { mutableStateOf(SettingsTab.Fetch) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PageHeader("تنظیمات", "گزینه ها دسته بندی شده اند")
        Surface(color = Card, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, Color(0xFF243244))) {
            Row(Modifier.fillMaxWidth().padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                SettingsTab.entries.forEach { item ->
                    val selected = item == tab
                    Box(
                        Modifier.weight(1f).background(if (selected) Accent else Color.Transparent, RoundedCornerShape(12.dp))
                            .clickable { tab = item }.padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center,
                    ) { Text(item.title, color = if (selected) Color.White else Muted, fontSize = 12.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium) }
                }
            }
        }
        when (tab) {
            SettingsTab.Fetch -> Panel {
                Text("دریافت از کانال ها", color = Text, fontWeight = FontWeight.Bold)
                NumberField("تعداد از هر کانال رتبه دوم", value.perChannelLimit) { onChange(value.copy(perChannelLimit = it.coerceIn(1, 200))) }
                NumberField("تعداد از هر کانال رتبه اول", value.priorityLimit) { onChange(value.copy(priorityLimit = it.coerceIn(1, 300))) }
                NumberField("دریافت همزمان کانال ها", value.fetchWorkers) { onChange(value.copy(fetchWorkers = it.coerceIn(1, 24))) }
            }
            SettingsTab.Test -> Panel {
                Text("تست واقعی", color = Text, fontWeight = FontWeight.Bold)
                NumberField("تست همزمان پینگ", value.pingWorkers) { onChange(value.copy(pingWorkers = it.coerceIn(1, 24))) }
                NumberField("مهلت TCP برحسب ms", value.tcpTimeoutMs) { onChange(value.copy(tcpTimeoutMs = it.coerceIn(800, 10000))) }
                NumberField("تعداد تلاش", value.attempts) { onChange(value.copy(attempts = it.coerceIn(1, 4), minSuccess = value.minSuccess.coerceAtMost(it.coerceIn(1, 4)))) }
                NumberField("حداقل موفقیت", value.minSuccess) { onChange(value.copy(minSuccess = it.coerceIn(1, value.attempts))) }
                TextFieldRow("URL تست واقعی", value.checkUrl) { onChange(value.copy(checkUrl = it)) }
                Toggle("بررسی کانفیگ های Xray", value.checkConfigs) { onChange(value.copy(checkConfigs = it)) }
                Toggle("بررسی پروکسی های تلگرام", value.checkProxies) { onChange(value.copy(checkProxies = it)) }
                Toggle("پیش فیلتر سریع TCP", value.tcpPrefilter) { onChange(value.copy(tcpPrefilter = it)) }
            }
            SettingsTab.Output -> Panel {
                Text("خروجی", color = Text, fontWeight = FontWeight.Bold)
                TextFieldRow("متن نام کانفیگ", value.tagPrefix) { onChange(value.copy(tagPrefix = it)) }
                Toggle("بازنویسی نام کانفیگ", value.renameNames) { onChange(value.copy(renameNames = it)) }
                Text("فایل ها و تب های خروجی فقط موارد سالم را نمایش می دهند.", color = Muted, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun ChannelsPage''', 'settings tabs')

regex(r'''@Composable\nprivate fun OutputPage\(.*?\n\}\n\n@Composable private fun PageHeader''', '''@Composable
private fun OutputPage(title: String, rows: List<CheckResult>, file: File?, context: Context, isProxy: Boolean, settings: SettingsState) {
    val clipboard = LocalClipboardManager.current
    val lines = rows.mapIndexed { index, row -> if (isProxy) row.item.raw else if (settings.renameNames) renameConfig(row.item.raw, "${settings.tagPrefix}-${index + 1}") else row.item.raw }
    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        item { PageHeader(title, "${rows.size} مورد سالم؛ موارد ناموفق مخفی شده اند") }
        item {
            Panel {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { clipboard.setText(AnnotatedString(lines.joinToString("\\n"))); Toast.makeText(context, "${lines.size} مورد کپی شد", Toast.LENGTH_SHORT).show() }, enabled = lines.isNotEmpty(), modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color.White)) { Text("کپی همه", fontWeight = FontWeight.Bold) }
                    FilledTonalButton(onClick = { file?.let { share(context, it) } }, enabled = file != null, modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Card2, contentColor = Text)) { Text("اشتراک فایل", fontWeight = FontWeight.Bold) }
                }
            }
        }
        itemsIndexed(rows, key = { _, row -> "${row.item.raw}-${row.tester}" }) { index, row ->
            Surface(color = Card, shape = RoundedCornerShape(17.dp), border = BorderStroke(1.dp, Color(0xFF243244))) {
                Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Surface(color = Accent.copy(alpha = .14f), shape = RoundedCornerShape(9.dp)) { Text(row.item.protocol.uppercase(), color = Accent, fontSize = 10.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)) }
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) {
                            Text("${row.item.host}:${row.item.port}", color = Text, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis, style = TextStyle(textDirection = TextDirection.Ltr))
                            Text("@${row.item.source} • ${row.tester}", color = Muted, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        Surface(color = Good.copy(alpha = .13f), shape = RoundedCornerShape(99.dp)) { Text("${row.ping ?: "-"} ms", color = Good, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp)) }
                    }
                    Text(lines[index], color = Muted, fontSize = 10.sp, maxLines = 2, overflow = TextOverflow.Ellipsis, style = TextStyle(textDirection = TextDirection.Ltr))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { clipboard.setText(AnnotatedString(lines[index])); Toast.makeText(context, "کپی شد", Toast.LENGTH_SHORT).show() }) { Text("کپی", color = Accent) }
                        if (isProxy) TextButton(onClick = { openTelegramProxy(context, row.item.raw) }) { Text("باز کردن در تلگرام", color = Good) }
                    }
                }
            }
        }
        if (rows.isEmpty()) item { Text("خروجی سالمی وجود ندارد.", color = Muted, modifier = Modifier.fillMaxWidth().padding(vertical = 48.dp), textAlign = androidx.compose.ui.text.style.TextAlign.Center) }
    }
}

@Composable private fun PageHeader''', 'output page')

regex(r'''@Composable private fun NumberField\(label: String, value: Int, onChange: \(Int\) -> Unit\) \{.*?\n\}\n\n@Composable private fun TextFieldRow''', '''@Composable private fun NumberField(label: String, value: Int, onChange: (Int) -> Unit) {
    OutlinedTextField(value = value.toString(), onValueChange = { it.filter(Char::isDigit).toIntOrNull()?.let(onChange) }, label = { Text(label) }, modifier = Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(15.dp), colors = appFieldColors())
}

@Composable private fun TextFieldRow''', 'number field')
regex(r'''@Composable private fun TextFieldRow\(label: String, value: String, onChange: \(String\) -> Unit\) \{.*?\n\}\n\n@Composable private fun Toggle''', '''@Composable private fun TextFieldRow(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(value = value, onValueChange = onChange, label = { Text(label) }, modifier = Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(15.dp), colors = appFieldColors(), textStyle = TextStyle(textDirection = TextDirection.Ltr))
}

@Composable private fun Toggle''', 'text field')
regex(r'''@Composable private fun Toggle\(label: String, checked: Boolean, onChange: \(Boolean\) -> Unit\) \{.*?\n\}\n\nprivate suspend fun collectAll''', '''@Composable private fun Toggle(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Surface(color = Card2, shape = RoundedCornerShape(15.dp)) {
        Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }.padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(label, color = Text, modifier = Modifier.weight(1f), fontSize = 13.sp, fontWeight = FontWeight.Medium)
            Switch(checked = checked, onCheckedChange = onChange, colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Accent, uncheckedThumbColor = Muted, uncheckedTrackColor = Color(0xFF263445)))
        }
    }
}

@Composable private fun appFieldColors() = OutlinedTextFieldDefaults.colors(focusedTextColor = Text, unfocusedTextColor = Text, focusedContainerColor = Card2, unfocusedContainerColor = Card2, focusedBorderColor = Accent, unfocusedBorderColor = Color(0xFF263445), focusedLabelColor = Accent, unfocusedLabelColor = Muted, cursorColor = Accent)

@Composable
private fun VpnDisconnectCard() {
    val context = LocalContext.current
    var message by remember { mutableStateOf("") }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) { requestVpnTakeover(context); message = "درخواست قطع VPN ارسال شد؛ چند لحظه بعد تست را بزن." } else message = "مجوز قطع VPN داده نشد."
    }
    Surface(color = Warn.copy(alpha = .09f), shape = RoundedCornerShape(15.dp), border = BorderStroke(1.dp, Warn.copy(alpha = .25f))) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("VPN فعال است", color = Warn, fontWeight = FontWeight.Bold)
            Text("بدون رفتن به برنامه دیگر، از دکمه زیر برای قطع اتصال فعلی استفاده کن.", color = Muted, fontSize = 11.sp)
            Button(onClick = { val intent = VpnService.prepare(context); if (intent != null) launcher.launch(intent) else { requestVpnTakeover(context); message = "درخواست قطع VPN ارسال شد." } }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = Warn, contentColor = Color(0xFF1B1400))) { Text("قطع VPN از داخل برنامه", fontWeight = FontWeight.Bold) }
            if (message.isNotBlank()) Text(message, color = Warn, fontSize = 11.sp)
            TextButton(onClick = { openVpnSettings(context) }, modifier = Modifier.align(Alignment.End)) { Text("تنظیمات VPN", color = Muted) }
        }
    }
}

private suspend fun collectAll''', 'switch and vpn card')

once('private fun share(context: Context, file: File) {', '''private fun openTelegramProxy(context: Context, raw: String) {
    val telegramUri = when {
        raw.startsWith("https://t.me/proxy", true) -> Uri.parse(raw.replaceFirst("https://t.me/proxy", "tg://proxy", true))
        raw.startsWith("https://t.me/socks", true) -> Uri.parse(raw.replaceFirst("https://t.me/socks", "tg://socks", true))
        else -> Uri.parse(raw)
    }
    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, telegramUri)) }.onFailure { Toast.makeText(context, "تلگرام یا برنامه سازگار پیدا نشد", Toast.LENGTH_SHORT).show() }
}

private fun requestVpnTakeover(context: Context) {
    runCatching { context.startService(Intent(context, VpnKickService::class.java).setAction(VpnKickService.ACTION_DISCONNECT_ACTIVE_VPN)) }.onFailure { openVpnSettings(context) }
}

private fun openVpnSettings(context: Context) {
    runCatching { context.startActivity(Intent(Settings.ACTION_VPN_SETTINGS)) }.onFailure { context.startActivity(Intent(Settings.ACTION_WIRELESS_SETTINGS)) }
}

private fun share(context: Context, file: File) {''', 'helpers')

path.write_text(text, encoding='utf-8')
print('Android v1.2.0 UX patch applied')
