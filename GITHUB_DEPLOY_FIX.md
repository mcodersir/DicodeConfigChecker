# GitHub deploy fix

## مشکل قبلی
ساخت EXE موفق بود، اما انتشار مستقیم با PowerShell روی سیستم محلی در مرحله اتصال به `api.github.com` خطا می‌داد. این معمولاً به خاطر DNS، نوع پروکسی، یا این است که پورت واردشده HTTP proxy نیست و فقط SOCKS است.

## راه جدید پیشنهادی
از این نسخه به بعد لازم نیست PowerShell روی سیستم شما به `api.github.com` وصل شود.

اسکریپت جدید فقط سورس و tag را با `git push` به GitHub می‌فرستد. بعد GitHub Actions روی سرور GitHub این کارها را انجام می‌دهد:

1. نصب Python
2. نصب requirements
3. دانلود و باندل Xray-core
4. ساخت EXE ویندوزی
5. حذف Release قبلی `v1.0.0`
6. ساخت Release جدید `v1.0.1`
7. آپلود EXE و سورس ZIP

## فایل اصلی اجرا
```bat
deploy_via_github_actions_v1_0_1.bat
```

## اگر Repository هنوز ساخته نشده
اول یک ریپوی Public با این اسم بساز:

```text
DicodeConfigChecker
```

آدرس پیشنهادی:

```text
https://github.com/new?name=DicodeConfigChecker&visibility=public
```

بعد دوباره فایل زیر را اجرا کن:

```bat
deploy_via_github_actions_v1_0_1.bat
```

## فایل‌های جدید
- `.github/workflows/release-windows.yml`
- `deploy_via_github_actions.ps1`
- `deploy_via_github_actions_v1_0_1.bat`
- `diagnose_proxy_ports.bat`

## نکته مهم درباره proxy
اگر خواستی روش مستقیم قبلی را تست کنی، PowerShell برای `Invoke-RestMethod -Proxy` به HTTP/HTTPS proxy نیاز دارد. خیلی از پورت‌های لوکال مثل `10808` یا بعضی وقت‌ها `10809` فقط SOCKS هستند و با PowerShell جواب نمی‌دهند.

برای دیدن پورت‌های باز:

```bat
diagnose_proxy_ports.bat
```

باز بودن پورت به معنی HTTP بودن آن نیست.

## Fix added after `remote: invalid credentials`

The Git push path has been changed from a Bearer auth header to Basic auth with username `x-access-token` and the pasted PAT as the password. The token is passed only through `http.extraHeader` for the current git command and is not saved in `.git/config`.

The deploy script also uses `-c credential.helper=` during authenticated pushes. This prevents cached Git Credential Manager credentials from overriding the token and causing `remote: invalid credentials`.

Required token permissions:

- Classic PAT: `repo` + `workflow`
- Fine-grained PAT: repository selected, `Contents: Read and write`, `Workflows: Read and write`

