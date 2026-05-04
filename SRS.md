# پلتفرم عملیات یادگیری ماشین برای پیش‌بینی ریزش مشتری  
# سند نیازمندی‌های نرم‌افزار

**نسخه**: ۱.۱.۰  
**تاریخ**: ۱۴۰۵/۰۲/۱۲

---

## فهرست مطالب

- [فارسی](#۱-مقدمه) / [English](#1-introduction)

---

## ۱. مقدمه

### ۱.۱ هدف

هدف این سند، تعیین نیازمندی‌های عملکردی و غیرعملکردی پلتفرم عملیات یادگیری ماشین برای پیش‌بینی ریزش مشتری است. این پلتفرم به تیم‌های داده امکان می‌دهد مدل‌های یادگیری ماشین را در یک محیط تولیدی آموزش دهند، ردیابی کنند، مستقر کنند و پایش کنند.

### ۱.۲ حوزه عملکرد

این سیستم شامل موارد زیر است:

- بارگذاری و پیش‌پردازش داده‌های مشتریان
- آموزش و بهینه‌سازی فراپارامترهای مدل‌های طبقه‌بندی
- ردیابی آزمایش‌ها و مدیریت مدل با چارچوب ردیابی آزمایش
- کش ویژگی‌های پیش‌پردازش شده با استفاده از حافظه نهان توزیع‌شده
- ارائه پیش‌بینی‌های بلادرنگ از طریق واسط برنامه‌نویسی REST
- بازآموزی غیرهمزمان مدل با استفاده از صف پیام
- پیش‌بینی دسته‌جمعی (batch prediction) از طریق صف وظایف توزیع‌شده
- پشته کامل دیدپذیری (سنجه‌ها، لاگ‌ها، داشبوردها)
- استقرار کانتینری با مدیریت سرویس‌ها

### ۱.۳ تعاریف و اختصارات

| واژه                          | معنی                                              |
| ----------------------------- | ------------------------------------------------- |
| عملیات یادگیری ماشین          | عملیات مربوط به چرخه حیات یادگیری ماشین           |
| چارچوب ردیابی آزمایش          | پلتفرم متن‌باز برای ردیابی چرخه حیات یادگیری ماشین |
| چارچوب بهینه‌سازی فراپارامترها | ابزار بهینه‌سازی خودکار فراپارامترهای مدل          |
| صف وظایف توزیع‌شده             | کارگزار وظایف برای اجرای غیرهمزمان                |
| ابزار جمع‌آوری سنجه            | جعبه‌ابزار مانیتورینگ و هشدار                      |
| ابزار مصورسازی                | پلتفرم نمایش داشبوردها و نمودارها                 |
| سامانه تجمیع لاگ              | ذخیره‌سازی و جستجوی لاگ‌ها                          |
| ذخیره‌سازی سازگار با ابر       | مخزن اشیاء با واسط سازگار با سرویس‌های ابری        |
| کش ویژگی (Feature Cache)      | حافظه نهان برای ذخیره ویژگی‌های پیش‌پردازش شده      |

---

## ۲. توصیف کلی

### ۲.۱ جایگاه محصول

این پلتفرم یک سامانه خودایستا متشکل از ریزخدمات گوناگون است که با ابزار مدیریت کانتینر مدیریت می‌شوند. با فایل داده موجود یکپارچه شده و قابلیت گسترش به ذخیره‌سازی ابری را دارد.

### ۲.۲ کاربران هدف

- **دانشمندان داده**: آموزش مدل، اجرای آزمایش‌ها، بررسی نتایج در چارچوب ردیابی آزمایش.
- **مهندسان یادگیری ماشین**: استقرار مدل، پایش عملکرد، آغاز بازآموزی.
- **تیم عملیات**: مدیریت زیرساخت، بررسی داشبوردها، تنظیم هشدارها.

---

## ۳. نیازمندی‌ها

### ۳.۱ نیازمندی‌های عملکردی

#### دریافت و پیش‌پردازش داده

- سیستم باید بتواند داده‌های مشتریان را از یک فایل داده بخواند.
- سیستم باید رمزگذاری ویژگی‌ها را انجام دهد، مقادیر گمشده را مدیریت کند و داده‌ها را به مجموعه آموزش و آزمون تقسیم کند.

#### کش ویژگی (Feature Cache)

- سیستم باید ویژگی‌های پیش‌پردازش شده را بر اساس هش یکتای ورودی مشتری در حافظه نهان توزیع‌شده ذخیره کند.
- سیستم باید با استفاده از الگوریتم MD5 و بر اساس محتوای JSON داده ورودی، هش یکتا تولید کند.
- حافظه نهان باید دارای زمان انقضا (TTL) قابل تنظیم باشد که مقدار پیش‌فرض آن ۳۶۰۰ ثانیه (یک ساعت) در نظر گرفته شده است.
- در صورت وجود داده در حافظه نهان، سیستم باید مستقیماً از ویژگی‌های ذخیره شده استفاده کند و مرحله پیش‌پردازش را تکرار نکند.
- در صورت عدم دسترسی به سرویس حافظه نهان، سیستم باید به صورت降یافته (graceful degradation) عمل کرده و ویژگی‌ها را مستقیماً محاسبه کند.
- سیستم باید آمار مربوط به حافظه نهان شامل تعداد درخواست‌های موفق (hit)، تعداد درخواست‌های ناموفق (miss) و نرخ اصابت (hit rate) را از طریق نقطه‌پایانی اختصاصی در دسترس قرار دهد.
- سیستم باید قابلیت پاک کردن اجباری حافظه نهان را برای اهداف تست و رفع اشکال فراهم کند.

#### آموزش مدل و بهینه‌سازی فراپارامترها

- سیستم باید یک طبقه‌بند جنگل تصادفی را با استفاده از چارچوب بهینه‌سازی فراپارامترها آموزش دهد.
- بهینه‌سازی باید مقدار سطح زیر منحنی را روی اعتبارسنجی متقابل ۵-بخشی با حداقل ۱۵ تلاش بیشینه کند.
- فراپارامترهای بهینه‌شونده باید شامل تعداد درخت‌ها (n_estimators)، حداکثر عمق (max_depth) و حداقل نمونه برای تقسیم (min_samples_split) باشند.

#### ردیابی آزمایش‌ها و مدیریت مدل

- همه اجراهای آموزشی باید در چارچوب ردیابی آزمایش ثبت شوند: پارامترها، سنجه‌ها، مصنوعات (ستون‌های ویژگی، مدل).
- بهترین مدل باید در رجیستری مدل ثبت شود.
- پس از آموزش، آخرین نسخه مدل باید به‌طور خودکار به مرحله تولید ارتقا یابد.
- سیستم باید قابلیت مقایسه خودکار عملکرد بین نسخه‌های مختلف مدل را بر اساس معیار سطح زیر منحنی فراهم کند.
- سیستم باید بتواند بهترین مدل را بر اساس معیار سطح زیر منحنی به صورت خودکار انتخاب و بارگذاری کند.

#### واسط برنامه‌نویسی استنتاج

- سیستم باید یک واسط برنامه‌نویسی REST با مسیرهای زیر ارائه دهد:
  - دریافت سلامت: بازگرداندن سلامت سرویس و وضعیت بارگذاری مدل.
  - ارسال پیش‌بینی: دریافت یک شیء شامل ویژگی‌های مشتری و بازگرداندن پیش‌بینی ریزش و احتمال.
  - دریافت سنجه‌ها: افشای سنجه‌های ابزار جمع‌آوری سنجه شامل شمارنده درخواست‌های پیش‌بینی.
  - دریافت آمار حافظه نهان: نمایش آمار مربوط به کش ویژگی.
  - دریافت سنجه‌های تفصیلی: نمایش مقایسه نسخه‌های مدل، آمار کش و وضعیت سرویس‌های پشتیبان.
- واسط باید مدل تولیدی را در هنگام راه‌اندازی از چارچوب ردیابی آزمایش بارگذاری کند.
- واسط باید مستندات تعاملی را در مسیر مستندات در دسترس قرار دهد.
- واسط باید قبل از هر بار پیش‌پردازش، حافظه نهان را بررسی کرده و در صورت وجود، از ویژگی‌های ذخیره شده استفاده کند.
- واسط باید پس از محاسبه ویژگی‌ها، آن‌ها را در حافظه نهان با زمان انقضای معین ذخیره کند.

#### بازآموزی غیرهمزمان

- کاربران باید بتوانند با ارسال یک وظیفه به صف وظایف توزیع‌شده، بازآموزی مدل را آغاز کنند.
- وظیفه بازآموزی باید همان خط‌لوله آموزشی را اجرا کند و در صورت موفقیت، مدل تولیدی را به‌روز کند.
- وضعیت بازآموزی باید لاگ و قابل مشاهده باشد.
- سیستم باید قابلیت پیش‌بینی دسته‌جمعی (batch prediction) را از طریق صف وظایف توزیع‌شده فراهم کند.
- نتایج پیش‌بینی دسته‌جمعی باید به مدت ۲۴ ساعت در حافظه نهان توزیع‌شده ذخیره شده و با شناسه یکتا قابل بازیابی باشد.
- وظیفه اجراکننده پیش‌بینی دسته‌جمعی باید مدل و ستون‌های ویژگی را به صورت کش شده در حافظه داخلی خود نگهداری کند تا از بارگذاری مجدد مکرر جلوگیری شود.

#### ذخیره‌سازی مصنوعات مدل

- مصنوعات چارچوب ردیابی آزمایش (مدل، فایل ستون‌ها) باید در یک سطل سازگار با ابر که توسط ذخیره‌سازی سازگار با ابر فراهم می‌شود، ذخیره شوند.
- اعتبارنامه‌های ذخیره‌سازی باید از طریق متغیرهای محیطی قابل تنظیم باشند.
- متادیتای مدل (پارامترها، سنجه‌ها، تگ‌ها) باید در پایگاه داده رابطه‌ای ذخیره شود.

#### مانیتورینگ و دیدپذیری

- ابزار جمع‌آوری سنجه باید سنجه‌ها را از سرویس واسط برنامه‌نویسی جمع‌آوری کند.
- لاگ‌های برنامه (به صورت ساختاریافته با فرمت JSON) باید توسط جمع‌آورنده لاگ جمع‌آوری و در سامانه تجمیع لاگ ذخیره شوند.
- ابزار مصورسازی باید داشبوردهایی برای سنجه‌های سیستم و مدل ارائه دهد و منابع داده آن به ابزار جمع‌آوری سنجه و سامانه تجمیع لاگ متصل باشند.
- داشبوردهای ابزار مصورسازی باید پشت پروکسی معکوس در دسترس باشند.
- هر سرویس باید نام خود را به طور خودکار در تمام لاگ‌های تولید شده تزریق کند.
- سیستم باید سنجه‌های سفارشی شامل نرخ اصابت کش ویژگی، دقت مدل تولیدی و شماره نسخه مدل تولیدی را از طریق نقطه‌پایانی سنجه‌ها در دسترس قرار دهد.
- سیستم باید آمار پیش‌بینی (تعداد کل پیش‌بینی‌ها، میانگین اطمینان، نرخ ریزش) را در حافظه نهان توزیع‌شده ذخیره و به‌روزرسانی کند.

#### پروکسی معکوس و مسیریابی

- پروکسی معکوس باید درخواست‌های ورودی را این‌گونه مسیریابی کند:
  - مسیر واسط برنامه‌نویسی به سرویس واسط
  - مسیر چارچوب ردیابی آزمایش به سرویس ردیابی
  - مسیر ابزار جمع‌آوری سنجه به سرویس سنجه
  - مسیر ابزار مصورسازی به سرویس مصورسازی
- پروکسی باید سرآیندهای مناسب را تنظیم کند تا عملکرد زیرمسیرها صحیح باشد.
- پروکسی باید از وب‌سوکت برای قابلیت‌های بی‌درنگ (real-time) ابزار مصورسازی پشتیبانی کند.

### ۳.۲ نیازمندی‌های غیرعملکردی

#### کارایی

- زمان پاسخ نقطه‌پایانی استنتاج برای یک درخواست منفرد در بار معمولی باید کمتر از ۵۰۰ میلی‌ثانیه باشد.
- سیستم باید حداقل ۱۰ درخواست استنتاج هم‌زمان را بدون افت کارایی پردازش کند.
- نرخ اصابت کش ویژگی باید در بار معمولی حداقل ۳۰ درصد باشد.

#### دسترس‌پذیری

- سرویس‌های اصلی باید در محیط شبه‌تولیدی دسترس‌پذیری ۹۹ درصد داشته باشند.
- بررسی‌های سلامت باید کانتینرهای ناسالم را به‌طور خودکار راه‌اندازی مجدد کنند.

#### امنیت

- اطلاعات حساس (گذرواژه‌های پایگاه داده، کلیدهای ذخیره‌سازی) باید از طریق متغیرهای محیطی منتقل شوند، نه به‌صورت سخت‌کدشده.
- پروکسی معکوس باید در محیط تولید، ارتباط غیرامن را به ارتباط امن هدایت کند (نیازمند گواهی معتبر).
- گذرواژه‌های پیش‌فرض ابزار مصورسازی و ذخیره‌سازی باید از طریق متغیرهای محیطی قابل تغییر باشند.

#### نگهداشت‌پذیری

- سیستم باید کاملاً کانتینری باشد و با یک دستور واحد مستقر شود.
- تمام سرویس‌ها باید در یک فایل تنظیمات با مدیریت وابستگی مشخص تعریف شوند.
- پیکربندی باید از طریق یک فایل محیطی برون‌سپاری شود.

#### قابلیت حمل

- پلتفرم باید روی هر میزبان کانتینری بدون تغییر (به‌جز پیکربندی متغیرهای محیطی) اجرا شود.
- استقرار روی بستر ارکستراسیون کانتینر باید با اندکی تنظیمات امکان‌پذیر باشد.

---

## ۴. نیازمندی‌های واسط خارجی

### ۴.۱ واسط‌های کاربری

- **واسط چارچوب ردیابی آزمایش**: برای مرور آزمایش‌ها.
- **واسط ابزار مصورسازی**: برای داشبوردها.
- **واسط مستندات تعاملی**: برای تست واسط برنامه‌نویسی.
- **واسط ابزار جمع‌آوری سنجه**: برای پرس‌وجوهای سنجه.

### ۴.۲ واسط‌های سخت‌افزاری

ندارد.

### ۴.۳ واسط‌های نرم‌افزاری

- **پایگاه داده رابطه‌ای**: برای فراداده چارچوب ردیابی آزمایش.
- **حافظه نهان توزیع‌شده**: برای صف وظایف توزیع‌شده و کش ویژگی.
- **ذخیره‌سازی اشیاء سازگار با ابر**: برای مصنوعات مدل.
- **ابزار جمع‌آوری سنجه**: برای جمع‌آوری سنجه‌های عددی.
- **سامانه تجمیع لاگ**: برای ذخیره و جستجوی لاگ‌های ساختاریافته.
- **جمع‌آورنده لاگ**: برای دریافت و تبدیل لاگ‌ها از سرویس‌های مختلف.

---

## ۵. معماری سیستم

نمودار کلی تعامل سرویس‌ها در مستند اصلی ارائه شده است. معماری از الگوی ریزمخدمات پیروی می‌کند:

- پروکسی معکوس به‌عنوان پروکسی لبه
- واسط برنامه‌نویسی بدون حالت برای استنتاج با قابلیت کش ویژگی
- کارگر غیرهمزمان برای بازآموزی و پیش‌بینی دسته‌جمعی
- سرویس‌های پشتیبان (پایگاه داده، کارگزار پیام، ذخیره‌سازی اشیاء) برای نگهداری حالت
- پشته کامل دیدپذیری شامل جمع‌آوری سنجه، جمع‌آوری لاگ و مصورسازی

---

## ۶. پیش‌فرض‌ها و وابستگی‌ها

- مجموعه داده مشتریان در دسترس بوده و از طرحواره مورد انتظار پیروی می‌کند.
- شبکه‌های کانتینری اجازه کشف سرویس با نام کانتینر را می‌دهند.
- همه تصاویر کانتینر از رجیستری‌های مشخص‌شده بدون محدودیت شبکه دریافت می‌شوند.
- کاربران دانش پایه‌ای از ابزارهای کانتینر و واسط برنامه‌نویسی REST دارند.
- سرویس حافظه نهان توزیع‌شده باید پیش از راه‌اندازی سرویس واسط برنامه‌نویسی در دسترس باشد.

---

## ۷. پیوست‌ها

### پیوست الف: متغیرهای محیطی

| متغیر                       | هدف                            |
| --------------------------- | ------------------------------ |
| اطلاعات اتصال پایگاه داده   | نام، کاربر و گذرواژه           |
| اعتبارنامه‌های ذخیره‌سازی     | کلید دسترسی و عبارت مخفی       |
| آدرس سرور ردیابی            | نشانی چارچوب ردیابی آزمایش     |
| رشته اتصال کارگزار پیام     | نشانی صف وظایف توزیع‌شده        |
| گذرواژه مدیر ابزار مصورسازی | رمز ورود پیش‌فرض                |
| آینه‌های رجیستری             | تنظیمات دریافت تصاویر و بسته‌ها |

### پیوست ب: جزئیات خط‌لوله آموزش

۱. بارگذاری داده  
۲. پیش‌پردازش ویژگی‌ها (یک‌داغ‌گذاری، مدیریت مقادیر گمشده)  
۳. تقسیم داده به نسبت ۸۰ به ۲۰ با نمونه‌برداری طبقه‌بندی شده  
۴. بهینه‌سازی فراپارامترها با چارچوب بهینه‌سازی (۱۵ تلاش، اعتبارسنجی متقابل ۵-بخشی، بیشینه‌سازی سطح زیر منحنی)  
۵. آموزش مدل نهایی جنگل تصادفی  
۶. ارزیابی سنجه‌ها (صحت، دقت، بازخوانی، معیار اف، سطح زیر منحنی)  
۷. ثبت در چارچوب ردیابی آزمایش (پارامترها، سنجه‌ها، مصنوعات)  
۸. ثبت مدل و ارتقا به مرحله تولید  

### پیوست ج: جزئیات مکانیزم کش ویژگی

۱. دریافت داده ورودی مشتری در قالب JSON  
۲. تولید هش یکتا با استفاده از الگوریتم MD5 بر روی محتوای JSON مرتب‌شده  
۳. جستجو در حافظه نهان توزیع‌شده با کلید `features:{hash}`  
۴. در صورت وجود (اصابت): بازیابی ویژگی‌ها و صرفه‌جویی در زمان پیش‌پردازش  
۵. در صورت عدم وجود (خطا): محاسبه ویژگی‌ها از طریق خط‌لوله پیش‌پردازش  
۶. ذخیره ویژگی‌های محاسبه‌شده در حافظه نهان با زمان انقضای ۳۶۰۰ ثانیه  
۷. به‌روزرسانی آمار حافظه نهان (تعداد اصابت، تعداد خطا، نرخ اصابت)  
۸. در صورت عدم دسترسی به سرویس حافظه نهان، ادامه کار بدون کش

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for the MLOps Churn Prediction Platform. The platform enables data science teams to train, track, deploy, and monitor machine learning models for customer churn prediction in a production environment.

### 1.2 Scope

The system covers:

- Loading and preprocessing customer data
- Training and hyperparameter optimization of classification models
- Experiment tracking and model registry using a tracking framework
- Precomputed feature caching using distributed cache
- Serving real-time predictions via a REST API
- Asynchronous model retraining triggered by a message queue
- Batch prediction through distributed task queue
- Full observability stack (metrics, logs, dashboards)
- Containerized deployment with service orchestration

### 1.3 Definitions and Acronyms

| Term          | Meaning                                     |
| ------------- | ------------------------------------------- |
| MLOps         | Machine Learning Operations                 |
| MLflow        | Open-source platform for the ML lifecycle   |
| Optuna        | Hyperparameter optimization framework       |
| Celery        | Distributed task queue                      |
| Prometheus    | Monitoring and alerting toolkit             |
| Grafana       | Analytics and monitoring visualization      |
| Loki          | Log aggregation system                      |
| Garage        | S3-compatible object storage                |
| Feature Cache | Distributed cache for preprocessed features |

---

## 2. Overall Description

### 2.1 Product Perspective

The platform is a self-contained system composed of multiple microservices orchestrated via container management tools. It integrates with existing data sources and can be extended to cloud storage.

### 2.2 User Characteristics

- **Data Scientists**: Train models, run experiments, review results in the tracking framework.
- **ML Engineers**: Deploy models, monitor performance, trigger retraining.
- **Operations**: Manage infrastructure, review dashboards, set alerts.

---

## 3. System Features and Requirements

### 3.1 Functional Requirements

#### Data Ingestion and Preprocessing

- The system shall read customer data from a data file.
- It shall perform feature encoding, handle missing values, and split data into training and test sets.

#### Feature Cache

- The system shall store preprocessed features in a distributed cache using a unique hash derived from customer input.
- The system shall generate a unique hash using the MD5 algorithm based on sorted JSON content of input data.
- The cache shall have a configurable time-to-live (TTL) with default value of 3600 seconds (one hour).
- When data exists in cache, the system shall use cached features directly without repeating the preprocessing step.
- When the cache service is unavailable, the system shall operate in graceful degradation mode and compute features directly.
- The system shall expose cache statistics including hit count, miss count, and hit rate through a dedicated endpoint.
- The system shall provide cache invalidation capability for testing and debugging purposes.

#### Model Training and Hyperparameter Optimization

- The system shall train a Random Forest classifier using the optimization framework for hyperparameter tuning.
- The optimization shall maximize the area under the curve over 5-fold cross-validation with at least 15 trials.
- The tunable hyperparameters shall include n_estimators, max_depth, and min_samples_split.

#### Experiment Tracking and Model Management

- All training runs shall be logged to the tracking framework, recording parameters, metrics, and artifacts (feature columns, model).
- The best model shall be registered in the model registry.
- After training, the latest model version shall be automatically promoted to the production stage.
- The system shall provide automatic performance comparison between different model versions based on area under the curve.
- The system shall automatically select and load the best model based on area under the curve metric.

#### Inference API

- The system shall provide a REST API with the following endpoints:
  - Health check: Return service health and model load status.
  - Prediction: Accept a JSON object with customer features and return a churn prediction and probability.
  - Metrics: Expose monitoring metrics including the prediction requests counter.
  - Cache statistics: Display feature cache performance metrics.
  - Detailed metrics: Display model version comparison, cache stats, and backend service status.
- The API shall load the production model from the tracking framework at startup.
- The API shall include interactive documentation accessible at the documentation path.
- The API shall check the cache before each preprocessing step and use stored features when available.
- The API shall store computed features in the cache with specified time-to-live after preprocessing.

#### Asynchronous Retraining

- Users shall be able to trigger model retraining by sending a task to the distributed task queue.
- The retraining task shall execute the same training pipeline and update the production model on success.
- Retraining status shall be logged and made observable.
- The system shall provide batch prediction capability through the distributed task queue.
- Batch prediction results shall be stored in the distributed cache for 24 hours and retrievable using a unique identifier.
- The batch prediction task shall cache the model and feature columns in its internal memory to avoid repeated loading.

#### Model Artifact Storage

- Tracking framework artifacts (model, columns file) shall be stored in a cloud-compatible bucket provided by the object storage.
- Credentials for the storage shall be configurable via environment variables.
- Model metadata (parameters, metrics, tags) shall be stored in a relational database.

#### Monitoring and Observability

- The monitoring tool shall scrape metrics from the API service.
- Application logs (structured in JSON format) shall be collected by the log collector and stored in the log aggregation system.
- The visualization tool shall provide dashboards for system and model metrics, with data sources connected to the monitoring tool and log aggregation system.
- The visualization dashboards shall be accessible behind the reverse proxy.
- Each service shall automatically inject its name into all generated logs.
- The system shall expose custom metrics including feature cache hit rate, production model accuracy, and production model version through the metrics endpoint.
- The system shall store and update prediction statistics (total predictions, average confidence, churn rate) in the distributed cache.

#### Reverse Proxy and Routing

- The reverse proxy shall route incoming requests as follows:
  - API path to the API service
  - Tracking framework path to the tracking service
  - Monitoring tool path to the metrics service
  - Visualization tool path to the visualization service
- The proxy shall set appropriate headers to ensure correct sub-path operation.
- The proxy shall support WebSocket for real-time capabilities of the visualization tool.

### 3.2 Non-Functional Requirements

#### Performance

- The inference endpoint shall respond within 500ms for a single request under normal load.
- The system shall support at least 10 concurrent inference requests without degradation.
- The feature cache hit rate shall be at least 30 percent under normal load.

#### Availability

- Core services shall achieve 99 percent uptime in a production-like environment (excluding maintenance).
- Health checks shall automatically restart unhealthy containers.

#### Security

- Sensitive credentials (database passwords, storage keys) shall be passed via environment variables, not hardcoded.
- The reverse proxy shall be configured to redirect unencrypted connections to encrypted connections in production (SSL certificates required).
- Default visualization tool and storage passwords shall be changeable through environment variables.

#### Maintainability

- The system shall be fully containerized and deployable with a single command.
- All services shall be defined in a single configuration file with clear dependency management.
- Configuration shall be externalized through an environment file.

#### Portability

- The platform shall run on any container host without modification beyond environment configuration.
- Deployment on container orchestration platforms shall be feasible after minor adjustments.

---

## 4. External Interface Requirements

### 4.1 User Interfaces

- **Tracking Framework UI**: Accessible for experiment browsing.
- **Visualization Tool UI**: Accessible for dashboards.
- **Interactive Documentation UI**: Accessible for API testing.
- **Monitoring Tool UI**: Accessible for metric queries.

### 4.2 Hardware Interfaces

None.

### 4.3 Software Interfaces

- **Relational Database**: For tracking framework metadata.
- **Distributed Cache**: For task queue and feature cache.
- **Cloud-Compatible Object Storage**: For model artifacts.
- **Monitoring Tool**: For numeric metric collection.
- **Log Aggregation System**: For structured log storage and query.
- **Log Collector**: For receiving and transforming logs from various services.

---

## 5. System Architecture

A high-level diagram of service interactions is provided in the main documentation. The architecture follows a microservices pattern with:

- Reverse proxy as an edge proxy
- Stateless API for inference with feature caching capability
- Asynchronous worker for retraining and batch prediction
- Backend services (database, message broker, object storage) for state persistence
- Full observability stack including metric collection, log collection, and visualization

---

## 6. Assumptions and Dependencies

- The customer dataset is available and follows the expected schema.
- Container networks allow service discovery by container name.
- All container images are pulled from the specified registries without network restrictions.
- Users have basic knowledge of container tools and REST APIs.
- The distributed cache service must be available before the API service startup for optimal performance.

---

## 7. Appendices

### Appendix A: Environment Variables

| Variable                          | Purpose                              |
| --------------------------------- | ------------------------------------ |
| Database connection info          | Name, user, and password             |
| Storage credentials               | Access key and secret phrase         |
| Tracking server address           | Tracking framework URL               |
| Message broker connection string  | Distributed task queue address       |
| Visualization tool admin password | Default login password               |
| Registry mirrors                  | Image and package retrieval settings |

### Appendix B: Training Pipeline Detail

1. Load data
2. Preprocess features (one-hot encoding, missing value handling)
3. Split data (80/20 ratio) with stratified sampling
4. Optimize hyperparameters using optimization framework (15 trials, 5-fold cross-validation, maximize area under curve)
5. Train final Random Forest model
6. Evaluate metrics (accuracy, precision, recall, F1 score, area under curve)
7. Log to tracking framework (parameters, metrics, artifacts)
8. Register model and promote to production stage

### Appendix C: Feature Cache Mechanism Detail

1. Receive customer input data in JSON format
2. Generate unique hash using MD5 algorithm on sorted JSON content
3. Query distributed cache with key format `features:{hash}`
4. If exists (cache hit): retrieve features and skip preprocessing
5. If not exists (cache miss): compute features through preprocessing pipeline
6. Store computed features in cache with 3600 seconds time-to-live
7. Update cache statistics (hit count, miss count, hit rate)
8. If cache service is unavailable, continue operation without caching
