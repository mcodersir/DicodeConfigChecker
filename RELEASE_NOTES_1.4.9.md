# Dicode Config Checker v1.4.9 — Stable

## ساب اختصاصی GitHub

- از تنظیمات، یک GitHub **Classic Personal Access Token** با scope `public_repo` وارد و ذخیره کنید.
- پس از اولین تست موفق، برنامه در حساب خود کاربر یک ریپازیتوری عمومی تصادفی با پایان `DIC` می‌سازد.
- کانفیگ‌های سالم در `sub.txt` و پروکسی‌های سالم تلگرام در `proxy.txt` قرار می‌گیرند.
- در اجراهای بعدی همان دو فایل به‌صورت خودکار به‌روزرسانی می‌شوند.
- لینک‌های raw در خود برنامه نمایش داده می‌شوند، مانند:
  `https://raw.githubusercontent.com/OWNER/REPOSITORY/refs/heads/main/sub.txt`

## کیفیت تست

- اعتبارسنجی SOCKS تلگرام اکنون یک تونل SOCKS5 واقعی به یکی از DCهای تلگرام برقرار می‌کند؛ صرفِ باز بودن پورت کافی نیست.
- معیار پایداری همچنان بر پایه چند تلاش و میانهٔ تأخیر است.
- کانفیگ‌ها در حالت Xray با درخواست واقعی بررسی می‌شوند و فقط در نبود پشتیبانی Xray از TCP fallback استفاده می‌شود.

## سازگاری

- این نسخه شامل fallback پایدار `t.me` به `telegram.me` است؛ ابتدا `t.me` بررسی می‌شود و تنها در خطا مسیر جایگزین به کار می‌رود.
- قابلیت ساب اختصاصی و خروجی `proxy.txt` در نسخه‌های Windows، Linux و Android موجود است.

## فایل‌های انتشار

- `DicodeConfigChecker-v1.4.9-windows-x64.exe`
- `DicodeConfigChecker-v1.4.9-linux-x86_64.tar.gz`
- `DicodeConfigChecker-v1.4.9-android.apk`
- `DicodeConfigChecker-v1.4.9-source.zip`
- `SHA256SUMS.txt`
