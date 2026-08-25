from pathlib import Path
import re

main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")


def add_import(anchor: str, new_imports: str) -> None:
    global text
    if new_imports.splitlines()[0] in text:
        return
    if anchor not in text:
        raise SystemExit(f"missing import anchor: {anchor}")
    text = text.replace(anchor, anchor + "\n" + new_imports, 1)


text = re.sub(r'private const val VERSION = "[^"]+"', 'private const val VERSION = "1.5.1"', text, count=1)
add_import(
    "import androidx.compose.ui.platform.LocalContext",
    "import androidx.compose.ui.platform.LocalLayoutDirection\nimport androidx.compose.ui.text.font.Font\nimport androidx.compose.ui.text.font.FontFamily\nimport androidx.compose.ui.unit.LayoutDirection",
)

color_marker = re.search(r"private val Bad = Color\(0x[0-9A-Fa-f]{8}\)", text)
if color_marker is None:
    raise SystemExit("color marker missing")
font_block = f'''{color_marker.group(0)}
private val VazirmatnFamily = FontFamily(Font(R.font.vazirmatn_regular))
private val DicodeTypography = Typography().let {{ base ->
    Typography(
        displayLarge = base.displayLarge.copy(fontFamily = VazirmatnFamily),
        displayMedium = base.displayMedium.copy(fontFamily = VazirmatnFamily),
        displaySmall = base.displaySmall.copy(fontFamily = VazirmatnFamily),
        headlineLarge = base.headlineLarge.copy(fontFamily = VazirmatnFamily),
        headlineMedium = base.headlineMedium.copy(fontFamily = VazirmatnFamily),
        headlineSmall = base.headlineSmall.copy(fontFamily = VazirmatnFamily),
        titleLarge = base.titleLarge.copy(fontFamily = VazirmatnFamily),
        titleMedium = base.titleMedium.copy(fontFamily = VazirmatnFamily),
        titleSmall = base.titleSmall.copy(fontFamily = VazirmatnFamily),
        bodyLarge = base.bodyLarge.copy(fontFamily = VazirmatnFamily),
        bodyMedium = base.bodyMedium.copy(fontFamily = VazirmatnFamily),
        bodySmall = base.bodySmall.copy(fontFamily = VazirmatnFamily),
        labelLarge = base.labelLarge.copy(fontFamily = VazirmatnFamily),
        labelMedium = base.labelMedium.copy(fontFamily = VazirmatnFamily),
        labelSmall = base.labelSmall.copy(fontFamily = VazirmatnFamily),
    )
}}'''
if "VazirmatnFamily" not in text:
    text = text.replace(color_marker.group(0), font_block, 1)

old = "MaterialTheme(colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card)) {"
new = '''CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card),
            typography = DicodeTypography,
        ) {'''
if old in text:
    text = text.replace(old, new, 1)
    boundary = "\n}\n\n@Composable\nprivate fun DashboardPage"
    if boundary not in text:
        raise SystemExit("DicodeApp closing boundary missing")
    text = text.replace(boundary, "\n    }\n}\n\n@Composable\nprivate fun DashboardPage", 1)
elif "CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl)" not in text:
    raise SystemExit("MaterialTheme marker missing")

manifest_path = Path("android/app/src/main/AndroidManifest.xml")
manifest = manifest_path.read_text(encoding="utf-8")
if 'android:supportsRtl="true"' not in manifest:
    manifest = manifest.replace("<application", '<application\n        android:supportsRtl="true"', 1)
manifest_path.write_text(manifest, encoding="utf-8")

theme_path = Path("android/app/src/main/res/values/themes.xml")
theme = theme_path.read_text(encoding="utf-8")
theme = re.sub(r'<item name="android:fontFamily">.*?</item>', '<item name="android:fontFamily">@font/vazirmatn_regular</item>', theme, count=1)
theme_path.write_text(theme, encoding="utf-8")

gradle_path = Path("android/app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r"versionCode\s*=\s*\d+", "versionCode = 151", gradle, count=1)
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.5.1"', gradle, count=1)
gradle_path.write_text(gradle, encoding="utf-8")

required = ('private const val VERSION = "1.5.1"', "VazirmatnFamily", "LocalLayoutDirection provides LayoutDirection.Rtl")
if not all(value in text for value in required):
    raise SystemExit("Android v1.5.1 RTL/font markers are missing")
main_path.write_text(text, encoding="utf-8")
print("Android v1.5.1 RTL and Vazirmatn patch applied")
