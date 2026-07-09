# Dicode Config Checker v1.0.1

ابزار دسکتاپ ویندوز برای جمع‌آوری کانفیگ از کانال‌های عمومی تلگرام، تست کیفیت با Xray-core یا TCP fallback و ساخت خروجی‌های جداگانه `sub.txt` و `proxy.txt`.

## تغییرات اصلی نسخه 1.0.1

- لیست جدید کانال‌های رتبه دوم جایگزین شد: 202 کانال یکتا.
- گزینه مستقل برای ساخت خروجی کانفیگ‌ها اضافه شد.
- حالت فقط پروکسی اضافه شد.
- اسکریپت build + deploy + release برای GitHub اضافه شد.
- اسکریپت release نسخه قبلی `v1.0.0` و tag آن را قبل از انتشار `v1.0.1` حذف می‌کند.

## حالت‌های خروجی

از صفحه تنظیمات:

- فقط کانفیگ: `بررسی کانفیگ‌های V2Ray/Xray` روشن، `بررسی پروکسی‌های تلگرام` خاموش.
- فقط پروکسی: `بررسی کانفیگ‌های V2Ray/Xray` خاموش، `بررسی پروکسی‌های تلگرام` روشن.
- هر دو: هر دو گزینه روشن.

اگر هر دو گزینه خاموش باشند، برنامه شروع نمی‌شود و هشدار می‌دهد.

## اجرای تستی

```bat
run_dev.bat
```

## ساخت EXE

```bat
build_exe.bat
```

خروجی‌ها:

```text
dist\DicodeConfigChecker.exe
release\DicodeConfigChecker-v1.0.1-windows.exe
```

## دیپلوی و انتشار روی GitHub

روی ویندوز این فایل را اجرا کن:

```bat
deploy_release_v1_0_1.bat
```

پیش‌نیازها:

- Python 3.10+
- Git نصب‌شده و داخل PATH
- GitHub token با دسترسی repo، یا متغیر محیطی `GITHUB_TOKEN`

پیش‌فرض ریپو داخل اسکریپت:

```text
mcodersir/DicodeConfigChecker
```

اگر ریپو فرق دارد، `publish_to_github.ps1` را باز کن و مقدارهای `Owner` و `RepoName` را تغییر بده.

## فایل‌های خروجی برنامه

- `sub.txt`: کانفیگ‌های سالم V2Ray/Xray
- `sub_base64.txt`: subscription base64
- `proxy.txt`: پروکسی‌های سالم تلگرام
- `proxy_base64.txt`: پروکسی‌های base64
- `alive_report.txt`: گزارش کانفیگ‌ها
- `proxy_report.txt`: گزارش پروکسی‌ها
- `report.json`: گزارش کامل ماشینی


## GitHub deploy if `api.github.com` fails

If deployment fails with `The remote name could not be resolved: 'api.github.com'`, the EXE has usually been built already and only GitHub publishing failed.

Use:

```bat
deploy_release_v1_0_1_with_proxy.bat
```

Enter an HTTP proxy such as `http://127.0.0.1:7890` or `http://127.0.0.1:10809`.

If `release\DicodeConfigChecker-v1.0.1-windows.exe` already exists, use:

```bat
publish_release_only_v1_0_1_with_proxy.bat
```

For diagnosis:

```bat
diagnose_github_connection.bat
```


## Deploy v1.0.1 without local GitHub API

If PowerShell cannot connect to `api.github.com`, use the GitHub Actions deploy path instead of the direct REST deploy path:

```bat
deploy_via_github_actions_v1_0_1.bat
```

This script only pushes the source and `v1.0.1` tag. GitHub Actions then builds the Windows EXE and creates the release on GitHub servers.

Direct local deploy is still available through:

```bat
deploy_release_v1_0_1_with_proxy.bat
```

For proxy diagnostics:

```bat
diagnose_proxy_ports.bat
```

## رفع خطای `remote: invalid credentials`

در نسخه فیکس‌شده، اسکریپت `deploy_via_github_actions.ps1` دیگر از `Bearer` برای `git push` استفاده نمی‌کند. توکن به شکل درستِ HTTPS Git یعنی Basic Auth در حافظه ارسال می‌شود و Credential Manager ویندوز برای همان دستور غیرفعال می‌شود تا اکانت/توکن قدیمی دخالت نکند.

توکن کلاسیک GitHub باید این scopeها را داشته باشد:

- `repo`
- `workflow`

بعد فقط این فایل را اجرا کن:

```bat
deploy_via_github_actions_v1_0_1.bat
```



### Tag push fix

If the deploy stops at `error: tag 'v1.0.1' not found`, use this package and run:

```bat
deploy_via_github_actions_v1_0_1.bat
```

The script now creates or replaces the tag safely with `git tag -f -a` and pushes `refs/tags/v1.0.1 --force`.
