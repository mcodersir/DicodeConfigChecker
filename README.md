<p align="center"><img src="assets/app.svg" width="88" alt="Dicode Config Checker"></p>
<h1 align="center">Dicode Config Checker 2</h1>
<p align="center">جمع‌آوری و سنجش واقعی کانفیگ‌ها با دسکتاپ C# و اپ Android</p>

## نسخه ۲ چه تفاوتی دارد؟

نسخه ۲ یک بازنویسی کامل دسکتاپ با C# و .NET 8 است. موتور تست واقعی با رویکرد **تخت‌شده (flat-batch)** طراحی شده: یک پردازش هسته برای تمام کانفیگ‌ها باز می‌شود و تست‌ها به‌صورت هم‌زمان و موازی انجام می‌شوند.

- **تست واقعی HTTP** به‌جای اتکا به باز بودن پورت
- **تخت‌شده**: یک runtime مشترک برای تمام کانفیگ‌های هر نوع هسته — بدون راه‌اندازی مکرر پردازش
- **Happy Eyeballs**: اتصال IPv4+IPv6 به‌صورت هم‌زمان برای سریع‌تر شدن HTTP
- **Sniffing فعال** در تنظیمات Xray و sing-box برای مسیریابی دقیق‌تر
- **retry جداگانه** فقط برای موارد شکست‌خورده
- پشتیبانی از Core A و Core B برای پوشش پروتکل‌های متنوع
- ثبت median، کمترین تأخیر، میانگین، تعداد تلاش و تعداد موفقیت
- پردازش موازی کنترل‌شده (حداکثر ۳۲ تست هم‌زمان)
- GeoFiles نسخه‌بندی‌شده و runtimeهای pin‌شده در فرایند انتشار
- رابط فارسی مینیمال و بازطراحی‌شده برای Windows و Android

## پروتکل‌ها

تست واقعی برای VLESS، VMess، Trojan، Shadowsocks، Hysteria 2 و TUIC طراحی شده است. پروکسی‌های Telegram با تست اتصال TCP مستقل سنجیده می‌شوند و در گزارش با تست HTTP واقعی اشتباه گرفته نمی‌شوند.

## خروجی‌ها

خروجی‌ها در پوشه `Documents/DicodeConfigChecker` نوشته می‌شوند:

| فایل | محتوا |
|---|---|
| `sub.txt` | کانفیگ‌های سالم، مرتب‌شده بر اساس median |
| `sub_base64.txt` | اشتراک Base64 کانفیگ‌های سالم |
| `proxy.txt` | پروکسی‌های سالم Telegram |
| `proxy_base64.txt` | اشتراک Base64 پروکسی‌ها |
| `report.json` | نتیجهٔ کامل و قابل پردازش هر تست |

## ساخت دسکتاپ

پیش‌نیاز: [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)

```powershell
dotnet build DicodeConfigChecker.sln -c Release
dotnet run --project tests/DicodeConfigChecker.Tests -c Release
dotnet publish src/DicodeConfigChecker.Desktop -c Release -r win-x64 --self-contained true
```

بسته‌های رسمی برای `win-x64`، `linux-x64`، `osx-x64` و `osx-arm64` ساخته می‌شوند و runtimeهای نسخه‌ثابت و GeoFiles داخل هر بسته قرار دارند. فونت وزیرمتن نیز همراه بسته‌ها ارائه می‌شود. برای اجرای توسعه‌ای می‌توانید فایل‌های اجرایی را با نام‌های `core-a` و `core-b` (در ویندوز با پسوند `.exe`) داخل پوشه `runtimes` قرار دهید یا مسیرشان را در `DICODE_CORE_A` و `DICODE_CORE_B` تنظیم کنید.

## ساخت Android

```bash
gradle -p android :app:lintDebug :app:assembleDebug
```

کتابخانه runtime موبایل در workflow از commit ثابت ساخته و داخل APK قرار داده می‌شود. حداقل نسخه Android برابر API 26 و target برابر API 36 است.

## انتشار و کنترل کیفیت

تگ `v2.0.0` تنها زمانی به Release پایدار تبدیل می‌شود که build با warning-as-error، تست parser، Android lint، ساخت Windows و ساخت APK همگی موفق باشند. Release شامل checksum و provenance است.

## مجوز

کد برنامه تحت [MIT](LICENSE) است. runtimeها و GeoFiles همراه برنامه آثار مستقل هستند و شرایط مجوز خودشان را حفظ می‌کنند؛ جزئیات در [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) آمده است.
