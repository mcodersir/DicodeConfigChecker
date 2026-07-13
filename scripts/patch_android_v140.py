from pathlib import Path
import re

main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if text.count(old) != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {text.count(old)}")
    text = text.replace(old, new, 1)


def replace_regex(pattern: str, replacement: str, name: str) -> None:
    global text
    text, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one match, found {count}")


replace_once('private const val VERSION = "1.3.0"', 'private const val VERSION = "1.4.0"', "version")

replace_once(
    "import androidx.compose.material3.*",
    """import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*""",
    "material icon imports",
)

dashboard = r'''@Composable
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
    val collectedDone = collected.isNotEmpty()
    val testedDone = results.isNotEmpty()
    val healthyCount = results.count { it.ok }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Surface(
            color = Card,
            shape = RoundedCornerShape(22.dp),
            border = BorderStroke(1.dp, Accent.copy(alpha = .18f)),
        ) {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("مرکز عملیات", color = Text, fontSize = 19.sp, fontWeight = FontWeight.Black)
                        Text("دریافت، قطع اتصال فعلی و تست واقعی", color = Muted, fontSize = 11.sp)
                    }
                    Surface(
                        color = if (busy) Accent.copy(alpha = .14f) else Good.copy(alpha = .12f),
                        shape = RoundedCornerShape(99.dp),
                    ) {
                        Text(
                            if (busy) "در حال اجرا" else "آماده",
                            color = if (busy) Accent else Good,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
                        )
                    }
                }
                Text(status, color = Text, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                val animatedProgress by animateFloatAsState(progress.coerceIn(0f, 1f), tween(260), label = "home-progress")
                AnimatedVisibility(visible = busy || animatedProgress > 0f, enter = fadeIn(), exit = fadeOut()) {
                    LinearProgressIndicator(
                        progress = { animatedProgress },
                        modifier = Modifier.fillMaxWidth().height(5.dp),
                        color = Accent,
                        trackColor = Card2,
                    )
                }
            }
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("دریافت شده", collected.size, Muted, Modifier.weight(1f))
            Metric("سالم", healthyCount, Good, Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("ناموفق", results.count { !it.ok }, Bad, Modifier.weight(1f))
            Metric("Xray", results.count { it.tester == "xray" }, Accent, Modifier.weight(1f))
        }

        HomeStepCard(
            number = 1,
            title = "دریافت از کانال ها",
            subtitle = if (collectedDone) "${collected.size} مورد دریافت شد" else "کانفیگ ها و پروکسی های عمومی را جمع آوری می کند",
            completed = collectedDone,
            active = busy && !collectedDone,
            buttonText = if (collectedDone) "انجام شد" else "شروع دریافت",
            enabled = !busy && !collectedDone,
            onClick = onCollect,
        )

        if (waitingDisconnect) VpnDisconnectCard()

        HomeStepCard(
            number = 2,
            title = "تست واقعی و ساخت خروجی",
            subtitle = when {
                testedDone -> "$healthyCount خروجی سالم آماده است"
                !collectedDone -> "ابتدا مرحله دریافت را انجام بده"
                else -> "پس از قطع اتصال فعلی، همه موارد را بررسی می کند"
            },
            completed = testedDone,
            active = busy && collectedDone,
            buttonText = if (testedDone) "انجام شد" else "شروع تست واقعی",
            enabled = !busy && collectedDone && !testedDone,
            onClick = onTest,
        )

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = onReset,
                enabled = !busy && (collectedDone || testedDone),
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Muted),
            ) {
                Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text("شروع دوباره", fontSize = 12.sp)
            }
            FilledTonalButton(
                onClick = onOpenOutputs,
                enabled = testedDone,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.filledTonalButtonColors(containerColor = Accent.copy(alpha = .15f), contentColor = Accent),
            ) {
                Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text("خروجی ها", fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }

        Surface(color = Card, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Color(0xFF243244))) {
            Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text("گزارش زنده", color = Text, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                if (logs.isEmpty()) Text("هنوز عملیاتی اجرا نشده", color = Muted, fontSize = 11.sp)
                else logs.takeLast(10).asReversed().forEach { LogLine(it) }
            }
        }
    }
}

@Composable
private fun HomeStepCard(
    number: Int,
    title: String,
    subtitle: String,
    completed: Boolean,
    active: Boolean,
    buttonText: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val stateColor = when {
        completed -> Good
        active -> Accent
        enabled -> Accent
        else -> Muted
    }
    Surface(
        color = Card,
        shape = RoundedCornerShape(19.dp),
        border = BorderStroke(1.dp, stateColor.copy(alpha = if (completed || active) .32f else .14f)),
    ) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Surface(color = stateColor.copy(alpha = .13f), shape = RoundedCornerShape(12.dp)) {
                    Box(Modifier.size(42.dp), contentAlignment = Alignment.Center) {
                        if (completed) Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Good, modifier = Modifier.size(23.dp))
                        else Text(number.toString(), color = stateColor, fontWeight = FontWeight.Black, fontSize = 16.sp)
                    }
                }
                Spacer(Modifier.width(11.dp))
                Column(Modifier.weight(1f)) {
                    Text(title, color = Text, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Text(subtitle, color = Muted, fontSize = 10.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
                if (completed) Text("تکمیل", color = Good, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
            Button(
                onClick = onClick,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth().height(46.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Accent,
                    contentColor = Color.White,
                    disabledContainerColor = if (completed) Good.copy(alpha = .12f) else Card2,
                    disabledContentColor = if (completed) Good else Muted.copy(alpha = .65f),
                ),
            ) {
                if (completed) Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(18.dp))
                else Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(19.dp))
                Spacer(Modifier.width(7.dp))
                Text(buttonText, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun SettingsPage'''

replace_regex(
    r'''@Composable\nprivate fun DashboardPage\(.*?\n\}\n\n@Composable\nprivate fun SettingsPage''',
    dashboard,
    "dashboard redesign",
)

replace_once(
    '''Button(onClick = { clipboard.setText(AnnotatedString(lines.joinToString("\\n"))); Toast.makeText(context, "${lines.size} مورد کپی شد", Toast.LENGTH_SHORT).show() }, enabled = lines.isNotEmpty(), modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color.White)) { Text("کپی همه", fontWeight = FontWeight.Bold) }''',
    '''Button(onClick = { clipboard.setText(AnnotatedString(lines.joinToString("\\n"))); Toast.makeText(context, "${lines.size} مورد کپی شد", Toast.LENGTH_SHORT).show() }, enabled = lines.isNotEmpty(), modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color.White)) { Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(7.dp)); Text("کپی همه", fontWeight = FontWeight.Bold) }''',
    "copy all icon button",
)
replace_once(
    '''FilledTonalButton(onClick = { file?.let { share(context, it) } }, enabled = file != null, modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Card2, contentColor = Text)) { Text("اشتراک فایل", fontWeight = FontWeight.Bold) }''',
    '''FilledTonalButton(onClick = { file?.let { share(context, it) } }, enabled = file != null, modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Card2, contentColor = Text)) { Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(7.dp)); Text("اشتراک فایل", fontWeight = FontWeight.Bold) }''',
    "share file icon button",
)
replace_once(
    '''TextButton(onClick = { clipboard.setText(AnnotatedString(lines[index])); Toast.makeText(context, "کپی شد", Toast.LENGTH_SHORT).show() }) { Text("کپی", color = Accent) }''',
    '''FilledTonalButton(onClick = { clipboard.setText(AnnotatedString(lines[index])); Toast.makeText(context, "کپی شد", Toast.LENGTH_SHORT).show() }, shape = RoundedCornerShape(11.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Accent.copy(alpha = .13f), contentColor = Accent)) { Icon(Icons.Default.ContentCopy, contentDescription = "کپی", modifier = Modifier.size(17.dp)); Spacer(Modifier.width(5.dp)); Text("کپی", fontSize = 11.sp) }''',
    "item copy icon button",
)
replace_once(
    '''if (isProxy) TextButton(onClick = { openTelegramProxy(context, row.item.raw) }) { Text("باز کردن در تلگرام", color = Good) }''',
    '''if (isProxy) { Spacer(Modifier.width(6.dp)); FilledTonalButton(onClick = { openTelegramProxy(context, row.item.raw) }, shape = RoundedCornerShape(11.dp), colors = ButtonDefaults.filledTonalButtonColors(containerColor = Good.copy(alpha = .13f), contentColor = Good)) { Icon(Icons.Default.OpenInNew, contentDescription = "باز کردن در تلگرام", modifier = Modifier.size(17.dp)); Spacer(Modifier.width(5.dp)); Text("تلگرام", fontSize = 11.sp, fontWeight = FontWeight.Bold) } }''',
    "telegram icon button",
)

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 140", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.4.0"', gradle, count=1)
if "material-icons-extended" not in gradle:
    gradle = gradle.replace(
        'implementation("androidx.compose.material3:material3")',
        'implementation("androidx.compose.material3:material3")\n    implementation("androidx.compose.material:material-icons-extended")',
        1,
    )
gradle_path.write_text(gradle, encoding="utf-8")

if 'private const val VERSION = "1.4.0"' not in text:
    raise SystemExit("Android Kotlin version is not 1.4.0")
if "HomeStepCard(" not in text or "Icons.Default.ContentCopy" not in text or "Icons.Default.OpenInNew" not in text:
    raise SystemExit("Android v1.4.0 UI markers are missing")

main_path.write_text(text, encoding="utf-8")
print("Android v1.4.0 dashboard and output actions applied")
