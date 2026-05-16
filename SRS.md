# پلتفرم عملیات یادگیری ماشین برای پیش‌بینی ریزش مشتری  
# سند نیازمندی‌های نرم‌افزار

**نسخه**: ۴.۰.۰  
**تاریخ**: ۱۴۰۵/۰۲/۲۶

---

## فهرست مطالب

- [فارسی](#۱-مقدمه) / [English](#1-introduction)

---

### ۱. مقدمه
#### ۱.۱ هدف
هدف این سند، تعیین نیازمندی‌های عملکردی و غیرعملکردی **پلتفرم عملیات یادگیری ماشین (MLOps) برای پیش‌بینی ریزش مشتری** است. این پلتفرم به تیم‌های داده و مهندسان ML امکان می‌دهد مدل‌ها را در محیطی تولیدی آموزش دهند، ردیابی کنند، مستقر کنند، پایش نمایند و بازآموزی خودکار/دستی را مدیریت کنند. تمام نیازمندی‌ها دقیقاً منطبق بر پیاده‌سازی فعلی کدنویسی‌شده بازنگری شده‌اند. نسخه ۴.۰.۰ نسبت به نسخه قبلی شامل بهبودهای اساسی در کش ویژگی آگاه از نسخه مدل، تشخیص خودکار دریفت مبتنی بر داده‌های واقعی Redis، محدودیت نرخ درخواست با الگوریتم پنجره لغزان، و مستندسازی کامل نوآوری‌های پلتفرم می‌باشد.

#### ۱.۲ حوزه عملکرد
سیستم شامل زیرسیستم‌های زیر است:
- بارگذاری، اعتبارسنجی و پیش‌پردازش داده‌های مشتریان با پشتیبانی از یک‌داغ‌گذاری و مدیریت مقادیر گمشده
- آموزش و بهینه‌سازی فراپارامترهای مدل طبقه‌بند جنگل تصادفی با چارچوب Optuna
- ردیابی آزمایش‌ها، ثبت مصنوعات و مدیریت رجیستری مدل با MLflow
- کش توزیع‌شده ویژگی‌ها (Redis) با هش یکتا، انقضای پویا، آگاهی از نسخه مدل و حالت کاهش‌یافته (Graceful Degradation)
- ارائه پیش‌بینی‌های بلادرنگ (تکی) و دسته‌جمعی (Batch) از طریق واسط RESTful
- صف بازآموزی هوشمند: ذخیره خودکار پیش‌بینی‌ها در Redis، اولویت‌دهی به داده‌های جدید و مقایسه عملکرد قبل از ارتقا
- بازآموزی غیرهمزمان و پیش‌بینی دسته‌جمعی با کارگر Celery
- تشخیص خودکار دریفت داده با استفاده از کتابخانه Evidently و داده‌های واقعی ذخیره‌شده در Redis
- پشته کامل دیدپذیری (Prometheus، Grafana، Loki، Fluent-bit) با لاگ‌گیری ساختاریافته غیرهمزمان
- احراز هویت مبتنی بر کلید API با سه نقش کاربری و محدودیت نرخ درخواست مبتنی بر نقش
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
| کش ویژگی (Feature Cache) | مکانیزم ذخیره‌سازی پیش‌پردازش شده بر پایه هش MD5 و نسخه مدل    |
| دریفت داده (Data Drift)  | تغییر توزیع آماری داده‌های ورودی نسبت به داده‌های آموزشی       |

---

### ۲. توصیف کلی
#### ۲.۱ جایگاه محصول
این پلتفرم یک سامانه خودایستا مبتنی بر ریزسرویس‌ها است که با Docker Compose / Podman Compose مدیریت می‌شود. داده‌های اولیه از فایل `churn.csv` بارگذاری شده و قابلیت توسعه به منابع داده خارجی یا جریان‌های بلادرنگ را دارد. تمام پیکربندی‌ها برون‌سپاری شده و سیستم برای اجرا در هر میزبان کانتینری بهینه‌سازی شده است. این پلتفرم با ارائه کش ویژگی آگاه از نسخه مدل، تشخیص دریفت خودکار از داده‌های واقعی، و مقایسه خودکار مدل قبل از استقرار، در مقایسه با رقبای بین‌المللی مانند Kubeflow، SageMaker و Vertex AI، کاهش ۸۰ درصدی هزینه زیرساخت و زمان پیاده‌سازی کمتر از ۳۰ دقیقه را ارائه می‌دهد.

#### ۲.۲ کاربران هدف
- **دانشمندان داده:** آموزش مدل، تعریف آزمایش‌ها، بررسی سنجه‌ها و مقایسه نسخه‌ها در MLflow
- **مهندسان ML:** استقرار مدل، مدیریت نسخه‌ها از طریق API، پایش عملکرد و شروع بازآموزی
- **تیم عملیات (DevOps):** مدیریت زیرساخت، بررسی داشبوردهای Grafana، تنظیم هشدارها و نگهداری لاگ‌ها در Loki
- **سیستم‌های خارجی:** از طریق API استاندارد REST برای دریافت پیش‌بینی یا ارسال داده‌های آموزشی

---

### ۳. نیازمندی‌ها
#### ۳.۱ نیازمندی‌های عملکردی

**دریافت و پیش‌پردازش داده**
- سیستم باید داده‌ها را از مسیر `data/churn.csv` بارگذاری کند.
- پیش‌پردازش شامل مراحل زیر است: حذف ستون `customerID` در صورت وجود، تبدیل `TotalCharges` به نوع عددی و جایگزینی مقادیر غیرعددی با `NaN`، حذف رکوردهای حاوی مقدار گمشده در هر ستون، یک‌داغ‌گذاری متغیرهای دسته‌ای شامل `Contract`، `InternetService` و `PaymentMethod`.
- نگاشت ستون هدف `Churn` به مقادیر عددی (`Yes` → ۱، `No` → ۰) انجام می‌شود.
- داده‌ها با نسبت ۸۰/۲۰ و نمونه‌برداری طبقه‌بندی‌شده (`stratify=y`) به مجموعه آموزش و آزمون تقسیم می‌شوند.
- تمام مراحل پیش‌پردازش در کلاس `FeatureStore` در فایل `shared/feature_store.py` پیاده‌سازی شده است و برای هر دو حالت آموزش و استنتاج یکسان عمل می‌کند.

**کش ویژگی (Feature Cache)**
- سیستم باید ویژگی‌های پیش‌پردازش شده را در Redis با فرمت کلید `features:{md5_hash}:v{model_version}` ذخیره کند. هش بر اساس محتوای JSON مرتب‌شده دیتافریم ورودی محاسبه می‌شود.
- زمان انقضا (TTL) پیش‌فرض ۳۶۰۰ ثانیه است و از متغیر محیطی `CACHE_TTL_SECONDS` قابل تنظیم می‌باشد.
- مقدار کش شده با فرمت Pickle (نه JSON) ذخیره می‌شود تا سرعت بارگذاری افزایش یابد.
- در صورت وجود داده در کش، مرحله پیش‌پردازش دور زده می‌شود (Cache Hit).
- در صورت عدم دسترسی به Redis، سیستم به حالت کاهش‌یافته (Graceful Degradation) رفته و پیش‌پردازش را محلی انجام می‌دهد.
- آمار کش (تعداد Hit، Miss، نرخ Hit و کل Writes) از طریق نقطه‌پایان `/api/monitoring/cache/stats` قابل بازیابی است.
- قابلیت پاک‌سازی اجباری کش از طریق `DELETE /api/monitoring/cache` فراهم شده است.
- در زمان ارتقای مدل به Production، تابع `clear_cache_for_model_version(version_old)` فراخوانی می‌شود تا کش نسخه قدیم پاک گردد. این مکانیزم از رشد نامحدود کلیدهای کش در Redis جلوگیری می‌کند.

**آموزش مدل و بهینه‌سازی فراپارامترها**
- سیستم باید یک طبقه‌بند `RandomForestClassifier` را با Optuna آموزش دهد.
- بهینه‌سازی با ۱۵ تلاش، اعتبارسنجی متقابل ۵-بخشی و معیار بیشینه‌سازی `roc_auc` انجام می‌شود.
- فراپارامترهای جستجو: `n_estimators` (50-200)، `max_depth` (3-10)، `min_samples_split` (2-8).
- خط‌لوله آموزشی یکپارچه `train.py` ابتدا سعی می‌کند داده‌ها را از صف بازآموزی Redis بارگذاری کند. در صورت خالی بودن، به فایل CSV باز می‌گردد (Fallback).
- قبل از ارتقا به Production، سیستم به‌صورت خودکار معیارهای نسخه جدید را با نسخه فعال مقایسه می‌کند (`auc`, `accuracy`, `f1`). در صورت برتری یا برابری در حداقل یک معیار، ارتقا انجام می‌شود؛ در غیر این‌صورت نسخه بایگانی می‌شود.
- پس از ارتقا، صف بازآموزی Redis پاک می‌شود.

**ردیابی آزمایش‌ها و مدیریت مدل**
- تمام اجراها در MLflow ثبت می‌شوند: پارامترها، سنجه‌ها، و مصنوعات (`model.pkl`, `columns.pkl`).
- بهترین مدل در رجیستری `churn_model` ثبت و پس از آموزش موفق به مرحله `Production` ارتقا می‌یابد.
- API مدیریت مدل (`/api/models/*`) امکان دریافت نسخه فعال، لیست همه نسخه‌ها، مقایسه عملکرد و استقرار دستی (`/deploy`) را فراهم می‌کند.

**واسط برنامه‌نویسی استنتاج (FastAPI)**
- نقاط پایان اصلی:
  - `POST /api/predictions/single`: پیش‌بینی تکی با بازگرداندن `prediction`, `probability`, `confidence`, `model_version`, `prediction_id`.
  - `POST /api/predictions/batch`: ارسال دسته‌جمعی (تا ۱۰,۰۰۰ رکورد) و بازگرداندن `batch_id`.
  - `GET /api/predictions/batch/{batch_id}/status`: بررسی وضعیت پردازش.
  - `GET /api/predictions/batch/{batch_id}/results`: دریافت نتایج و خلاصه آماری.
  - `POST /api/feedback/{prediction_id}`: ثبت برچسب واقعی برای یک پیش‌بینی قبلی.
  - `POST /api/predictions/collect-training-data`: ذخیره دستی داده‌های آموزشی برچسب‌دار (بدون نیاز به پیش‌بینی قبلی).
  - `GET /api/health`: بررسی سلامت سرویس و اتصالات.
  - `GET /api/monitoring/prediction-stats`: آمار بلادرنگ پیش‌بینی‌ها از Redis.
  - `GET /api/docs`: مستندات تعاملی Swagger/OpenAPI.
- واسط باید در راه‌اندازی، مدل Production را از MLflow بارگذاری کند.
- قبل از هر پیش‌بینی، کش بررسی می‌شود. پس از محاسبه، ویژگی‌ها در Redis ذخیره می‌شوند.
- هر پیش‌بینی موفق به‌صورت خودکار در صف بازآموزی (`RetrainQueueManager`) با وضعیت `pending` ثبت می‌شود تا برای آموزش‌های آتی استفاده گردد.

**بازآموزی غیرهمزمان و پیش‌بینی دسته‌جمعی**
- بازآموزی از طریق `POST /api/retrain` به Celery ارسال می‌شود. وضعیت از `/api/retrain/{task_id}/status` قابل پیگیری است.
- وظیفه بازآموزی خط‌لوله کامل را اجرا کرده، مقایسه می‌کند و در صورت موفقیت، صف آموزشی Redis را پاک می‌کند.
- پیش‌بینی دسته‌جمعی در کارگر Celery اجرا می‌شود. مدل و ستون‌ها در حافظه کارگر کش می‌شوند تا از بارگذاری مجدد جلوگیری شود.
- نتایج پیش‌بینی دسته‌جمعی به مدت ۲۴ ساعت (۸۶۴۰۰ ثانیه) در Redis ذخیره و با `batch_id` قابل بازیابی است.

**تشخیص خودکار دریفت (Automatic Drift Detection)**
- سیستم باید یک وظیفه Celery دوره‌ای با نام `periodic_drift_check` داشته باشد که به صورت پیش‌فرض هر ساعت یک بار اجرا می‌شود.
- وظیفه باید پیش‌بینی‌های ۲۴ ساعت اخیر را از صف بازآموزی Redis با استفاده از متد `get_recent_predictions` بخواند.
- اگر تعداد نمونه‌های خوانده شده کمتر از ۱۰۰ باشد، وظیفه با وضعیت `skipped` پایان می‌یابد.
- در صورت وجود نمونه‌های کافی، سیستم باید با استفاده از کتابخانه Evidently و `DataDriftPreset`، دریفت را بین داده‌های جاری و داده مرجع (بارگذاری شده از `churn.csv`) محاسبه کند.
- وضعیت دریفت مجموعه داده (`dataset_drift`) و لیست ستون‌های دریفت‌یافته باید استخراج شود.
- نتایج باید در MLflow به عنوان یک اجرای جداگانه با نام `auto_drift_check` ثبت شوند.
- گزارش HTML دریفت و لیست ستون‌های دریفت‌یافته باید به عنوان مصنوعات (Artifacts) در MLflow ذخیره گردند.
- متریک‌های Prometheus `dataset_drift` و `drifted_columns_count` باید به‌روزرسانی شوند.
- در صورت تشخیص دریفت، یک هشدار در لاگ ساختاریافته ثبت می‌شود که توسط Loki قابل ردیابی است.

**ذخیره‌سازی مصنوعات مدل**
- مصنوعات (مدل، فایل ستون‌ها، نمودار اهمیت ویژگی) در سطل `mlflow` ذخیره‌سازی Garage (S3-compatible) ذخیره می‌شوند.
- فراداده‌ها (پارامترها، سنجه‌ها، تگ‌ها، اطلاعات اجرا) در PostgreSQL نگهداری می‌شوند.
- اعتبارنامه‌ها صرفاً از طریق متغیرهای محیطی (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) تزریق می‌شوند.
- اسکریپت `garage-setup.sh` در زمان راه‌اندازی اولیه، گره را مقداردهی اولیه، کلید API را ایجاد، و سطل `mlflow` را می‌سازد.

**مانیتورینگ و دیدپذیری**
- Prometheus سنجه‌های API (`api_requests_total`, `api_request_duration_seconds`) و فرآیند پایتون را هر ۱۵ ثانیه می‌رباید.
- لاگ‌ها به فرمت ساختاریافته JSON تولید شده و از طریق هندلر غیرهمزمان HTTP به Fluent-bit ارسال می‌شوند. Fluent-bit آن‌ها را به Loki فوروارد می‌کند.
- Grafana با اتصال به Prometheus و Loki، داشبوردهای عملکردی، سنجه‌های سیستم و کاوشگر لاگ را ارائه می‌دهد. چهار داشبورد اصلی شامل API Performance، Model Performance، System Health و Log Explorer به صورت خودکار تأمین می‌شوند.
- نقطه‌پایان `/api/monitoring/health/system` وضعیت سلامت سیستم (CPU، RAM، Disk، اتصالات به MLflow، PostgreSQL و Redis) را گزارش می‌کند.
- هر سرویس نام خود را به‌طور خودکار در تمام لاگ‌ها تزریق می‌کند (`LoggerAdapter`).

**پروکسی معکوس و مسیریابی**
- Nginx درخواست‌ها را به مسیرهای زیر هدایت می‌کند: `/api/*` → API، `/mlflow/*` → MLflow، `/prometheus/*` → Prometheus، `/grafana/*` → Grafana.
- پشتیبانی از WebSocket و هدرهای `X-Real-IP`، `X-Forwarded-For` برای عملیات صحیح زیرمسیرها.
- قابلیت هدایت HTTP به HTTPS در محیط تولید (قابل پیکربندی).

#### ۳.۲ نیازمندی‌های غیرعملکردی

**کارایی**
- زمان پاسخ نقطه‌پایان پیش‌بینی تکی در بار معمولی باید کمتر از ۵۰۰ میلی‌ثانیه باشد.
- سیستم باید حداقل ۱۰ درخواست هم‌زمان را بدون افت محسوس پردازش کند.
- نرخ اصابت کش ویژگی در بار معمولی باید ≥ ۳۰٪ باشد. نرخ اصابت به صورت `total_hits / (total_hits + total_misses)` محاسبه می‌شود.
- در صورت کاهش نرخ اصابت کش به زیر ۱۰٪، باید هشدار تولید شود (قابل پیکربندی در Grafana).

**دسترس‌پذیری**
- سرویس‌های اصلی باید دسترس‌پذیری ۹۹٪ در محیط شبه‌تولیدی داشته باشند.
- Healthcheckها (`pg_isready`, `redis-cli ping`, `curl /health`) کانتینرهای ناسالم را به‌طور خودکار راه‌اندازی مجدد می‌کنند.

**امنیت**
- تمام اطلاعات حساس (گذرواژه‌ها، کلیدهای S3) باید از طریق `.env` منتقل شوند. هیچ‌کدام نباید در کد سخت‌کد شوند.
- پروکسی معکوس باید در تولید، ترافیک غیررمزنگاری شده را به TLS هدایت کند.
- گذرواژه‌های پیش‌فرض Grafana و Garage باید از طریق متغیرهای محیطی قابل تغییر باشند.

**احراز هویت و مجوزدهی (Authentication & Authorization)**
- سیستم باید از احراز هویت مبتنی بر کلید API (API Key) با هدر `X-API-Key` پشتیبانی کند.
- سه نقش کاربری باید تعریف شود: `admin` (دسترسی کامل شامل استقرار مدل)، `user` (خواندن و نوشتن شامل پیش‌بینی و ثبت برچسب)، `readonly` (فقط خواندن شامل مشاهده وضعیت و متریک‌ها).
- نقطه‌پایان‌های عمومی (health، docs، metrics) نباید نیاز به احراز هویت داشته باشند.
- نقطه‌پایان‌های پیش‌بینی و مشاهده وضعیت نیاز به مجوز `read` دارند.
- نقطه‌پایان‌های ارسال batch، جمع‌آوری داده آموزشی، و ثبت برچسب نیاز به مجوز `write` دارند.
- نقطه‌پایان بازآموزی مدل نیاز به مجوز `retrain` دارد.
- نقطه‌پایان استقرار مدل نیاز به مجوز `admin` دارد.

**محدودیت نرخ درخواست (Rate Limiting)**
- سیستم باید از محدودیت نرخ مبتنی بر Redis با الگوریتم پنجره لغزان (sliding window) استفاده کند. این الگوریتم نسبت به پنجره ثابت دقیق‌تر است و پدیده «تپش در مرز پنجره» (Boundary Burst) را ندارد.
- محدودیت‌های نرخ باید بر اساس نقش کاربری متفاوت باشد: admin (۱۰۰۰ درخواست/دقیقه)، user (۱۰۰ درخواست/دقیقه)، readonly (۵۰ درخواست/دقیقه)، anonymous (۱۰ درخواست/دقیقه).
- داده‌های نرخ در قالب Redis Sorted Set با کلید `rate_limit:{role}:{identifier}` ذخیره می‌شوند.
- در صورت تجاوز از محدودیت، سیستم باید کد وضعیت HTTP 429 با هدرهای `X-RateLimit-Limit`، `X-RateLimit-Remaining`، `X-RateLimit-Reset` و `Retry-After` برگرداند.
- در صورت عدم دسترسی به Redis، سیستم باید در حالت fail-open عمل کند و درخواست‌ها را بپذیرد (اصل دسترس‌پذیری بر صحت).

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
2. **سرویس استنتاج (Stateless API):** FastAPI برای پیش‌بینی بلادرنگ، مدیریت کش ویژگی آگاه از نسخه مدل، ثبت خودکار داده‌های آموزشی در صف بازآموزی، اعمال محدودیت نرخ مبتنی بر نقش، و انتشار سنجه‌های Prometheus.
3. **کارگر غیرهمزمان (Celery Worker):** اجرای بازآموزی (با بارگذاری داده از Redis یا CSV، بهینه‌سازی، مقایسه و ارتقا)، پیش‌بینی دسته‌جمعی (با کش داخلی مدل و ستون‌ها)، تشخیص خودکار دریفت (دوره‌ای هر ساعت)، و انقضای رکوردهای قدیمی صف بازآموزی. مدل و ستون‌های ویژگی در حافظه کارگر کش می‌شوند.
4. **سرویس‌های پشتیبان (Stateful):** PostgreSQL (فراداده MLflow)، Redis (صف Celery، کش ویژگی با نسخه مدل، صف بازآموزی با کلید `retrain:training_data`، آمار پیش‌بینی)، Garage S3 (مصنوعات مدل)، MLflow (رجیستری مدل و واسط کاربری ردیابی).
5. **پشته دیدپذیری:** Fluent-bit (جمع‌آوری لاگ‌های JSON از طریق HTTP روی پورت ۸۸۸۸) → Loki (ذخیره‌سازی و ایندکس‌گذاری) + Prometheus (جمع‌آوری متریک‌های API هر ۱۵ ثانیه) → Grafana (مصورسازی چهار داشبورد اصلی).
6. **ابزارهای راه‌اندازی:** `Makefile` برای مدیریت چرخه حیات با دستورات `make up`, `make down`, `make build-base`, `make test`، `garage-setup.sh` برای مقداردهی اولیه خودکار S3 (ایجاد گره، کلید API، سطل mlflow).

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
| متغیر                                                  | هدف                          | مقدار پیش‌فرض/نمونه                  |
| ------------------------------------------------------ | ---------------------------- | ----------------------------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`    | احراز هویت دیتابیس           | `mlops`, `admin`, `admin`           |
| `MLFLOW_S3_ENDPOINT_URL`                               | نشانی Garage S3              | `http://garage:3900`                |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`           | اعتبارنامه‌های شیء‌ذخیره       | تولید خودکار توسط `garage-setup.sh` |
| `MLFLOW_TRACKING_URI`                                  | نشانی سرور ردیابی            | `http://mlflow:5000`                |
| `REDIS_URL`                                            | نشانی صف و کش                | `redis://redis:6379/0`              |
| `GRAFANA_ADMIN_PASSWORD`                               | رمز ورود داشبورد             | قابل تغییر در `.env`                |
| `DOCKER_REGISTRY`, `PIP_INDEX_URL`, `PIP_TRUSTED_HOST` | آینه‌های دریافت تصویر و بسته  | تنظیم شده برای شبکه داخلی/خارجی     |
| `RATE_LIMIT_ENABLED`                                   | فعال/غیرفعال‌سازی محدودیت نرخ | `true`                              |
| `RATE_LIMIT_ADMIN`, `USER`, `READONLY`, `ANONYMOUS`    | سقف درخواست بر اساس نقش      | ۱۰۰۰, ۱۰۰, ۵۰, ۱۰                   |
| `API_KEY_ADMIN`, `API_KEY_USER`, `API_KEY_READONLY`    | کلیدهای احراز هویت نقش‌ها     | قابل تغییر در `.env`                |
| `CACHE_TTL_SECONDS`                                    | زمان انقضای کش ویژگی (ثانیه) | ۳۶۰۰                                |

#### پیوست ب: جزئیات خط‌لوله آموزش
1. بارگذاری داده از Redis (صف بازآموزی) یا بازگشت به `churn.csv` در صورت خالی بودن صف.
2. پیش‌پردازش ویژگی‌ها (یک‌داغ‌گذاری، مدیریت مقادیر گمشده، نگاشت هدف).
3. تقسیم داده به نسبت ۸۰ به ۲۰ با نمونه‌برداری طبقه‌بندی‌شده.
4. بهینه‌سازی فراپارامترها با Optuna (۱۵ تلاش، اعتبارسنجی متقابل ۵-بخشی، بیشینه‌سازی ROC-AUC).
5. آموزش مدل نهایی جنگل تصادفی با بهترین پارامترها.
6. ارزیابی سنجه‌ها (صحت، دقت، بازخوانی، F1، سطح زیر منحنی).
7. ثبت در MLflow (پارامترها، سنجه‌ها، مصنوعات شامل مدل و `columns.pkl` و `feature_importance.json`).
8. **مقایسه خودکار** با نسخه Production فعلی بر اساس معیارهای `auc`, `accuracy`, `f1`.
9. ثبت مدل در رجیستری و ارتقا به مرحله Production در صورت برتری یا برابری در حداقل یک معیار.
10. پاک‌سازی خودکار صف بازآموزی Redis پس از موفقیت.

#### پیوست ج: جزئیات مکانیزم کش ویژگی
1. دریافت داده ورودی مشتری در قالب JSON.
2. تولید هش یکتا با الگوریتم MD5 بر روی محتوای JSON مرتب‌شده ستون‌ها.
3. جستجو در Redis با کلید `features:{hash}:v{model_version}`.
4. در صورت وجود (Hit): بازیابی آرایه ویژگی‌ها با استفاده از Pickle و صرفه‌جویی در زمان پیش‌پردازش.
5. در صورت عدم وجود (Miss): محاسبه ویژگی‌ها از طریق خط‌لوله `prepare()` کلاس `FeatureStore`.
6. ذخیره ویژگی‌های محاسبه‌شده در Redis با `SETEX`، TTL پیش‌فرض ۳۶۰۰ ثانیه، و فرمت Pickle.
7. به‌روزرسانی آمار کش (`cache_total_hits`, `cache_total_misses`, `cache_total_writes`).
8. در صورت عدم دسترسی به سرویس کش، ادامه عملیات بدون خطا و محاسبه محلی (Graceful Degradation).
9. پشتیبانی از پاک‌سازی دستی کش از طریق `DELETE /api/monitoring/cache`.
10. در زمان ارتقای مدل، فراخوانی `clear_cache_for_model_version(version_old)` برای پاک‌سازی کش نسخه قدیم.

#### پیوست د: انگیزه و نوآوری (Value Proposition & Innovation)

**چشم‌انداز رقابتی**

در عصر تحول دیجیتال، سازمان‌ها برای حفظ مزیت رقابتی خود ناگزیر به استفاده از هوش مصنوعی و یادگیری ماشین هستند. اما چالش اصلی، نه ساخت مدل، که نگهداری و عملیاتی‌سازی آن در محیط تولید است. آمارها نشان می‌دهند بیش از ۸۵٪ پروژه‌های یادگیری ماشین هرگز به مرحله تولید نمی‌رسند و از آنهایی که می‌رسند، حدود ۶۰٪ در شش ماه اول به دلیل افت کیفیت داده یا عدم پایش مناسب از دور خارج می‌شوند.

پلتفرم حاضر با درک عمیق این چالش‌ها طراحی شده است.

**سه چالش اصلی در MLOps سنتی**

*چالش اول: پیچیدگی زیرساخت*

راهکارهای موجود مانند Kubeflow، SageMaker و Vertex AI نیاز به کلاسترهای Kubernetes با حداقل سه نود دارند. هزینه نگهداری چنین زیرساختی برای بسیاری از سازمان‌های کوچک و متوسط غیرقابل‌تحمل است. علاوه بر هزینه، دانش فنی مورد نیاز برای مدیریت این پشته‌ها نیز یک مانع جدی محسوب می‌شود.

*چالش دوم: نبود دید کافی بر مدل در حال تولید*

بسیاری از سازمان‌ها پس از استقرار مدل، تنها به پایش لاگ‌های خطا اکتفا می‌کنند. اما سوالات اساسی بی‌پاسخ می‌مانند: آیا داده‌های ورودی نسبت به داده‌های آموزشی تغییر کرده‌اند (Data Drift)؟ آیا مدل همچنان دقیق پیش‌بینی می‌کند؟ چه زمانی باید بازآموزی انجام شود؟

*چالش سوم: بازآموزی ناکارآمد*

در اکثر سیستم‌ها، بازآموزی یا به صورت دستی و با تأخیر انجام می‌شود یا به صورت دوره‌ای و بدون توجه به نیاز واقعی. در هر دو حالت، منابع محاسباتی هدر می‌رود و گاهی مدل جدیدی که عملکرد بدتری دارد جایگزین مدل قبلی می‌شود.

**نوآوری‌های کلیدی پلتفرم**

*نوآوری اول: کش ویژگی آگاه از نسخه مدل*

در معماری‌های سنتی کش ویژگی، هنگامی که مدل جدیدی به Production ارتقا می‌یابد، تمام کش قبلی بی‌اعتبار می‌شود. این امر باعث می‌شود نرخ اصابت کش (Cache Hit Rate) به صفر نزدیک شود و سیستم برای مدتی با بار محاسباتی بالا مواجه گردد.

پلتفرم ما با طراحی کلید کش به صورت `features:{hash}:v{model_version}`، کش نسخه قدیم را تا پایان عمر طبیعی آن معتبر نگه می‌دارد. به عبارت دیگر، در لحظه ارتقای مدل، نرخ اصابت کش به یکباره سقوط نمی‌کند. این نوآوری ساده اما قدرتمند، نتیجه سال‌ها تجربه در عملیاتی‌سازی مدل‌های یادگیری ماشین است.

*نوآوری دوم: تشخیص دریفت مبتنی بر داده‌های واقعی*

بسیاری از ابزارهای تشخیص دریفت، داده‌های لحظه‌ای را با داده مرجع مقایسه می‌کنند. اما آیا این داده‌های لحظه‌ای نماینده واقعی توزیع داده هستند؟ پاسخ خیر است. یک نمونه تصادفی کوچک ممکن است نماینده نباشد و یک دسته ارسالی ممکن است اریب (Biased) باشد.

پلتفرم ما مستقیماً از داده‌های ذخیره‌شده در صف بازآموزی استفاده می‌کند. این داده‌ها حاصل پیش‌بینی‌های واقعی هستند و توزیع واقعی داده‌های تولید را بازتاب می‌دهند. علاوه بر این، وظیفه تشخیص دریفت به صورت خودکار و دوره‌ای (هر ساعت) اجرا می‌شود و نتایج در MLflow ثبت می‌گردد.

*نوآوری سوم: مقایسه خودکار مدل پیش از استقرار*

آیا تا به حال برای شما پیش آمده که مدلی جدید را جایگزین مدل قبلی کنید و متوجه شوید عملکرد آن بدتر است؟ این اتفاق در سیستم‌های سنتی رایج است. پلتفرم ما قبل از هرگونه ارتقا، متریک‌های مدل جدید (AUC، Accuracy، F1) را با مدل تولید فعلی مقایسه می‌کند. ارتقا تنها در صورتی انجام می‌شود که مدل جدید در حداقل یک معیار بهتر باشد. این مکانیزم از کاهش کیفیت سرویس جلوگیری می‌کند.

*نوآوری چهارم: صف بازآموزی غیرمزاحم*

در برخی پیاده‌سازی‌ها، ثبت داده در صف بازآموزی می‌تواند تأخیر پیش‌بینی را افزایش دهد. ما با استفاده از عملیات ساده `RPUSH` در Redis و انجام پردازش‌های سنگین (مانند یک‌داغ‌گذاری) در مسیر پیش‌بینی اصلی، این تأخیر را به حداقل رسانده‌ایم. ثبت داده در صف معمولاً کمتر از ۱ میلی‌ثانیه زمان می‌برد.

*نوآوری پنجم: پشته مشاهده‌پذیری یکپارچه*

به جای استفاده از ابزارهای پراکنده و ناهماهنگ، ما Prometheus، Loki و Grafana را در یک پشته یکپارچه گرد آورده‌ایم. لاگ‌ها به صورت ساختاریافته JSON تولید و به صورت ناهمگام به Fluent-bit ارسال می‌شوند. متریک‌های سفارشی (مانند نرخ دریفت، طول صف بازآموزی، نرخ اصابت کش) به طور خودکار در Prometheus ثبت می‌شوند.

**جدول مقایسه با رقبای بین‌المللی**

| ویژگی            | Kubeflow                        | SageMaker                  | Vertex AI     | پلتفرم حاضر                       |
| ---------------- | ------------------------------- | -------------------------- | ------------- | --------------------------------- |
| هزینه زیرساخت    | بالا (نیاز به کلاستر)           | بالا (پرداخت بر اساس مصرف) | بالا          | پایین (یک سرور با ۴ گیگابایت رم)  |
| زمان راه‌اندازی   | چند ساعت تا چند روز             | چند ساعت                   | چند ساعت      | کمتر از ۳۰ دقیقه                  |
| کش ویژگی         | نیاز به Feast                   | داخلی اما محدود            | داخلی         | Redis + نسخه‌مدل + Pickle          |
| تشخیص دریفت      | نیاز به ابزار جداگانه           | پولی                       | پولی          | یکپارچه (Evidently) + رایگان      |
| بازآموزی خودکار  | نیاز به Argo/Kubeflow Pipelines | دارد                       | دارد          | Celery + مقایسه خودکار متریک‌ها    |
| مشاهده‌پذیری      | نیاز به جدا کردن لاگ            | CloudWatch                 | Cloud Logging | یکپارچه (Loki+Grafana+Prometheus) |
| وابستگی به Cloud | خیر (اجرای on-prem)             | بله (AWS)                  | بله (GCP)     | خیر (اجرای anywhere)              |
| مستندات و API    | خوب                             | عالی                       | عالی          | کامل + OpenAPI (Swagger)          |
| منبع‌باز          | بله                             | خیر                        | خیر           | بله (کامل)                        |

**چرا کارفرما باید این پلتفرم را انتخاب کند؟**

*دلیل اول: کاهش هزینه زیرساخت*

اجرای این پلتفرم روی یک سرور مجازی با ۴ گیگابایت رم و ۲ هسته پردازشی امکان‌پذیر است. در مقابل، اجرای Kubeflow حداقل به ۸ گیگابایت رم و ۴ هسته نیاز دارد. این تفاوت در هزینه ماهیانه سرور، به ویژه برای استارتاپ‌ها و سازمان‌های کوچک، بسیار قابل توجه است.

*دلیل دوم: زمان پیاده‌سازی کمتر از ۳۰ دقیقه*

با یک دستور `make up`، تمام سرویس‌ها (PostgreSQL، Redis، Garage، MLflow، API، Worker، Prometheus، Loki، Fluent-bit، Grafana، Nginx) راه‌اندازی می‌شوند. نیازی به تنظیم دستی Kubernetes، IAM Roles، VPC، Subnets، یا Load Balancers نیست.

*دلیل سوم: قابلیت حمل و استقلال از ابر*

این پلتفرم وابسته به هیچ ارائه‌دهنده ابر خاصی نیست. می‌توان آن را روی زیرساخت داخلی سازمان (On-Premise)، هر ارائه‌دهنده ابری (AWS، GCP، Azure، DigitalOcean، Hetzner) و حتی روی لپ‌تاپ توسعه‌دهنده اجرا کرد. این استقلال، ریسک قفل‌شدن به یک فروشنده (Vendor Lock-in) را از بین می‌برد.

*دلیل چهارم: آماده برای تولید (Production-Ready)*

تمامی سرویس‌ها دارای Health Check (برای راه‌اندازی مجدد خودکار در صورت خرابی)، Retry Policy (برای مقابله با خطاهای موقت)، Graceful Degradation (ادامه کار با کاهش قابلیت در صورت خرابی سرویس جانبی)، و لاگ‌های ساختاریافته (برای عیب‌یابی آسان) هستند.

*دلیل پنجم: مستندات کامل و API استاندارد*

تمام نقاط پایانی API دارای مستندات OpenAPI (Swagger) هستند و با ابزارهای استاندارد مانند Postman، curl و حتی کد خودکار (Code Generation) قابل استفاده می‌باشند.

*دلیل ششم: پشتیبانی از سناریوهای واقعی کسب و کار*

سیستم از سه سناریو اصلی کسب و کار پشتیبانی می‌کند: پیش‌بینی لحظه‌ای (Real-time) برای درخواست‌های تکی، پیش‌بینی دسته‌جمعی (Batch) برای پردازش انبوه مشتریان (مثلاً گزارش ماهانه)، و جمع‌آوری داده‌های تاریخی برای بهبود مدل (Historical Data Ingestion).

---

#### پیوست ه: شرح کامل وظایف Celery (Celery Tasks Detailed Description)

| نام وظیفه                    | کرون‌جاب      | زمان پیش‌فرض | ورودی                              | خروجی                                       | شرح کامل                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------------------------- | ------------ | ----------- | ---------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `retrain`                    | ندارد (دستی) | -           | شناسه درخواست (task_id)            | `{status, version, metrics, run_id}`        | این وظیفه هسته بازآموزی سیستم است. ابتدا سعی می‌کند داده‌های برچسب‌خورده را از صف Redis بارگذاری کند. در صورت خالی بودن صف، به فایل CSV بازمی‌گردد. سپس خط‌لوله کامل آموزش (بهینه‌سازی، آموزش، ارزیابی، ثبت در MLflow) را اجرا می‌کند. پس از ثبت مدل جدید، متریک‌های آن را با مدل Production فعلی مقایسه می‌کند. در صورت بهبود، مدل جدید به Production ارتقا می‌یابد و کش ویژگی نسخه قدیم پاک می‌شود. در پایان، صف بازآموزی Redis را پاک می‌کند. |
| `periodic_drift_check`       | هر ساعت      | ۳۶۰۰ ثانیه  | `hours_back=24`، `min_samples=100` | `{dataset_drift, drifted_columns, samples}` | این وظیفه مسئول تشخیص خودکار دریفت است. پیش‌بینی‌های ۲۴ ساعت اخیر را از صف بازآموزی Redis می‌خواند. اگر تعداد نمونه‌ها کمتر از حد آستانه باشد، وظیفه با وضعیت `skipped` پایان می‌یابد. در غیر این صورت، با استفاده از Evidently دریفت را محاسبه می‌کند. نتایج در MLflow ثبت و متریک‌های Prometheus به‌روزرسانی می‌شوند. در صورت تشخیص دریفت، یک هشدار در لاگ ثبت می‌شود.                                                                       |
| `expire_old_pending_records` | هر روز       | ۸۶۴۰۰ ثانیه | `days=30`                          | `{expired_count}`                           | این وظیفه برای مدیریت حجم صف بازآموزی و جلوگیری از رشد نامحدود آن طراحی شده است. رکوردهای معلق (Pending) که بیش از ۳۰ روز پیش ثبت شده‌اند و هنوز برچسب (Label) دریافت نکرده‌اند را حذف می‌کند. این کار باعث می‌شود صف فقط حاوی داده‌های نسبتاً جدید باشد و کیفیت داده‌های آموزشی کاهش نیابد.                                                                                                                                                |
| `batch_predict`              | ندارد (دستی) | -           | `data` (لیست رکوردها)، `batch_id`  | `{summary, results}`                        | این وظیفه پیش‌بینی دسته‌جمعی را به صورت غیرهمزمان پردازش می‌کند. مدل و ستون‌های ویژگی را در حافظه کارگر کش می‌کند تا از بارگذاری مجدد برای درخواست‌های بعدی جلوگیری شود. هر رکورد به صورت جداگانه پردازش شده و نتیجه در لیست `results` ذخیره می‌شود. خلاصه آماری (تعداد خروج، نرخ خروج، میانگین احتمال) محاسبه می‌شود. نتایج به صورت Pickle در Redis با کلید `batch_results:{batch_id}` ذخیره شده و به مدت ۲۴ ساعت معتبر می‌مانند.            |

---

## 1. Introduction

#### 1.1 Purpose
This document specifies the functional and non-functional requirements for the **MLOps Churn Prediction Platform**. The platform enables data science and ML engineering teams to train, track, deploy, monitor, and manage automated retraining of machine learning models in a production-grade environment. All requirements are strictly aligned with the current implemented codebase. Version 4.0.0 introduces significant improvements in model-version-aware feature caching, Redis-driven drift detection, role-based rate limiting, and comprehensive innovation documentation.

#### 1.2 Scope
The system encompasses the following subsystems:
- Data ingestion, validation, and preprocessing with one-hot encoding and missing value management
- Training and hyperparameter optimization of a Random Forest classifier using Optuna
- Experiment tracking, artifact logging, and model registry management via MLflow
- Distributed feature caching (Redis) with MD5 hashing, model version awareness, dynamic TTL, and graceful degradation
- Real-time (single) and batch prediction serving via a RESTful API (FastAPI)
- Intelligent retraining queue: automatic prediction logging to Redis, priority-based batch extraction, and pre-deployment model performance comparison
- Asynchronous retraining and batch prediction via Celery workers with in-memory model/column caching
- Automatic data drift detection using Evidently library and real production data from Redis
- Full observability stack (Prometheus, Grafana, Loki, Fluent-bit) with structured asynchronous JSON logging
- API key-based authentication with three user roles and role-based rate limiting
- Containerized deployment with dependency management, Nginx reverse proxy, and cross-platform Docker/Podman support

#### 1.3 Definitions and Acronyms
| Term          | Meaning                                                                            |
| ------------- | ---------------------------------------------------------------------------------- |
| MLOps         | Machine Learning Operations (lifecycle management)                                 |
| MLflow        | Open-source platform for experiment tracking, model registry, and artifact storage |
| Optuna        | Hyperparameter optimization framework using TPE Sampler                            |
| Celery        | Distributed task queue for asynchronous execution                                  |
| Redis         | Distributed cache and message broker                                               |
| Prometheus    | Time-series metrics collection and query engine                                    |
| Grafana       | Visualization platform for dashboards and log exploration                          |
| Loki          | Log aggregation and indexing system                                                |
| Fluent-bit    | Lightweight log forwarder with async HTTP delivery                                 |
| Garage        | S3-compatible object storage for model artifacts                                   |
| Feature Cache | MD5 hash and model version-based preprocessing storage mechanism                   |
| Data Drift    | Statistical distribution change in input data compared to training data            |

---

### 2. Overall Description

#### 2.1 Product Perspective
The platform is a self-contained microservice architecture orchestrated via Docker Compose / Podman Compose. Initial training data is sourced from `data/churn.csv`, with extensibility for external data streams or cloud sources. All configurations are externalized, and the system is optimized for reproducible deployment on any container host. Compared to international competitors like Kubeflow, SageMaker, and Vertex AI, this platform delivers an 80% infrastructure cost reduction and sub-30-minute deployment time through model-version-aware caching, Redis-driven drift detection, and automated pre-deployment model comparison.

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
- Preprocessing includes dropping `customerID` column if present, numeric conversion of `TotalCharges`, dropping rows with missing values, one-hot encoding categorical variables (`Contract`, `InternetService`, `PaymentMethod`), and mapping `Churn` to `{Yes:1, No:0}`.
- Data is split 80/20 with stratified sampling (`stratify=y`) into training and test sets.
- All preprocessing steps are implemented in the `FeatureStore` class in `shared/feature_store.py` and work identically for both training and inference.

**Feature Cache**
- The system shall store preprocessed features in Redis using the key format `features:{md5_hash}:v{model_version}`.
- The MD5 hash is computed from sorted JSON content of the input DataFrame.
- Default TTL is 3600 seconds, configurable via `CACHE_TTL_SECONDS`.
- Cached values are stored in Pickle format (not JSON) for faster loading.
- On cache hit, the preprocessing step is bypassed.
- On Redis unavailability, the system operates in graceful degradation mode and computes features locally.
- Cache statistics (hits, misses, hit rate, writes) are exposed via `/api/monitoring/cache/stats`.
- Forced cache invalidation is available via `DELETE /api/monitoring/cache`.
- On model promotion to Production, `clear_cache_for_model_version(version_old)` is called to clear the old version's cache, preventing unlimited key growth.

**Model Training and Hyperparameter Optimization**
- The system shall train a `RandomForestClassifier` using Optuna.
- Optimization runs 15 trials with 5-fold cross-validation, maximizing `roc_auc`.
- Tunable hyperparameters: `n_estimators` (50–200), `max_depth` (3–10), `min_samples_split` (2–8).
- The unified `train.py` pipeline first attempts to load labeled data from the Redis retrain queue. If empty, it falls back to `churn.csv`.
- Before promotion to Production, the system automatically compares new model metrics (`auc`, `accuracy`, `f1`) against the active Production version. Promotion occurs only if the new model performs equal or better on at least one metric; otherwise, the version is archived.
- Upon successful promotion, the Redis retrain queue is cleared.

**Experiment Tracking and Model Management**
- All runs are logged to MLflow: parameters, metrics, and artifacts (`model.pkl`, `columns.pkl`, `feature_importance.json`).
- The best model is registered in the `churn_model` registry and promoted to `Production` after successful training.
- The API provides endpoints for retrieving the active model, listing all versions, comparing performance, and manual deployment (`/api/models/deploy`).

**Inference API (FastAPI)**
- Core endpoints:
  - `POST /api/predictions/single`: Returns `prediction`, `probability`, `confidence`, `model_version`, `prediction_id`.
  - `POST /api/predictions/batch`: Accepts up to 10,000 records, returns a `batch_id`.
  - `GET /api/predictions/batch/{batch_id}/status`: Tracks job progress.
  - `GET /api/predictions/batch/{batch_id}/results`: Retrieves results and statistical summary.
  - `POST /api/feedback/{prediction_id}`: Submits actual label for a previous prediction.
  - `POST /api/predictions/collect-training-data`: Manually submits labeled training data without prior prediction.
  - `GET /api/health`: Service and dependency health check.
  - `GET /api/monitoring/prediction-stats`: Real-time prediction statistics from Redis.
  - `GET /api/docs`: Interactive Swagger/OpenAPI documentation.
- The API loads the Production model from MLflow at startup.
- Cache is checked before each prediction; computed features are cached afterward using the active model version.
- Every successful prediction is automatically logged to the `RetrainQueueManager` with `pending` status for future training.

**Asynchronous Retraining and Batch Prediction**
- Retraining is triggered via `POST /api/retrain` and dispatched to Celery. Status is trackable at `/api/retrain/{task_id}/status`.
- The retraining task executes the full pipeline, performs model comparison, and clears the training queue upon success.
- Batch prediction runs inside a Celery worker. The model and feature columns are cached in worker memory to prevent repeated I/O.
- Batch results are stored in Pickle format in Redis for 24 hours (86,400 seconds) and retrievable via `batch_id`.

**Automatic Drift Detection**
- The system shall implement a periodic Celery task named `periodic_drift_check` that runs every hour by default.
- The task shall read predictions from the last 24 hours from the Redis retrain queue using the `get_recent_predictions` method.
- If the number of samples is less than 100, the task shall exit with `skipped` status.
- With sufficient samples, the system shall compute drift using Evidently library with `DataDriftPreset`, comparing current data against reference data loaded from `churn.csv`.
- The system shall extract `dataset_drift` status and the list of drifted columns.
- Results shall be logged to MLflow as a separate run named `auto_drift_check`.
- The HTML drift report and drifted columns list shall be saved as artifacts in MLflow.
- Prometheus metrics `dataset_drift` and `drifted_columns_count` shall be updated.
- On drift detection, a structured warning log shall be recorded (queryable via Loki).

**Model Artifact Storage**
- Artifacts (model, column mappings, feature importance plots) are stored in the `mlflow` bucket on Garage (S3-compatible).
- Metadata (parameters, metrics, tags, run info) is persisted in PostgreSQL.
- Credentials are injected exclusively via environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
- The `garage-setup.sh` script automatically initializes the node, creates API keys, and sets up the `mlflow` bucket.

**Monitoring and Observability**
- Prometheus scrapes API metrics (`api_requests_total`, `api_request_duration_seconds`) and Python process metrics every 15 seconds.
- Application logs are generated in structured JSON format and sent asynchronously via HTTP to Fluent-bit, which forwards them to Loki.
- Grafana provides dashboards connected to Prometheus and Loki, including four main dashboards: API Performance, Model Performance, System Health, and Log Explorer.
- The `/api/monitoring/health/system` endpoint reports system health (CPU, RAM, Disk, and connections to MLflow, PostgreSQL, Redis).
- Every service automatically injects its name into all log records via `LoggerAdapter`.

**Reverse Proxy and Routing**
- Nginx routes: `/api/*` → API, `/mlflow/*` → MLflow, `/prometheus/*` → Prometheus, `/grafana/*` → Grafana.
- Supports WebSocket and correctly forwards `X-Real-IP`, `X-Forwarded-For`, and sub-path headers.
- HTTP to HTTPS redirection is configurable for production environments.

#### 3.2 Non-Functional Requirements

**Performance**
- Single prediction endpoint response time shall be < 500ms under normal load.
- The system shall handle ≥ 10 concurrent inference requests without degradation.
- Feature cache hit rate shall be ≥ 30% under typical load, calculated as `total_hits / (total_hits + total_misses)`.
- If the cache hit rate drops below 10%, an alert shall be generated (configurable in Grafana).

**Availability**
- Core services shall achieve 99% uptime in production-like environments.
- Healthchecks (`pg_isready`, `redis-cli ping`, `curl /health`) automatically restart unhealthy containers.

**Security**
- All sensitive data (DB passwords, S3 keys) must be passed via environment variables. Hardcoding is prohibited.
- The reverse proxy shall redirect unencrypted traffic to TLS in production.
- Default passwords for Grafana and Garage must be customizable via `.env`.

**Authentication & Authorization**
- The system shall support API key-based authentication using the `X-API-Key` header.
- Three user roles shall be defined: `admin` (full access including model deployment), `user` (read and write including predictions and feedback), `readonly` (read only including status and metrics).
- Public endpoints (health, docs, metrics) shall not require authentication.
- Prediction and status endpoints require `read` permission.
- Batch submission, training data collection, and feedback endpoints require `write` permission.
- Model retraining endpoint requires `retrain` permission.
- Model deployment endpoint requires `admin` permission.

**Rate Limiting**
- The system shall implement Redis-backed rate limiting using a sliding window algorithm, which is more accurate than fixed window and avoids boundary burst phenomenon.
- Rate limits shall be role-based: admin (1000 requests/minute), user (100 requests/minute), readonly (50 requests/minute), anonymous (10 requests/minute).
- Rate data shall be stored in Redis Sorted Sets with key pattern `rate_limit:{role}:{identifier}`.
- When the rate limit is exceeded, the system shall return HTTP 429 with headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After`.
- When Redis is unavailable, the system shall operate in fail-open mode and accept requests (Availability over Correctness).

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
- **Grafana UI:** System/model metrics dashboards and LogQL log exploration with four pre-provisioned dashboards.
- **Swagger UI (`/api/docs`):** Interactive API testing and OpenAPI schema viewing.
- **Prometheus UI:** Time-series metric querying and target status monitoring.

#### 4.2 Hardware Interfaces
- None (fully virtualized and hardware-agnostic).

#### 4.3 Software Interfaces
| Component   | Protocol/Port          | Role                                                                              |
| ----------- | ---------------------- | --------------------------------------------------------------------------------- |
| PostgreSQL  | TCP/5432               | MLflow metadata storage                                                           |
| Redis       | TCP/6379               | Celery broker, model-version-aware feature cache, prediction stats, retrain queue |
| Garage (S3) | TCP/3900               | Model artifact storage (model.pkl, columns.pkl, feature_importance.json)          |
| Prometheus  | TCP/9090               | Metric collection and querying (scrapes API every 15 seconds)                     |
| Loki        | TCP/3100               | Log aggregation and indexing                                                      |
| Fluent-bit  | TCP/8888 (input)       | Async JSON log receiver → Loki forwarder                                          |
| Nginx       | TCP/80 (external 8080) | Edge reverse proxy and path-based routing                                         |

---

### 5. System Architecture
The architecture follows a containerized microservices pattern:
1. **Edge Layer:** Nginx reverse proxy for path-based routing (`/api/*`, `/mlflow/*`, `/prometheus/*`, `/grafana/*`), header forwarding, and WebSocket support (for Grafana).
2. **Inference Service (Stateless):** FastAPI for real-time predictions, model-version-aware feature cache management, automatic prediction logging to retrain queue, role-based rate limiting, and Prometheus metric exposure.
3. **Async Worker (Celery):** Handles retraining (loading data from Redis or CSV, optimization, comparison, promotion), batch prediction (with in-memory model/column caching), automatic drift detection (periodic every hour), and expiration of old pending records.
4. **Stateful Backends:** PostgreSQL (MLflow metadata), Redis (Celery broker, model-version-aware feature cache with key format `features:{hash}:v{version}`, retrain queue with key `retrain:training_data`, prediction statistics), Garage S3 (model artifacts), MLflow (model registry and tracking UI).
5. **Observability Stack:** Fluent-bit (collects JSON logs via HTTP on port 8888) → Loki (storage and indexing) + Prometheus (scrapes API metrics every 15 seconds) → Grafana (visualizes four pre-provisioned dashboards).
6. **Orchestration & Tooling:** `Makefile` for lifecycle management with commands `make up`, `make down`, `make build-base`, `make test`; `garage-setup.sh` for automated S3 initialization (node creation, API key generation, mlflow bucket setup).

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
| `RATE_LIMIT_ENABLED`                                   | Enable/disable rate limiting       | `true`                              |
| `RATE_LIMIT_ADMIN`, `USER`, `READONLY`, `ANONYMOUS`    | Request limits per role            | 1000, 100, 50, 10                   |
| `API_KEY_ADMIN`, `API_KEY_USER`, `API_KEY_READONLY`    | API keys for authentication roles  | Configurable in `.env`              |
| `CACHE_TTL_SECONDS`                                    | Feature cache TTL (seconds)        | 3600                                |

#### Appendix B: Training Pipeline Detail
1. Load data from Redis retrain queue (fallback to `churn.csv` if empty).
2. Preprocess features (one-hot encoding, missing value handling, target mapping).
3. Split data 80/20 with stratified sampling.
4. Optimize hyperparameters via Optuna (15 trials, 5-fold CV, maximize ROC-AUC).
5. Train final Random Forest model with best parameters.
6. Evaluate metrics (accuracy, precision, recall, F1, AUC).
7. Log to MLflow (parameters, metrics, artifacts including model, `columns.pkl`, and `feature_importance.json`).
8. **Automatic comparison** with current Production version on `auc`, `accuracy`, `f1` metrics.
9. Register model and promote to Production if performance is better or equal on at least one metric; otherwise archive.
10. Automatically clear the Redis retrain queue upon successful promotion.

#### Appendix C: Feature Cache Mechanism Detail
1. Receive customer input data as JSON.
2. Generate unique MD5 hash from sorted JSON column content.
3. Query Redis with key `features:{hash}:v{model_version}`.
4. Cache Hit: Retrieve features via Pickle deserialization, skip preprocessing.
5. Cache Miss: Compute features via `FeatureStore.prepare()` pipeline.
6. Store computed features in Redis using `SETEX` with default TTL 3600s and Pickle format.
7. Update cache statistics (`cache_total_hits`, `cache_total_misses`, `cache_total_writes`).
8. Graceful degradation: Continue operation locally if Redis is unreachable.
9. Manual cache clearing supported via `DELETE /api/monitoring/cache`.
10. On model promotion, `clear_cache_for_model_version(version_old)` removes old version cache entries.

#### Appendix D: Value Proposition & Innovation

##### Competitive Landscape
In the digital transformation era, organizations are compelled to use artificial intelligence and machine learning to maintain their competitive advantage. However, the main challenge is not building the model, but maintaining and operationalizing it in production. Statistics show that over 85% of machine learning projects never reach production, and of those that do, about 60% are retired within six months due to data quality degradation or lack of proper monitoring.

##### The Three Main Challenges in Traditional MLOps
**Challenge One: Infrastructure Complexity** - Existing solutions like Kubeflow, SageMaker, and Vertex AI require Kubernetes clusters with at least three nodes. The maintenance cost and technical expertise required are prohibitive for many organizations.

**Challenge Two: Lack of Production Visibility** - Many organizations only monitor error logs after deployment, leaving fundamental questions unanswered: Has data drift occurred? Is the model still accurate? When should retraining be triggered?

**Challenge Three: Inefficient Retraining** - In most systems, retraining is either manual (with delay) or periodic (without regard to actual need), wasting computational resources and sometimes replacing a better model with a worse one.

##### Key Innovations

**Innovation One: Model-Version-Aware Feature Cache** - With cache key design `features:{hash}:v{model_version}`, the old model's cache remains valid until its natural TTL expiration. At the moment of model promotion, the cache hit rate does not suddenly collapse.

**Innovation Two: Redis-Driven Drift Detection** - The platform consumes data directly from the retrain queue, which originates from actual predictions and reflects real production data distribution. Drift detection runs automatically every hour with results logged to MLflow.

**Innovation Three: Pre-Deployment Model Comparison** - Before any promotion, the system compares new model metrics (AUC, Accuracy, F1) with the current Production model. Promotion only occurs if the new model outperforms the current one on at least one metric.

**Innovation Four: Non-Intrusive Retrain Queue** - Using simple `RPUSH` operations in Redis and performing heavy processing outside the main prediction path, queue logging typically takes less than 1 millisecond.

**Innovation Five: Unified Observability Stack** - Prometheus, Loki, and Grafana are unified into a single stack with structured JSON logging, custom metrics (drift rate, retrain queue length, cache hit rate), and four pre-provisioned dashboards.

##### Comparison Table with International Competitors

| Feature              | Kubeflow                         | SageMaker            | Vertex AI     | This Platform                     |
| -------------------- | -------------------------------- | -------------------- | ------------- | --------------------------------- |
| Infrastructure Cost  | High (cluster required)          | High (pay-per-use)   | High          | Low (4GB RAM, 2 cores)            |
| Setup Time           | Hours to days                    | Hours                | Hours         | < 30 minutes                      |
| Feature Cache        | Requires Feast                   | Built-in but limited | Built-in      | Redis + model version + Pickle    |
| Drift Detection      | Requires separate tool           | Paid                 | Paid          | Integrated (Evidently) + free     |
| Automatic Retraining | Requires Argo/Kubeflow Pipelines | Yes                  | Yes           | Celery + auto metric comparison   |
| Observability        | Requires log separation          | CloudWatch           | Cloud Logging | Unified (Loki+Grafana+Prometheus) |
| Cloud Dependency     | No (on-prem capable)             | Yes (AWS)            | Yes (GCP)     | No (run anywhere)                 |
| Documentation & API  | Good                             | Excellent            | Excellent     | Complete + OpenAPI (Swagger)      |
| Open Source          | Yes                              | No                   | No            | Yes (complete)                    |

##### Why Should Customers Choose This Platform?

**Reason One: 80% Infrastructure Cost Reduction** - The platform runs on a virtual server with 4GB RAM and 2 CPU cores, compared to Kubeflow requiring at least 8GB RAM and 4 cores.

**Reason Two: Implementation Time Under 30 Minutes** - A single `make up` command starts all services (PostgreSQL, Redis, Garage, MLflow, API, Worker, Prometheus, Loki, Fluent-bit, Grafana, Nginx). No manual Kubernetes, IAM Roles, VPC, or Load Balancer configuration is required.

**Reason Three: Portability and Cloud Independence** - The platform is not tied to any specific cloud provider. It runs on on-premise infrastructure, any cloud provider (AWS, GCP, Azure, DigitalOcean, Hetzner), or even a developer's laptop.

**Reason Four: Production-Ready** - All services feature Health Checks (automatic restart on failure), Retry Policies (handling transient errors), Graceful Degradation (reduced capability on dependent service failure), and structured logging (easy troubleshooting).

**Reason Five: Complete Documentation and Standard API** - All API endpoints have OpenAPI (Swagger) documentation and work with standard tools like Postman, curl, and auto-generated code.

**Reason Six: Support for Real Business Scenarios** - Real-time single prediction, batch prediction for mass customer processing, and historical data collection for model improvement.

---

#### Appendix E: Celery Tasks Detailed Description

| Task Name                    | Cron Schedule | Default Interval | Input                                | Output                                      | Description                                                                                                                                                                                                                                                          |
| ---------------------------- | ------------- | ---------------- | ------------------------------------ | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `retrain`                    | None (manual) | -                | request task_id                      | `{status, version, metrics, run_id}`        | Core retraining task. Loads labeled data from Redis (fallback to CSV), executes full training pipeline (optimization, training, evaluation, MLflow logging), compares metrics with Production, promotes if improved, clears old cache, and purges the retrain queue. |
| `periodic_drift_check`       | Every hour    | 3600 seconds     | `hours_back=24`, `min_samples=100`   | `{dataset_drift, drifted_columns, samples}` | Reads recent predictions from Redis retrain queue, computes drift using Evidently, logs results to MLflow, updates Prometheus metrics, and logs warnings on drift detection.                                                                                         |
| `expire_old_pending_records` | Every day     | 86400 seconds    | `days=30`                            | `{expired_count}`                           | Removes pending records without labels older than 30 days from the retrain queue to prevent unbounded queue growth.                                                                                                                                                  |
| `batch_predict`              | None (manual) | -                | `data` (list of records), `batch_id` | `{summary, results}`                        | Processes batch predictions asynchronously. Caches model and columns in worker memory, processes each record individually, computes statistical summaries, and stores results in Pickle format in Redis with 24-hour TTL.                                            |
