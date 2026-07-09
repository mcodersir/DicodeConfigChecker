# Dicode Config Checker v1.0.1

## تغییرات

- لیست کامل جدید کانال‌های رتبه دوم جایگزین شد.
- `MAIN_CHANNELS` در فایل‌های پیش‌فرض خالی شد تا لیست جدید واقعاً رتبه دوم بماند.
- گزینه مستقل «بررسی کانفیگ‌های V2Ray/Xray و ساخت sub.txt» اضافه شد.
- گزینه مستقل «بررسی پروکسی‌های تلگرام و ساخت proxy.txt» حفظ شد.
- حالت فقط پروکسی اضافه شد: کانفیگ‌ها خاموش، پروکسی‌ها روشن.
- اگر هر دو خروجی خاموش باشند، برنامه قبل از شروع هشدار می‌دهد.
- اسکریپت دیپلوی `deploy_release_v1_0_1.bat` اضافه شد.
- اسکریپت انتشار، release/tag نسخه `v1.0.0` را حذف می‌کند، سورس را push می‌کند، tag `v1.0.1` می‌سازد و دو asset منتشر می‌کند:
  - `DicodeConfigChecker-v1.0.1-windows.exe`
  - `DicodeConfigChecker-source-v1.0.1.zip`

## اجرا

برای اجرای برنامه در حالت توسعه:

```bat
run_dev.bat
```

برای ساخت EXE:

```bat
build_exe.bat
```

برای build + push + release روی GitHub:

```bat
deploy_release_v1_0_1.bat
```
