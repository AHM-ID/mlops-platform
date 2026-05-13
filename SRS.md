# پلتفرم عملیات یادگیری ماشین برای پیش‌بینی ریزش مشتری  
# سند نیازمندی‌های نرم‌افزار

**نسخه**: ۱.۲.۰  
**تاریخ**: ۱۴۰۵/۰۲/۱۲

---

## فهرست مطالب

- [فارسی](#۱-مقدمه) / [English](#1-introduction)

---

### ۱. مقدمه
#### ۱.۱ هدف
هدف این سند، تعیین نیازمندی‌های عملکردی و غیرعملکردی **پلتفرم عملیات یادگیری ماشین (MLOps) برای پیش‌بینی ریزش مشتری** است. این پلتفرم به تیم‌های داده و مهندسان ML امکان می‌دهد مدل‌ها را در محیطی تولیدی آموزش دهند، ردیابی کنند، مستقر کنند، پایش نمایند و بازآموزی خودکار/دستی را مدیریت کنند. تمام نیازمندی‌ها دقیقاً منطبق بر پیاده‌سازی فعلی کدنویسی‌شده بازنگری شده‌اند.

#### ۱.۲ حوزه عملکرد
سیستم شامل زیرسیستم‌های زیر است:
- بارگذاری، اعتبارسنجی و پیش‌پردازش داده‌های مشتریان با پشتیبانی از یک‌داغ‌گذاری و مدیریت مقادیر گمشده
- آموزش و بهینه‌سازی فراپارامترهای مدل طبقه‌بند جنگل تصادفی با چارچوب Optuna
- ردیابی آزمایش‌ها، ثبت مصنوعات و مدیریت رجیستری مدل با MLflow
- کش توزیع‌شده ویژگی‌ها (Redis) با هش یکتا، انقضای پویا و حالت کاهش‌یافته (Graceful Degradation)
- ارائه پیش‌بینی‌های بلادرنگ (تکی) و دسته‌جمعی (Batch) از طریق واسط RESTful
- صف بازآموزی هوشمند: ذخیره خودکار پیش‌بینی‌ها در Redis، اولویت‌دهی به داده‌های جدید و مقایسه عملکرد قبل از ارتقا
- بازآموزی غیرهمزمان و پیش‌بینی دسته‌جمعی با کارگر Celery
- پشته کامل دیدپذیری (Prometheus، Grafana، Loki، Fluent-bit) با لاگ‌گیری ساختاریافته غیرهمزمان
- استقرار کانتینری با مدیریت وابستگی، پروکسی معکوس Nginx و پشتیبانی همزمان از Docker/Podman

#### ۱.۳ تعاریف و اختصارات
| واژه                     | معنی                                                         |
| ------------------------ | ------------------------------------------------------------ |
| MLOps                    | عملیات چرخه حیات یادگیری ماشین                               |
| MLflow                   | پلتفرم متن‌باز ردیابی آزمایش، رجیستری مدل و ذخیره‌سازی مصنوعات |
| Optuna                   | چارچوب بهینه‌سازی خودکار فراپارامترها با الگوریتم TPE Sampler |
| Celery                   | کارگزار وظایف توزیع‌شده برای اجرای غیرهمزمان                  |
| Redis                    | حافظه نهان توزیع‌شده و صف پیام (Broker)                       |
| Prometheus               | ابزار جمع‌آوری و پرس‌وجوی سنجه‌های سری زمانی                    |
| Grafana                  | پلتفرم مصورسازی داشبوردها و لاگ‌ها                            |
| Loki                     | سامانه تجمیع و جستجوی لاگ‌های ساختاریافته                     |
| Fluent-bit               | جمع‌آورنده سبک لاگ با ارسال غیرهمزمان HTTP                    |
| Garage                   | ذخیره‌سازی اشیاء سازگار با S3 برای مصنوعات مدل                |
| کش ویژگی (Feature Cache) | مکانیزم ذخیره‌سازی پیش‌پردازش شده بر پایه هش MD5               |

---

### ۲. توصیف کلی
#### ۲.۱ جایگاه محصول
این پلتفرم یک سامانه خودایستا مبتنی بر ریزسرویس‌ها است که با Docker Compose / Podman Compose مدیریت می‌شود. داده‌های اولیه از فایل `churn.csv` بارگذاری شده و قابلیت توسعه به منابع داده خارجی یا جریان‌های بلادرنگ را دارد. تمام پیکربندی‌ها برون‌سپاری شده و سیستم برای اجرا در هر میزبان کانتینری بهینه‌سازی شده است.

#### ۲.۲ کاربران هدف
- **دانشمندان داده:** آموزش مدل، تعریف آزمایش‌ها، بررسی سنجه‌ها و مقایسه نسخه‌ها در MLflow
- **مهندسان ML:** استقرار مدل، مدیریت نسخه‌ها از طریق API، پایش عملکرد و شروع بازآموزی
- **تیم عملیات (DevOps):** مدیریت زیرساخت، بررسی داشبوردهای Grafana، تنظیم هشدارها و نگهداری لاگ‌ها در Loki
- **سیستم‌های خارجی:** از طریق API استاندارد REST برای دریافت پیش‌بینی یا ارسال داده‌های آموزشی

---

### ۳. نیازمندی‌ها
#### ۳.۱ نیازمندی‌های عملکردی
**دریافت و پیش‌پردازش داده**
- سیستم باید داده‌ها را از `data/churn.csv` بارگذاری کند.
- پیش‌پردازش شامل تبدیل عددی `TotalCharges`، حذف سطردارای مقادیر گمشده، یک‌داغ‌گذاری متغیرهای دسته‌ای و نگاشت `Churn` به `{Yes:1, No:0}` است.
- داده‌ها با نسبت ۸۰/۲۰ و نمونه‌برداری طبقه‌بندی‌شده (`stratify=y`) به مجموعه آموزش و آزمون تقسیم می‌شوند.

**کش ویژگی (Feature Cache)**
- سیستم باید ویژگی‌های پیش‌پردازش شده را در Redis با کلید `features:{md5_hash}` ذخیره کند. هش بر اساس محتوای JSON مرتب‌شده محاسبه می‌شود.
- زمان انقضا (TTL) پیش‌فرض ۳۶۰۰ ثانیه است و قابل پیکربندی می‌باشد.
- در صورت وجود داده در کش، مرحله پیش‌پردازش دور زده می‌شود (Cache Hit).
- در صورت عدم دسترسی به Redis، سیستم به حالت کاهش‌یافته (Graceful Degradation) رفته و پیش‌پردازش را محلی انجام می‌دهد.
- آمار کش (تعداد Hit، Miss، نرخ Hit و کل Writes) از طریق نقطه‌پایان `/api/monitoring/cache/stats` قابل بازیابی است.
- قابلیت پاک‌سازی اجباری کش از طریق `DELETE /api/monitoring/cache` فراهم شده است.

**آموزش مدل و بهینه‌سازی فراپارامترها**
- سیستم باید یک طبقه‌بند `RandomForestClassifier` را با Optuna آموزش دهد.
- بهینه‌سازی با ۱۵ تلاش، اعتبارسنجی متقابل ۵-بخشی و معیار بیشینه‌سازی `roc_auc` انجام می‌شود.
- فراپارامترهای جستجو: `n_estimators` (50-200)، `max_depth` (3-10)، `min_samples_split` (2-8).
- **ویژگی جدید:** خط‌لوله `train_from_redis.py` ابتدا سعی می‌کند داده‌ها را از صف بازآموزی Redis بارگذاری کند. در صورت خالی بودن، به CSV باز می‌گردد (Fallback).
- قبل از ارتقا به Production، سیستم به‌صورت خودکار معیارهای نسخه جدید را با نسخه فعال مقایسه می‌کند (`auc`, `accuracy`, `f1`). در صورت برتری یا برابری، ارتقا انجام می‌شود؛ در غیر این‌صورت نسخه بایگانی می‌شود.

**ردیابی آزمایش‌ها و مدیریت مدل**
- تمام اجراها در MLflow ثبت می‌شوند: پارامترها، سنجه‌ها، و مصنوعات (`model.pkl`, `columns.pkl`).
- بهترین مدل در رجیستری `churn_model` ثبت و پس از آموزش موفق به مرحله `Production` ارتقا می‌یابد.
- API مدیریت مدل (`/api/models/*`) امکان دریافت نسخه فعال، لیست همه نسخه‌ها، مقایسه عملکرد و استقرار دستی (`/deploy`) را فراهم می‌کند.

**واسط برنامه‌نویسی استنتاج (FastAPI)**
- نقاط پایان اصلی:
  - `POST /api/predictions/single`: پیش‌بینی تکی با بازگرداندن `prediction`, `probability`, `confidence`, `model_version`.
  - `POST /api/predictions/batch`: ارسال دسته‌جمعی (تا ۱۰,۰۰۰ رکورد) و بازگرداندن `batch_id`.
  - `GET /api/batch/{batch_id}/status`: بررسی وضعیت پردازش.
  - `GET /api/batch/{batch_id}/results`: دریافت نتایج و خلاصه آماری.
  - `POST /api/collect-training-data`: ذخیره دستی داده‌های آموزشی برچسب‌دار.
  - `GET /api/health`: بررسی سلامت سرویس و اتصالات.
  - `GET /api/monitoring/prediction-stats`: آمار بلادرنگ پیش‌بینی‌ها از Redis.
  - `GET /api/docs`: مستندات تعاملی Swagger/OpenAPI.
- واسط باید در راه‌اندازی، مدل Production را از MLflow بارگذاری کند.
- قبل از هر پیش‌بینی، کش بررسی می‌شود. پس از محاسبه، ویژگی‌ها در Redis ذخیره می‌شوند.
- **ویژگی جدید:** هر پیش‌بینی موفق به‌صورت خودکار در صف بازآموزی (`RetrainQueueManager`) ثبت می‌شود تا برای آموزش‌های آتی استفاده گردد.

**بازآموزی غیرهمزمان و پیش‌بینی دسته‌جمعی**
- بازآموزی از طریق `POST /api/retrain` به Celery ارسال می‌شود. وضعیت از `/api/retrain/{task_id}/status` قابل پیگیری است.
- وظیفه بازآموزی خط‌لوله کامل را اجرا کرده، مقایسه می‌کند و در صورت موفقیت، صف آموزشی Redis را پاک می‌کند.
- پیش‌بینی دسته‌جمعی در کارگر Celery اجرا می‌شود. مدل و ستون‌ها در حافظه کارگر کش می‌شوند تا از بارگذاری مجدد جلوگیری شود.
- نتایج پیش‌بینی دسته‌جمعی به مدت ۲۴ ساعت (۸۶۴۰۰ ثانیه) در Redis ذخیره و با `batch_id` قابل بازیابی است.

**ذخیره‌سازی مصنوعات مدل**
- مصنوعات (مدل، فایل ستون‌ها، نمودارها) در سطل `mlflow` ذخیره‌سازی Garage (S3-compatible) ذخیره می‌شوند.
- فراداده‌ها (پارامترها، سنجه‌ها، تگ‌ها، اطلاعات اجرا) در PostgreSQL نگهداری می‌شوند.
- اعتبارنامه‌ها صرفاً از طریق متغیرهای محیطی (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) تزریق می‌شوند.

**مانیتورینگ و دیدپذیری**
- Prometheus سنجه‌های API (`api_requests_total`, `api_request_duration_seconds`) و فرآیند پایتون را هر ۱۵ ثانیه می‌رباید.
- لاگ‌ها به فرمت ساختاریافته JSON تولید شده و از طریق هندلر غیرهمزمان HTTP به Fluent-bit ارسال می‌شوند. Fluent-bit آن‌ها را به Loki فوروارد می‌کند.
- Grafana با اتصال به Prometheus و Loki، داشبوردهای عملکردی، سنجه‌های سیستم و کاوشگر لاگ را ارائه می‌دهد.
- نقطه‌پایان `/api/monitoring/health/system` وضعیت سلامت سیستم (CPU، RAM، Disk، اتصالات) را گزارش می‌کند.
- هر سرویس نام خود را به‌طور خودکار در تمام لاگ‌ها تزریق می‌کند (`LoggerAdapter`).

**پروکسی معکوس و مسیریابی**
- Nginx درخواست‌ها را به مسیرهای زیر هدایت می‌کند: `/api/*` → API، `/mlflow/*` → MLflow، `/prometheus/*` → Prometheus، `/grafana/*` → Grafana.
- پشتیبانی از WebSocket و هدرهای `X-Real-IP`، `X-Forwarded-For` برای عملیات صحیح زیرمسیرها.
- قابلیت هدایت HTTP به HTTPS در محیط تولید (قابل پیکربندی).

#### ۳.۲ نیازمندی‌های غیرعملکردی
**کارایی**
- زمان پاسخ نقطه‌پایان پیش‌بینی تکی در بار معمولی باید کمتر از ۵۰۰ میلی‌ثانیه باشد.
- سیستم باید حداقل ۱۰ درخواست هم‌زمان را بدون افت محسوس پردازش کند.
- نرخ اصابت کش ویژگی در بار معمولی باید ≥ ۳۰٪ باشد.

**دسترس‌پذیری**
- سرویس‌های اصلی باید دسترس‌پذیری ۹۹٪ در محیط شبه‌تولیدی داشته باشند.
- Healthcheckها (`pg_isready`, `redis-cli ping`, `curl /health`) کانتینرهای ناسالم را به‌طور خودکار راه‌اندازی مجدد می‌کنند.

**امنیت**
- تمام اطلاعات حساس (گذرواژه‌ها، کلیدهای S3) باید از طریق `.env` منتقل شوند. هیچ‌کدام نباید در کد سخت‌کد شوند.
- پروکسی معکوس باید در تولید، ترافیک غیررمزنگاری شده را به TLS هدایت کند.
- گذرواژه‌های پیش‌فرض Grafana و Garage باید از طریق متغیرهای محیطی قابل تغییر باشند.

**نگهداشت‌پذیری**
- سیستم باید کاملاً کانتینری باشد و با یک دستور (`make up`) مستقر شود.
- فایل `docker-compose.yml` و `Makefile` مدیریت وابستگی، ترتیب شروع و پلتفرم‌های Docker/Podman را یکپارچه می‌کنند.
- پیکربندی کاملاً برون‌سپاری شده از طریق `.env.example` و `.env`.

**قابلیت حمل**
- پلتفرم باید روی هر میزبان لینوکس/ویندوز دارای کانتینر اجرا شود.
- استقرار روی ارکستراتورها (Kubernetes، Swarm) با حداقل تغییر در فایل‌های پیکربندی امکان‌پذیر است.

---

### ۴. نیازمندی‌های واسط خارجی
#### ۴.۱ واسط‌های کاربری
- **MLflow UI:** مرور آزمایش‌ها، رجیستری مدل و مصنوعات.
- **Grafana UI:** داشبوردهای سنجه‌ها و کاوش لاگ‌ها.
- **Swagger UI (`/api/docs`):** تست تعاملی API و مشاهده اسکیمای OpenAPI.
- **Prometheus UI:** پرس‌وجوی سنجه‌های سری زمانی و وضعیت هدف‌ها.

#### ۴.۲ واسط‌های سخت‌افزاری
- ندارد (کاملاً مجازی‌شده و مستقل از سخت‌افزار).

#### ۴.۳ واسط‌های نرم‌افزاری
| کامپوننت    | پروتکل/پورت | نقش                                            |
| ----------- | ----------- | ---------------------------------------------- |
| PostgreSQL  | TCP/5432    | ذخیره فراداده MLflow                           |
| Redis       | TCP/6379    | صف Celery، کش ویژگی، آمار پیش‌بینی، صف بازآموزی |
| Garage (S3) | TCP/3900    | ذخیره‌سازی مصنوعات مدل و فایل‌های ردیابی         |
| Prometheus  | TCP/9090    | جمع‌آوری و پرس‌وجوی سنجه‌ها                       |
| Loki        | TCP/3100    | ذخیره‌سازی و ایندکس لاگ‌ها                       |
| Fluent-bit  | TCP/8888    | دریافت لاگ‌های JSON و فوروارد به Loki           |
| Nginx       | TCP/80      | پروکسی لبه و مسیریابی درخواست‌ها                |

---

### ۵. معماری سیستم
معماری از الگوی ریزسرویس‌های کانتینری پیروی می‌کند:
1. **لایه لبه (Edge):** Nginx به‌عنوان پروکسی معکوس، مسیریابی مبتنی بر مسیر و پشتیبانی WebSocket.
2. **سرویس استنتاج (Stateless API):** FastAPI برای پیش‌بینی بلادرنگ، مدیریت کش ویژگی، ثبت خودکار داده‌های آموزشی و انتشار سنجه‌های Prometheus.
3. **کارگر غیرهمزمان (Celery Worker):** اجرای بازآموزی و پیش‌بینی دسته‌جمعی با کش داخلی مدل و ستون‌ها برای کاهش تأخیر.
4. **سرویس‌های پشتیبان (Stateful):** PostgreSQL، Redis، Garage و MLflow برای نگهداری حالت، فراداده، صف‌ها و مصنوعات.
5. **پشته دیدپذیری:** Fluent-bit (جمع‌آوری) → Loki (ذخیره) + Prometheus (سنجه) → Grafana (مصورسازی).
6. **ابزارهای راه‌اندازی:** `Makefile` برای مدیریت چرخه حیات، `garage-setup.sh` برای مقداردهی اولیه خودکار S3.

---

### ۶. پیش‌فرض‌ها و وابستگی‌ها
- مجموعه داده `churn.csv` در مسیر `./data/` موجود و از طرحواره مورد انتظار پیروی می‌کند.
- شبکه‌های کانتینری امکان کشف سرویس با نام کانتینر را فراهم می‌کنند.
- تصاویر کانتینر از رجیستری‌های پیکربندی‌شده (`DOCKER_REGISTRY`, `PIP_INDEX_URL`) دریافت می‌شوند.
- کاربران با مفاهیم کانتینر، REST API و مدیریت متغیرهای محیطی آشنایی پایه دارند.
- سرویس Redis و Garage باید پیش از راه‌اندازی کامل API و Worker در دسترس باشند (مدیریت شده توسط `depends_on` و healthcheckها).

---

### ۷. پیوست‌ها
#### پیوست الف: متغیرهای محیطی کلیدی
| متغیر                                                  | هدف                         | مقدار پیش‌فرض/نمونه                  |
| ------------------------------------------------------ | --------------------------- | ----------------------------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`    | احراز هویت دیتابیس          | `mlops`, `admin`, `admin`           |
| `MLFLOW_S3_ENDPOINT_URL`                               | نشانی Garage S3             | `http://garage:3900`                |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`           | اعتبارنامه‌های شیء‌ذخیره      | تولید خودکار توسط `garage-setup.sh` |
| `MLFLOW_TRACKING_URI`                                  | نشانی سرور ردیابی           | `http://mlflow:5000`                |
| `REDIS_URL`                                            | نشانی صف و کش               | `redis://redis:6379/0`              |
| `GRAFANA_ADMIN_PASSWORD`                               | رمز ورود داشبورد            | قابل تغییر در `.env`                |
| `DOCKER_REGISTRY`, `PIP_INDEX_URL`, `PIP_TRUSTED_HOST` | آینه‌های دریافت تصویر و بسته | تنظیم شده برای شبکه داخلی/خارجی     |

#### پیوست ب: جزئیات خط‌لوله آموزش
1. بارگذاری داده از Redis (صف بازآموزی) یا بازگشت به `churn.csv` در صورت خالی بودن صف.
2. پیش‌پردازش ویژگی‌ها (یک‌داغ‌گذاری، مدیریت مقادیر گمشده، نگاشت هدف).
3. تقسیم داده به نسبت ۸۰ به ۲۰ با نمونه‌برداری طبقه‌بندی‌شده.
4. بهینه‌سازی فراپارامترها با Optuna (۱۵ تلاش، اعتبارسنجی متقابل ۵-بخشی، بیشینه‌سازی ROC-AUC).
5. آموزش مدل نهایی جنگل تصادفی با بهترین پارامترها.
6. ارزیابی سنجه‌ها (صحت، دقت، بازخوانی، F1، سطح زیر منحنی).
7. ثبت در MLflow (پارامترها، سنجه‌ها، مصنوعات شامل مدل و `columns.pkl`).
8. **مقایسه خودکار** با نسخه Production فعلی بر اساس معیارهای کلیدی.
9. ثبت مدل در رجیستری و ارتقا به مرحله Production در صورت برتری/برابری.
10. پاک‌سازی خودکار صف بازآموزی پس از موفقیت.

#### پیوست ج: جزئیات مکانیزم کش ویژگی
1. دریافت داده ورودی مشتری در قالب JSON.
2. تولید هش یکتا با الگوریتم MD5 بر روی محتوای JSON مرتب‌شده ستون‌ها.
3. جستجو در Redis با کلید `features:{hash}`.
4. در صورت وجود (Hit): بازیابی آرایه ویژگی‌ها و صرفه‌جویی در زمان پیش‌پردازش.
5. در صورت عدم وجود (Miss): محاسبه ویژگی‌ها از طریق خط‌لوله `prepare()`.
6. ذخیره ویژگی‌های محاسبه‌شده در Redis با `SETEX` و TTL پیش‌فرض ۳۶۰۰ ثانیه.
7. به‌روزرسانی آمار کش (`cache_total_hits`, `cache_total_misses`, `cache_total_writes`).
8. در صورت عدم دسترسی به سرویس کش، ادامه عملیات بدون خطا و محاسبه محلی (Graceful Degradation).
9. پشتیبانی از پاک‌سازی دسته‌ای کش از طریق API برای اهداف تست و دیباگ.
  
---

### 1. Introduction
#### 1.1 Purpose
This document specifies the functional and non-functional requirements for the **MLOps Churn Prediction Platform**. The platform enables data science and ML engineering teams to train, track, deploy, monitor, and manage automated retraining of machine learning models in a production-grade environment. All requirements are strictly aligned with the current implemented codebase.

#### 1.2 Scope
The system encompasses the following subsystems:
- Data ingestion, validation, and preprocessing with one-hot encoding and missing value management
- Training and hyperparameter optimization of a Random Forest classifier using Optuna
- Experiment tracking, artifact logging, and model registry management via MLflow
- Distributed feature caching (Redis) with MD5 hashing, dynamic TTL, and graceful degradation
- Real-time (single) and batch prediction serving via a RESTful API (FastAPI)
- Intelligent retraining queue: automatic prediction logging to Redis, priority-based batch extraction, and pre-deployment model performance comparison
- Asynchronous retraining and batch prediction via Celery workers with in-memory model/column caching
- Full observability stack (Prometheus, Grafana, Loki, Fluent-bit) with structured asynchronous JSON logging
- Containerized deployment with dependency management, Nginx reverse proxy, and cross-platform Docker/Podman support

#### 1.3 Definitions and Acronyms
| Term                                  | Meaning                                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| MLOps                                 | Machine Learning Operations (lifecycle management)                                            |
| MLflow                                | Open-source platform for experiment tracking, model registry, and artifact storage            |
| Optuna                                | Hyperparameter optimization framework using TPE Sampler                                       |
| Celery                                | Distributed task queue for asynchronous execution                                             |
| Redis                                 | Distributed cache and message broker                                                          |
| Prometheus                            | Time-series metrics collection and query engine                                               |
| Grafana                               | Visualization platform for dashboards and log exploration                                     |
| Loki                                  | Log aggregation and indexing system                                                           |
| Fluent-bit                            | Lightweight log forwarder with async HTTP delivery                                            |
| Garage                                | S3-compatible object storage for model artifacts                                              |
| Retrain Queue (`RetrainQueueManager`) | Redis-backed pipeline for collecting prediction data and triggering incremental model updates |

---

### 2. Overall Description
#### 2.1 Product Perspective
The platform is a self-contained microservice architecture orchestrated via Docker Compose / Podman Compose. Initial training data is sourced from `data/churn.csv`, with extensibility for external data streams or cloud sources. All configurations are externalized, and the system is optimized for reproducible deployment on any container host.

#### 2.2 User Characteristics
- **Data Scientists:** Model training, experiment definition, metric review, and version comparison via MLflow UI.
- **ML Engineers:** Model deployment, API-driven version management, performance monitoring, and retraining orchestration.
- **Operations / DevOps:** Infrastructure management, Grafana dashboard monitoring, alert configuration, and log analysis via Loki.
- **External Systems:** Integration via standardized REST endpoints for real-time/batch predictions and training data submission.

---

### 3. System Features and Requirements
#### 3.1 Functional Requirements
**Data Ingestion and Preprocessing**
- The system shall load data from `data/churn.csv`.
- Preprocessing includes numeric conversion of `TotalCharges`, dropping rows with missing values, one-hot encoding categorical variables, and mapping `Churn` to `{Yes:1, No:0}`.
- Data is split 80/20 with stratified sampling (`stratify=y`) into training and test sets.

**Feature Cache**
- The system shall store preprocessed features in Redis using the key format `features:{md5_hash}`. The hash is computed from sorted JSON input content.
- Default Time-To-Live (TTL) is 3600 seconds and is configurable.
- On cache hit, the preprocessing step is bypassed.
- On Redis unavailability, the system operates in graceful degradation mode and computes features locally.
- Cache statistics (hits, misses, hit rate, total writes) are exposed via `/api/monitoring/cache/stats`.
- Forced cache invalidation is available via `DELETE /api/monitoring/cache`.

**Model Training and Hyperparameter Optimization**
- The system shall train a `RandomForestClassifier` using Optuna.
- Optimization runs 15 trials with 5-fold cross-validation, maximizing `roc_auc`.
- Tunable hyperparameters: `n_estimators` (50–200), `max_depth` (3–10), `min_samples_split` (2–8).
- **New Feature:** The `train_from_redis.py` pipeline first attempts to load training data from the Redis retrain queue. If empty, it falls back to the original CSV.
- Before promotion to Production, the system automatically compares new model metrics (`auc`, `accuracy`, `f1`) against the active Production version. Promotion occurs only if the new model performs equal or better; otherwise, it is archived.

**Experiment Tracking and Model Management**
- All runs are logged to MLflow: parameters, metrics, and artifacts (`model.pkl`, `columns.pkl`).
- The best model is registered in the `churn_model` registry.
- The API provides endpoints for retrieving the active model, listing all versions, comparing performance, and manual deployment (`/api/models/deploy`).

**Inference API (FastAPI)**
- Core endpoints:
  - `POST /api/predictions/single`: Returns `prediction`, `probability`, `confidence`, `model_version`.
  - `POST /api/predictions/batch`: Accepts up to 10,000 records, returns a `batch_id`.
  - `GET /api/batch/{batch_id}/status`: Tracks job progress.
  - `GET /api/batch/{batch_id}/results`: Retrieves results and statistical summary.
  - `POST /api/collect-training-data`: Manually submits labeled training data.
  - `GET /api/health`: Service and dependency health check.
  - `GET /api/monitoring/prediction-stats`: Real-time prediction statistics from Redis.
  - `GET /api/docs`: Interactive Swagger/OpenAPI documentation.
- The API loads the Production model from MLflow at startup.
- Cache is checked before each prediction; computed features are cached afterward.
- **New Feature:** Every successful prediction is automatically logged to the `RetrainQueueManager` for future model updates.

**Asynchronous Retraining and Batch Prediction**
- Retraining is triggered via `POST /api/retrain` and dispatched to Celery. Status is trackable at `/api/retrain/{task_id}/status`.
- The retraining task executes the full pipeline, performs model comparison, and clears the training queue upon success.
- Batch prediction runs inside a Celery worker. The model and feature columns are cached in worker memory to prevent repeated I/O.
- Batch results are stored in Redis for 24 hours (86,400 seconds) and retrievable via `batch_id`.

**Model Artifact Storage**
- Artifacts (model, column mappings, plots) are stored in the `mlflow` bucket on Garage (S3-compatible).
- Metadata (parameters, metrics, tags, run info) is persisted in PostgreSQL.
- Credentials are injected exclusively via environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).

**Monitoring and Observability**
- Prometheus scrapes API metrics (`api_requests_total`, `api_request_duration_seconds`) and Python process metrics every 15 seconds.
- Application logs are generated in structured JSON format and sent asynchronously via HTTP to Fluent-bit, which forwards them to Loki.
- Grafana provides dashboards connected to Prometheus and Loki, including log exploration.
- `/api/monitoring/health/system` reports system health (CPU, RAM, Disk, backend connections).
- Every service automatically injects its name into all log records via `LoggerAdapter`.

**Reverse Proxy and Routing**
- Nginx routes: `/api/*` → API, `/mlflow/*` → MLflow, `/prometheus/*` → Prometheus, `/grafana/*` → Grafana.
- Supports WebSocket and correctly forwards `X-Real-IP`, `X-Forwarded-For`, and sub-path headers.
- HTTP to HTTPS redirection is configurable for production environments.

#### 3.2 Non-Functional Requirements
**Performance**
- Single prediction endpoint response time shall be < 500ms under normal load.
- The system shall handle ≥ 10 concurrent inference requests without degradation.
- Feature cache hit rate shall be ≥ 30% under typical load.

**Availability**
- Core services shall achieve 99% uptime in production-like environments.
- Healthchecks (`pg_isready`, `redis-cli ping`, `curl /health`) automatically restart unhealthy containers.

**Security**
- All sensitive data (DB passwords, S3 keys) must be passed via environment variables. Hardcoding is prohibited.
- The reverse proxy shall redirect unencrypted traffic to TLS in production.
- Default passwords for Grafana and Garage must be customizable via `.env`.

**Maintainability**
- The system is fully containerized and deployable via a single command (`make up`).
- `docker-compose.yml` and `Makefile` manage dependency ordering, startup sequence, and Docker/Podman compatibility.
- Configuration is fully externalized through `.env.example` and `.env`.

**Portability**
- The platform runs on any Linux/Windows container host.
- Deployment to orchestrators (Kubernetes, Swarm) requires minimal configuration adjustments.

---

### 4. External Interface Requirements
#### 4.1 User Interfaces
- **MLflow UI:** Experiment browsing, registry management, artifact inspection.
- **Grafana UI:** System/model metrics dashboards and LogQL log exploration.
- **Swagger UI (`/api/docs`):** Interactive API testing and OpenAPI schema viewing.
- **Prometheus UI:** Time-series metric querying and target status monitoring.

#### 4.2 Hardware Interfaces
- None (fully virtualized and hardware-agnostic).

#### 4.3 Software Interfaces
| Component   | Protocol/Port          | Role                                                          |
| ----------- | ---------------------- | ------------------------------------------------------------- |
| PostgreSQL  | TCP/5432               | MLflow metadata storage                                       |
| Redis       | TCP/6379               | Celery broker, feature cache, prediction stats, retrain queue |
| Garage (S3) | TCP/3900               | Model artifact storage                                        |
| Prometheus  | TCP/9090               | Metric collection and querying                                |
| Loki        | TCP/3100               | Log aggregation and indexing                                  |
| Fluent-bit  | TCP/8888 (input)       | Async JSON log receiver → Loki forwarder                      |
| Nginx       | TCP/80 (external 8080) | Edge reverse proxy and path-based routing                     |

---

### 5. System Architecture
The architecture follows a containerized microservices pattern:
1. **Edge Layer:** Nginx reverse proxy for path-based routing, header forwarding, and WebSocket support.
2. **Inference Service (Stateless):** FastAPI for real-time predictions, feature cache management, automatic training data logging, and Prometheus metric exposure.
3. **Async Worker (Celery):** Handles retraining and batch prediction with in-memory model/column caching to minimize latency.
4. **Stateful Backends:** PostgreSQL, Redis, Garage, and MLflow for state persistence, messaging, queues, and artifact tracking.
5. **Observability Stack:** Fluent-bit (collection) → Loki (storage) + Prometheus (metrics) → Grafana (visualization).
6. **Orchestration & Tooling:** `Makefile` for lifecycle management, `garage-setup.sh` for automated S3 initialization, and cross-platform Compose support.

---

### 6. Assumptions and Dependencies
- The `churn.csv` dataset exists at `./data/` and conforms to the expected schema.
- Container networking enables DNS-based service discovery.
- Container images are pulled from configured registries (`DOCKER_REGISTRY`, `PIP_INDEX_URL`).
- Users possess foundational knowledge of containerization, REST APIs, and environment variable management.
- Redis and Garage must be healthy before API and Worker startup (enforced via `depends_on` and healthchecks).

---

### 7. Appendices
#### Appendix A: Key Environment Variables
| Variable                                               | Purpose                            | Default/Sample                      |
| ------------------------------------------------------ | ---------------------------------- | ----------------------------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`    | Database authentication            | `mlops`, `admin`, `admin`           |
| `MLFLOW_S3_ENDPOINT_URL`                               | Garage S3 endpoint                 | `http://garage:3900`                |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`           | Object storage credentials         | Auto-generated by `garage-setup.sh` |
| `MLFLOW_TRACKING_URI`                                  | Tracking server address            | `http://mlflow:5000`                |
| `REDIS_URL`                                            | Queue and cache connection         | `redis://redis:6379/0`              |
| `GRAFANA_ADMIN_PASSWORD`                               | Dashboard login password           | Configurable in `.env`              |
| `DOCKER_REGISTRY`, `PIP_INDEX_URL`, `PIP_TRUSTED_HOST` | Image/package mirror configuration | Set for internal/external networks  |

#### Appendix B: Training Pipeline Detail
1. Load data from Redis retrain queue (fallback to `churn.csv` if empty).
2. Preprocess features (one-hot encoding, missing value handling, target mapping).
3. Split data 80/20 with stratified sampling.
4. Optimize hyperparameters via Optuna (15 trials, 5-fold CV, maximize ROC-AUC).
5. Train final Random Forest model with best parameters.
6. Evaluate metrics (accuracy, precision, recall, F1, AUC).
7. Log to MLflow (parameters, metrics, artifacts including model & `columns.pkl`).
8. **Automatic comparison** with current Production version on key metrics.
9. Register model and promote to Production if performance is equal/better; otherwise archive.
10. Automatically clear the Redis retrain queue upon successful promotion.

#### Appendix C: Feature Cache Mechanism Detail
1. Receive customer input data as JSON.
2. Generate unique MD5 hash from sorted JSON column content.
3. Query Redis with key `features:{hash}`.
4. Cache Hit: Retrieve features, skip preprocessing.
5. Cache Miss: Compute features via `prepare()` pipeline.
6. Store computed features in Redis using `SETEX` with default TTL 3600s.
7. Update cache statistics (`cache_total_hits`, `cache_total_misses`, `cache_total_writes`).
8. Graceful degradation: Continue operation locally if Redis is unreachable.
9. Batch cache clearing supported via API for testing/debugging.