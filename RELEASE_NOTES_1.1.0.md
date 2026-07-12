# Dicode Config Checker v1.1.0 Preview

این نسخه یک پیش‌انتشار چندسکویی است. نسخه پایدار **v1.0.1 حذف نشده** و تمام فایل‌های آن در Releases باقی می‌ماند.

## تغییرات اصلی

- خروجی مستقل برای Windows، Linux x86_64 و Android
- رابط مینیمال و تاریک Android نزدیک به طراحی نسخه دسکتاپ
- فرایند دو مرحله‌ای دریافت کانفیگ و سپس تست بعد از قطع اتصال فعلی
- جمع‌آوری از Telegram Preview بدون نیاز به ورود به حساب
- تفکیک کانفیگ‌ها و پروکسی‌های Telegram
- ساخت `sub.txt`، `proxy.txt`، خروجی Base64 و `report.json`
- اشتراک‌گذاری مستقیم فایل‌های خروجی در Android
- پشتیبانی Xray در نسخه‌های دسکتاپ و مسیر سازگار با Linux
- بهبود High-DPI و Retry درخواست‌های موقت Telegram در دسکتاپ
- تست‌های خودکار Parser و فایل SHA-256 برای خروجی‌های انتشار

## فایل‌های انتشار

- `DicodeConfigChecker-v1.1.0-windows.exe`
- `DicodeConfigChecker-v1.1.0-linux-x86_64.tar.gz`
- `DicodeConfigChecker-v1.1.0-android-preview.apk`
- `DicodeConfigChecker-source-v1.1.0.zip`
- `SHA256SUMS.txt`

## محدودیت نسخه Android Preview

در Android تست فعلی با چند اتصال TCP به مقصد انجام می‌شود. تست عبور واقعی ترافیک از Xray فعلاً در نسخه دسکتاپ انجام می‌شود. این APK با امضای Debug برای آزمایش پیش‌انتشار ساخته شده است.
