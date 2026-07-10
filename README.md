<p align="center">
  <img src="assets/app.svg" width="96" alt="Dicode Config Checker">
</p>

<h1 align="center">Dicode Config Checker</h1>

<p align="center">
  ابزار ویندوزی برای جمع‌آوری، تفکیک و بررسی کانفیگ‌های عمومی و پروکسی‌های تلگرام
</p>

<p align="center">
  <a href="https://github.com/mcodersir/DicodeConfigChecker/releases/latest"><img src="https://img.shields.io/github/v/release/mcodersir/DicodeConfigChecker?style=flat-square&label=release" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/channels-242-2ea44f?style=flat-square" alt="242 channels">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/mcodersir/DicodeConfigChecker?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/mcodersir/DicodeConfigChecker/releases/latest"><strong>دانلود آخرین نسخه</strong></a>
  ·
  <a href="#مشارکت-در-فهرست-کانالها">پیشنهاد کانال</a>
  ·
  <a href="#ساخت-و-اجرا">ساخت از سورس</a>
</p>

---

## درباره پروژه

Dicode Config Checker فهرستی از کانال‌های عمومی تلگرام را بررسی می‌کند، لینک‌های کانفیگ و پروکسی را از پست‌های عمومی جمع‌آوری می‌کند و نتیجه را در خروجی‌های جداگانه تحویل می‌دهد.

برنامه برای بررسی کانفیگ‌های سازگار، در صورت دسترسی از `Xray-core` استفاده می‌کند. در موارد دیگر، تست دسترسی شبکه و TCP به‌عنوان روش جایگزین اجرا می‌شود. نتیجه نهایی بر اساس وضعیت اتصال و تاخیر مرتب می‌شود تا خروجی قابل استفاده‌تری در اختیار داشته باشید.

## امکانات

| قابلیت | توضیح |
|---|---|
| جمع‌آوری از کانال‌های عمومی | خواندن پست‌های قابل مشاهده در Telegram Preview بدون نیاز به ورود به حساب |
| فهرست داخلی کانال‌ها | شامل ۲۴۲ کانال عمومی قابل ویرایش از طریق `channels.txt` |
| خروجی جداگانه | تفکیک کانفیگ‌های V2Ray/Xray از پروکسی‌های Telegram |
| حالت فقط کانفیگ یا فقط پروکسی | هر بخش را می‌توان به‌صورت مستقل از تنظیمات فعال یا غیرفعال کرد |
| بررسی چندمرحله‌ای | تست با Xray در حالت سازگار و استفاده از TCP fallback در سایر موارد |
| مرتب‌سازی بر اساس تاخیر | چینش نتایج سالم بر اساس پینگ ثبت‌شده |
| گزارش کامل | ساخت گزارش متنی و JSON برای بررسی دقیق‌تر نتایج |
| رابط دسکتاپ | رابط گرافیکی فارسی برای اجرای مراحل جمع‌آوری و تست |

## روش کار

1. کانال‌های ثبت‌شده در `channels.txt` خوانده می‌شوند.
2. لینک‌های پشتیبانی‌شده از صفحات عمومی تلگرام استخراج می‌شوند.
3. موارد تکراری و نامعتبر حذف می‌شوند.
4. کانفیگ‌ها و پروکسی‌ها با روش مناسب بررسی می‌شوند.
5. خروجی‌های سالم و گزارش‌های تکمیلی در کنار برنامه ذخیره می‌شوند.

> برای مرحله جمع‌آوری باید دسترسی شما به صفحات عمومی تلگرام برقرار باشد. نتیجه تست‌ها نیز به وضعیت شبکه، محدودیت‌های اپراتور و در دسترس بودن سرورها وابسته است.

## حالت‌های خروجی

از بخش تنظیمات می‌توانید یکی از این حالت‌ها را انتخاب کنید:

- **فقط کانفیگ:** بررسی V2Ray/Xray روشن و بررسی پروکسی تلگرام خاموش
- **فقط پروکسی:** بررسی V2Ray/Xray خاموش و بررسی پروکسی تلگرام روشن
- **هر دو:** هر دو گزینه روشن

اگر هر دو گزینه خاموش باشند، برنامه پیش از شروع هشدار می‌دهد.

## فایل‌های خروجی

| فایل | محتوا |
|---|---|
| `sub.txt` | کانفیگ‌های سالم V2Ray/Xray |
| `sub_base64.txt` | نسخه Base64 اشتراک کانفیگ‌ها |
| `proxy.txt` | پروکسی‌های سالم Telegram MTProto/SOCKS |
| `proxy_base64.txt` | نسخه Base64 پروکسی‌ها |
| `alive_report.txt` | گزارش خوانا از کانفیگ‌های سالم |
| `proxy_report.txt` | گزارش خوانا از پروکسی‌ها |
| `report.json` | گزارش کامل و ساختاریافته |
| `all_configs_stage1.txt` | داده خام جمع‌آوری‌شده پیش از تست |

## دانلود نسخه آماده

فایل اجرایی ویندوز از بخش [Releases](https://github.com/mcodersir/DicodeConfigChecker/releases/latest) در دسترس است.

بعد از دانلود، فایل EXE را در یک پوشه با دسترسی نوشتن اجرا کنید تا خروجی‌ها در همان مسیر ذخیره شوند. Windows Defender یا آنتی‌ویروس ممکن است فایل‌های ساخته‌شده با PyInstaller را در اولین اجرا بررسی کند.

## ساخت و اجرا

### پیش‌نیازها

- Windows 10 یا Windows 11
- Python 3.10 یا جدیدتر
- اتصال اینترنت برای نصب وابستگی‌ها و دریافت اختیاری Xray-core

### اجرای نسخه توسعه

```bat
run_dev.bat
```

### ساخت فایل EXE

```bat
build_exe.bat
```

خروجی اصلی در این مسیر ساخته می‌شود:

```text
dist\DicodeConfigChecker.exe
```

نسخه نام‌گذاری‌شده برای انتشار نیز در پوشه `release` قرار می‌گیرد.

## مدیریت فهرست کانال‌ها

فهرست منابع در فایل زیر قرار دارد:

```text
channels.txt
```

هر خط باید فقط شامل یک آدرس عمومی تلگرام با این قالب باشد:

```text
t.me/channel_username
```

ترتیب خطوط حفظ می‌شود و موارد تکراری هنگام پردازش کنار گذاشته می‌شوند.

## مشارکت در فهرست کانال‌ها

در حال حاضر مسیر مشارکت عمومی پروژه روی **پیشنهاد و اصلاح کانال‌های منبع** متمرکز است.

برای پیشنهاد کانال جدید، از فرم زیر استفاده کنید:

<p align="center">
  <a href="https://github.com/mcodersir/DicodeConfigChecker/issues/new?template=channel-suggestion.yml"><img src="https://img.shields.io/badge/پیشنهاد_کانال-ثبت_Issue-2ea44f?style=for-the-badge" alt="Suggest a channel"></a>
</p>

کانال پیشنهادی باید:

- عمومی و بدون نیاز به عضویت اجباری برای مشاهده اولیه باشد؛
- به‌صورت منظم کانفیگ یا پروکسی منتشر کند؛
- در فهرست فعلی تکراری نباشد؛
- لینک مستقیم و معتبر `t.me` داشته باشد؛
- محتوای نامرتبط، فریبنده یا اسپم غالب نداشته باشد.

پس از بررسی و اضافه شدن پیشنهاد، نام حساب GitHub پیشنهاددهنده در بخش مشارکت‌کنندگان کانال ثبت می‌شود. جزئیات بیشتر در [راهنمای مشارکت](CONTRIBUTING.md) آمده است.

## سازندگان و مشارکت‌کنندگان

<table>
  <tr>
    <td align="center" width="180">
      <a href="https://github.com/mcodersir">
        <img src="https://github.com/mcodersir.png?size=120" width="88" alt="M_CODER"><br>
        <strong>M_CODER</strong>
      </a><br>
      <sub>سازنده و توسعه‌دهنده اصلی<br>طراحی محصول و رابط کاربری</sub>
    </td>
    <td align="center" width="180">
      <a href="https://github.com/farhadfwladyan">
        <img src="https://github.com/farhadfwladyan.png?size=120" width="88" alt="farhadfwladyan"><br>
        <strong>farhadfwladyan</strong>
      </a><br>
      <sub>مشارکت‌کننده فهرست کانال‌ها</sub>
    </td>
  </tr>
</table>

## نکات مهم

- منابع این پروژه کانال‌های عمومی و مستقل هستند و حضور یک کانال در فهرست به معنی تایید محتوای آن نیست.
- سالم بودن یک کانفیگ یا پروکسی دائمی نیست و ممکن است در هر لحظه تغییر کند.
- پروژه هیچ سرور، کانفیگ یا پروکسی را میزبانی یا فروش نمی‌کند.
- مسئولیت استفاده از خروجی‌ها و رعایت قوانین محل زندگی بر عهده کاربر است.

## مجوز

این پروژه تحت مجوز موجود در فایل [LICENSE](LICENSE) منتشر شده است.
