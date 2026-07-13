from pathlib import Path
import re

main_path = Path("android/app/src/main/java/ir/dicode/configchecker/MainActivity.kt")
text = main_path.read_text(encoding="utf-8")

text = text.replace('private const val VERSION = "1.3.0"', 'private const val VERSION = "1.4.0"', 1)

icon_imports = '''import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons