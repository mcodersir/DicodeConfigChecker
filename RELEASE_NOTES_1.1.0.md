# Dicode Config Checker v1.1.0 Complete Preview

این نسخه یک پیش‌انتشار چندسکویی کامل‌تر است. نسخه پایدار **v1.0.1 حذف نشده** و فایل‌های آن در Releases باقی می‌ماند.

## تغییرات اصلی

- خروجی مستقل برای Windows، Linux x86_64 و Android
- اعمال آیکون برنامه روی فایل EXE و پنجره ویندوز
- قرار گرفتن Xray Core، `geoip.dat` و `geosite.dat` داخل بسته‌های Windows و Linux
- رابط Android با پنج بخش داشبورد، تنظیمات، کانال‌ها، کانفیگ‌ها و پروکسی‌ها
- کانال‌های رتبه اول و دوم با سقف جداگانه
- تنظیم تعداد تلاش، حداقل موفقیت، URL تست، نام‌گذاری و نوع خروجی
- رفع هم‌پوشانی رابط Android با نوار وضعیت، وای‌فای، باتری و ناوبری سیستم
- آیکون Adaptive و Round برای Android
- ساخت و قراردادن `AndroidLibXrayLite` داخل APK
- تست واقعی VLESS، VMess، Trojan و Shadowsocks از مسیر Xray Core در Android
- مشخص شدن روش تست هر نتیجه با `xray`، `tcp-fallback` یا `telegram-tcp`
- فرایند دو مرحله‌ای دریافت کانفیگ و سپس تست بعد از قطع اتصال فعلی
- ساخت `sub.txt`، `proxy.txt`، خروجی Base64 و `report.json`
- ثبت نسخه Xray Core در `report.json` اندروید
- اشتراک‌گذاری مستقیم فایل‌های خروجی در Android
- فایل SHA-256 برای همه خروجی‌های انتشار

## فایل‌های انتشار

- `DicodeConfigChecker-v1.1.0-windows.exe`
- `DicodeConfigChecker-v1.1.0-linux-x86_64.tar.gz`
- `DicodeConfigChecker-v1.1.0-android-preview.apk`
- `DicodeConfigChecker-source-v1.1.0.zip`
- `SHA256SUMS.txt`

## وضعیت Android Preview

APK با امضای Debug برای آزمایش پیش‌انتشار ساخته می‌شود. کانفیگ‌های اصلی Xray به‌صورت واقعی از داخل هسته تست می‌شوند؛ پروکسی‌های Telegram و پروتکل‌های پشتیبانی‌نشده با روش مناسب جایگزین بررسی می‌شوند.
