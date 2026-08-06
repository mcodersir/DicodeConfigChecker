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
    "import androidx.compose.ui.platform.LocalLayoutDirection\nimport androidx.compose.ui.text.font.Font\nimport androidx.compose.ui.text.font.FontFamily\nimport androidx.compose.ui.text.platform.Typeface\nimport androidx.compose.ui.unit.LayoutDirection",
)

marker = "private val Bad = Color(0xFFEF4444)"
font_block = '''private val Bad = Color(0xFFEF4444)
private val VazirmatnFamily = FontFamily(Font(R.font.vazirmatn_regular))
private val DicodeTypography = Typography(
    displayLarge = Typography().displayLarge.copy(fontFamily = VazirmatnFamily),
    displayMedium = Typography().displayMedium.copy(fontFamily = VazirmatnFamily),
    displaySmall = Typography().displaySmall.copy(fontFamily = VazirmatnFamily),
    headlineLarge = Typography().headlineLarge.copy(fontFamily = VazirmatnFamily),
    headlineMedium = Typography().headlineMedium.copy(fontFamily = VazirmatnFamily),
    headlineSmall = Typography().headlineSmall.copy(fontFamily = VazirmatnFamily),
    titleLarge = Typography().titleLarge.copy(fontFamily = VazirmatnFamily),
    titleMedium = Typography().titleMedium.copy(fontFamily = VazirmatnFamily),
    titleSmall = Typography().titleSmall.copy(fontFamily = VazirmatnFamily),
    bodyLarge = Typography().bodyLarge.copy(fontFamily = VazirmatnFamily),
    bodyMedium = Typography().bodyMedium.copy(fontFamily = VazirmatnFamily),
    bodySmall = Typography().bodySmall.copy(fontFamily = VazirmatnFamily),
    labelLarge = Typography().labelLarge.copy(fontFamily = VazirmatnFamily),
    labelMedium = Typography().labelMedium.copy(fontFamily = VazirmatnFamily),
    labelSmall = Typography().labelSmall.copy(fontFamily = VazirmatnFamily),
)'''
if "VazirmatnFamily" not in text:
    if marker not in text:
        raise SystemExit("color marker missing")
    text = text.replace(marker, font_block, 1)

old = "MaterialTheme(colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card)) {"
new = '''CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = darkColorScheme(primary = Accent, background = Bg, surface = Card),
            typography = DicodeTypography,
        ) {'''
if old in text:
    text = text.replace(old, new, 1)
    # DicodeApp ends immediately before the next @Composable declaration.
    boundary = "\n}\n\n@Composable\nprivate fun DashboardPage"
    if boundary not in text:
        raise SystemExit("DicodeApp closing boundary missing")
    text = text.replace(boundary, "\n    }\n}\n\n@Composable\nprivate fun DashboardPage", 1)
elif "CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl)" not in text:
    raise SystemExit("MaterialTheme marker missing")

# Ensure manifest and theme explicitly opt into RTL and the bundled font.
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

required = (
    'private const val VERSION = "1.5.1"',
    "VazirmatnFamily",
    "LocalLayoutDirection provides LayoutDirection.Rtl",
)
if not all(value in text for value in required):
    raise SystemExit("Android v1.5.1 RTL/font markers are missing")
main_path.write_text(text, encoding="utf-8")
print("Android v1.5.1 RTL and Vazirmatn patch applied")
