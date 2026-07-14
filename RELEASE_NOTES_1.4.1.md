# Dicode Config Checker v1.4.1

رفع اختلال دسترسی به Telegram Preview در شرایطی که دامنه `t.me` روی شبکه کاربر باز نمی‌شود.

## تغییرات

- لینک کانال با هر دو فرم `t.me/username` و `telegram.me/username` پذیرفته می‌شود.
- برای هر اجرا، برنامه ابتدا preview را از `t.me` امتحان می‌کند.
- فقط در صورت خطای واقعی در `t.me`، همان کانال به‌صورت خودکار از `telegram.me` خوانده می‌شود.
- ترتیب و سازگاری فهرست فعلی کانال‌ها حفظ شده است؛ نیازی به ویرایش دستی `channels.txt` نیست.
- fallback برای نسخه‌های Windows، Linux و Android اعمال شده است.

## فایل‌های انتشار

- `DicodeConfigChecker-v1.4.1-windows-x64.exe`
- `DicodeConfigChecker-v1.4.1-linux-x86_64.tar.gz`
- `DicodeConfigChecker-v1.4.1-android.apk`
- `DicodeConfigChecker-v1.4.1-source.zip`
- `SHA256SUMS.txt`
