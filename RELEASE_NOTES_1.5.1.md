# Dicode Config Checker v1.5.1

## رفع خطای شروع برنامه در Windows و Linux

- فایل‌های قابل‌نوشتن برنامه دیگر کنار فایل اجرایی ذخیره نمی‌شوند.
- مسیر استاندارد دادهٔ کاربر در Windows، Linux و macOS استفاده می‌شود و پوشه‌های لازم پیش از نوشتن ساخته می‌شوند.
- تنظیمات و فایل کانال نسخه‌های portable قبلی، در صورت وجود، بدون بازنویسی فایل جدید مهاجرت می‌شوند.
- متغیر `DICODE_DATA_DIR` برای تعیین مسیر سفارشی داده پشتیبانی می‌شود.

## نسخه macOS

- خروجی مستقل برای Apple Silicon (`arm64`) و Macهای Intel (`x86_64`) اضافه شد.
- برنامه به‌صورت `.app` ساخته، ad-hoc sign و در فایل ZIP منتشر می‌شود.
- Xray-core متناسب با معماری هر runner در بسته قرار می‌گیرد.

## انتشار مطمئن ساب GitHub

- `sub.txt` و `proxy.txt` اکنون در یک commit اتمیک منتشر می‌شوند؛ انتشار نیمه‌کارهٔ فقط یکی از فایل‌ها حذف شده است.
- شاخهٔ پیش‌فرض واقعی ریپازیتوری استفاده می‌شود و محدودیتی به نام `main` وجود ندارد.
- پس از commit، محتوای هر دو فایل از GitHub خوانده و دقیقاً راستی‌آزمایی می‌شود.
- آماده‌شدن شاخهٔ ریپازیتوری تازه‌ساخته‌شده با retry کنترل‌شده مدیریت می‌شود.
- خطاهای موقت DNS، TLS، rate limit و خطاهای 5xx با backoff دوباره امتحان می‌شوند.

## رابط فارسی و فونت

- جهت سراسری رابط دسکتاپ و Android به RTL تغییر کرد.
- فونت رسمی Vazirmatn از commit ثابت پروژهٔ اصلی دریافت می‌شود و پیش از build با Git blob hash بررسی می‌شود.
- فونت در Windows، Linux، macOS و Android داخل بسته قرار می‌گیرد و در سطح application/Material typography اعمال می‌شود.

## سرعت و پایداری

- راه‌اندازی برنامه دیگر به قابل‌نوشتن‌بودن پوشهٔ executable وابسته نیست و از failure/retry غیرضروری در شروع جلوگیری می‌کند.
- آماده‌سازی و انتشار ساب به یک commit هماهنگ تبدیل شده و تعداد حالت‌های خطای رقابتی کاهش یافته است.
- build و تست برای هر چهار پلتفرم در یک workflow واحد انجام می‌شود و release فقط پس از موفقیت همهٔ jobها ساخته می‌شود.

## فایل‌های انتشار

- `DicodeConfigChecker-v1.5.1-windows-x64.exe`
- `DicodeConfigChecker-v1.5.1-linux-x86_64.tar.gz`
- `DicodeConfigChecker-v1.5.1-macos-arm64.zip`
- `DicodeConfigChecker-v1.5.1-macos-x86_64.zip`
- `DicodeConfigChecker-v1.5.1-android.apk`
- `DicodeConfigChecker-v1.5.1-source.zip`
- `SHA256SUMS.txt`
