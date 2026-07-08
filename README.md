# Dicode Config Checker v1.0.0

![Dicode Config Checker](assets/app.png)

## فارسی

**Dicode Config Checker** یک ابزار دسکتاپ ویندوزی برای جمع‌آوری کانفیگ از کانال‌های عمومی تلگرام، تست واقعی‌تر با Xray-core، و ساخت خروجی‌های آماده‌ی مصرف است.

### قابلیت‌ها

- رابط کاربری دارک، مینمال و مناسب کاربر غیر برنامه‌نویس
- دریافت دو مرحله‌ای: اول جمع‌آوری با اتصال فعال، بعد تست پس از قطع اتصال
- تست کیفیت با Xray-core در حالت `auto` و `xray`
- پیش‌فیلتر TCP برای حذف سریع سرورهای مرده
- خروجی جدا برای کانفیگ‌ها و پروکسی‌های تلگرام
- ساخت `sub.txt` و `sub_base64.txt`
- ساخت `proxy.txt` و `proxy_base64.txt`
- ویرایش تعداد کانفیگ هر کانال و کانال اصلی از داخل نرم‌افزار
- ویرایش، افزودن، ایمپورت و پاکسازی لیست کانال‌ها
- امکان روشن/خاموش کردن بازنویسی نام کانفیگ بعد از `#`
- امکان تغییر متن نام کانفیگ، مثل `t.me/dicodeir-1`
- دانلود Xray-core قبل از Build و Embed شدن داخل فایل EXE نهایی

### خروجی‌ها

```text
sub.txt
sub_base64.txt
proxy.txt
proxy_base64.txt
all_configs_stage1.txt
alive_report.txt
proxy_report.txt
report.json
run_log.txt
```

### اجرای توسعه

```bat
run_dev.bat
```

### ساخت فایل EXE

```bat
build_exe.bat
```

خروجی:

```text
dist\DicodeConfigChecker.exe
```

### انتشار روی GitHub

توکن را داخل کد یا فایل ذخیره نکنید. قبل اجرا، متغیر محیطی را ست کنید:

```powershell
$env:GITHUB_TOKEN="YOUR_NEW_TOKEN"
.\publish_to_github.ps1
```

یا فایل زیر را اجرا کنید و توکن را وقتی پرسید وارد کنید:

```bat
publish_to_github.bat
```

اسکریپت انتشار این کارها را انجام می‌دهد:

1. ساخت EXE
2. ساخت ریپازیتوری `DicodeConfigChecker`
3. Push کردن سورس کد
4. ساخت تگ `v1.0.0`
5. ساخت Release
6. آپلود فایل EXE و ZIP سورس در Release

---

## English

**Dicode Config Checker** is a Windows desktop tool for collecting configuration candidates from public Telegram channels, verifying them with Xray-core based quality testing, and generating ready-to-use subscription outputs.

### Features

- Polished dark GUI for non-technical users
- Two-stage workflow: fetch first, disconnect, then test
- Xray-core based real-delay style testing in `auto` and `xray` modes
- TCP prefilter to skip clearly dead endpoints before heavier tests
- Separate outputs for V2Ray/Xray configs and Telegram MTProto/SOCKS proxies
- Generates `sub.txt` and `sub_base64.txt`
- Generates `proxy.txt` and `proxy_base64.txt`
- Edit per-channel and main-channel limits inside the app
- Add, batch-edit, import, deduplicate and save channels from the GUI
- Optional remark rewriting after `#`
- Custom remark prefix, e.g. `t.me/dicodeir-1`
- Xray-core is downloaded before build and embedded inside the final EXE

### Build

```bat
build_exe.bat
```

Output:

```text
dist\DicodeConfigChecker.exe
```

### Publish to GitHub

Do not store tokens in source code. Use an environment variable:

```powershell
$env:GITHUB_TOKEN="YOUR_NEW_TOKEN"
.\publish_to_github.ps1
```

The publisher script will create the repository, push the source, create `v1.0.0`, create a GitHub Release, and upload the Windows EXE plus source archive.

## Version

The application version is intentionally kept at `1.0.0`.

---

## Publish troubleshooting / رفع مشکل انتشار

If publishing fails with `invalid credentials`, create a new GitHub token and set it only in the current PowerShell session:

```powershell
$env:GITHUB_TOKEN="YOUR_NEW_TOKEN"
.\publish_to_github.ps1
```

اگر خطای `Could not resolve host: github.com` دیدی، مشکل از اتصال سیستم به GitHub است. پروکسی/VPN را روشن کن یا DNS را درست کن و دوباره اسکریپت را اجرا کن.

The release script does not store your token in `.git/config`; it uses an in-memory Git authorization header for push/tag operations.
