<p align="center"><img src="assets/app.svg" width="88" alt="Dicode Config Checker"></p>
<h1 align="center">Dicode Config Checker 2</h1>
<p align="center">جمع‌آوری و سنجش واقعی کانفیگ‌ها با دسکتاپ C# و اپ Android</p>

## نسخه ۲ چه تفاوتی دارد؟

نسخه ۲ یک بازنویسی دسکتاپ با C# و .NET 8 است. تست کانفیگ دیگر با باز و بسته کردن یک پردازش برای هر تلاش انجام نمی‌شود. کانفیگ‌ها صفحه‌بندی می‌شوند، هر صفحه یک runtime مشترک دارد، برای هر کانفیگ یک ورودی SOCKS مستقل ساخته می‌شود و درخواست HTTP واقعی به‌صورت هم‌زمان از داخل همان مسیر عبور می‌کند.

- تست واقعی HTTP به‌جای اتکا به باز بودن پورت
- اجرای batch با حداکثر ۳۲ کانفیگ در هر پردازش
- retry جداگانه فقط برای موارد شکست‌خورده
- پشتیبانی از Core A و Core B برای پوشش پروتکل‌های متنوع
- ثبت median، کمترین تاخیر، میانگین، تعداد تلاش و تعداد موفقیت
- پردازش موازی کنترل‌شده برای جلوگیری از فشار بی‌رویه روی CPU و شبکه
- GeoFiles نسخه‌بندی‌شده و runtimeهای pin‌شده در فرایند انتشار
- رابط فارسی ساده و بازطراحی‌شده برای Windows و Android

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
| `report.json` | نتیجه کامل و قابل پردازش هر تست |

## ساخت دسکتاپ

پیش‌نیاز: [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)

```powershell
dotnet build DicodeConfigChecker.sln -c Release
dotnet run --project tests/DicodeConfigChecker.Tests -c Release
dotnet publish src/DicodeConfigChecker.Desktop -c Release -r win-x64 --self-contained true
```

runtimeها هنگام Release توسط GitHub Actions با نسخه‌های ثابت به بسته Windows اضافه می‌شوند. برای اجرای توسعه‌ای می‌توانید فایل‌های اجرایی را با نام‌های `core-a.exe` و `core-b.exe` داخل پوشه `runtimes` قرار دهید یا مسیرشان را در `DICODE_CORE_A` و `DICODE_CORE_B` تنظیم کنید.

## ساخت Android

```bash
gradle -p android :app:lintDebug :app:assembleDebug
```

کتابخانه runtime موبایل در workflow از commit ثابت ساخته و داخل APK قرار داده می‌شود. حداقل نسخه Android برابر API 26 و target برابر API 36 است.

## انتشار و کنترل کیفیت

تگ `v2.0.0` تنها زمانی به Release پایدار تبدیل می‌شود که build با warning-as-error، تست parser، Android lint، ساخت Windows و ساخت APK همگی موفق باشند. Release شامل checksum و provenance است.

## مجوز

کد برنامه تحت [MIT](LICENSE) است. runtimeها و GeoFiles همراه برنامه آثار مستقل هستند و شرایط مجوز خودشان را حفظ می‌کنند؛ جزئیات در [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) آمده است.
