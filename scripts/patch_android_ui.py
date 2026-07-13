from pathlib import Path

path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)",
    "Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 14.dp, vertical = 8.dp)",
    1,
)
text = text.replace(
    "NavigationBar(containerColor = Card) {",
    "NavigationBar(containerColor = Card, modifier = Modifier.navigationBarsPadding()) {",
    1,
)

replacements = {
    "private val Bg = Color(0xFF090D12)": "private val Bg = Color(0xFF070B10)",
    "private val Card = Color(0xFF111821)": "private val Card = Color(0xFF0D141D)",
    "private val Card2 = Color(0xFF0D141D)": "private val Card2 = Color(0xFF111A24)",
    "private val Accent = Color(0xFF3B82F6)": "private val Accent = Color(0xFF2A9FFF)",
    "private val Text = Color(0xFFEAF1FA)": "private val Text = Color(0xFFEAF5FF)",
    "private val Muted = Color(0xFF9CAABC)": "private val Muted = Color(0xFF8FA3B8)",
    "private val Good = Color(0xFF22C55E)": "private val Good = Color(0xFF34D399)",
    "private val Bad = Color(0xFFEF4444)": "private val Bad = Color(0xFFFB7185)",
    "Modifier.size(42.dp).background(Card2, RoundedCornerShape(13.dp))": "Modifier.size(36.dp).background(Card2, RoundedCornerShape(10.dp))",
    "Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)": "Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 10.dp)",
    "Modifier.fillMaxWidth().background(Card, RoundedCornerShape(18.dp)).padding(16.dp)": "Modifier.fillMaxWidth().background(Card, RoundedCornerShape(14.dp)).padding(14.dp)",
    "modifier.background(Card, RoundedCornerShape(14.dp)).padding(vertical = 12.dp)": "modifier.background(Card, RoundedCornerShape(12.dp)).padding(vertical = 10.dp)",
}
for old, new in replacements.items():
    text = text.replace(old, new)

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
text = text.replace(old_metrics, new_metrics, 1)

old_actions = '''            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.weight(1f)) { Text("شروع از ابتدا") }
                OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.weight(1f)) { Text("اشتراک خروجی") }
            }'''
new_actions = '''            OutlinedButton(onClick = onReset, enabled = !busy, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("شروع از ابتدا") }
            OutlinedButton(onClick = onOpenOutputs, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(11.dp)) { Text("اشتراک خروجی") }'''
text = text.replace(old_actions, new_actions, 1)

path.write_text(text, encoding="utf-8")
print("Android responsive UI patch applied")
