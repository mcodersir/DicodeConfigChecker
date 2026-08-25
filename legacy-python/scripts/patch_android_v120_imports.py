from pathlib import Path

path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = path.read_text(encoding="utf-8")

replacements = {
    "import androidx.compose.foundation.lazy.items\n": "import androidx.compose.foundation.lazy.items\nimport androidx.compose.foundation.lazy.itemsIndexed\n",
    "import androidx.compose.ui.text.AnnotatedString\n": "import androidx.compose.ui.text.AnnotatedString\nimport androidx.compose.ui.text.TextStyle\n",
}

for old, new in replacements.items():
    if new.strip() in text:
        continue
    if old not in text:
        raise SystemExit(f"missing expected import anchor: {old.strip()}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Android v1.2.0 missing imports added")
