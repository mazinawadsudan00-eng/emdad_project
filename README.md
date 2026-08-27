# منصة إمداد الرقمية — نظام إدارة المخزون والتحليل المرئي
### دراسة حالة: مجمع نابلس للغاز

مشروع Django كامل (واجهة أمامية + خلفية + قاعدة بيانات) ينفّذ المتطلبات الوظيفية
وغير الوظيفية الواردة في وثيقة البحث المرفقة (الفصل الثالث)، ويعيد استخدام
تصاميم الواجهات الخمس التي زوّدتني بها (login / mainboard / sales / customer /
inventory) كقوالب Django حقيقية مربوطة بقاعدة بيانات فعلية.

---

## 1. المتطلبات قبل التشغيل

- Python 3.11 أو أحدث (تم بناء المشروع وفق Python 3.13 المذكور في أدوات البحث).
- pip
- اتصال إنترنت عند أول تشغيل (لتحميل Bootstrap / Chart.js من CDN، ولتثبيت Django).

## 2. خطوات التشغيل (خطوة بخطوة)

```bash
# 1) إنشاء بيئة افتراضية (موصى به)
python -m venv venv
source venv/bin/activate        # على ويندوز: venv\Scripts\activate

# 2) تثبيت المتطلبات
pip install -r requirements.txt

# 3) تجهيز قاعدة البيانات (SQLite افتراضياً - لا يحتاج أي إعداد إضافي)
python manage.py migrate

# 4) تعبئة بيانات تجريبية (مستخدمون + أصناف + مخزون + فواتير) تطابق التصاميم الأصلية
python manage.py seed_demo

# 5) تشغيل الخادم المحلي
python manage.py runserver
```

افتح المتصفح على: **http://127.0.0.1:8000/**

## 3. بيانات الدخول التجريبية (بعد تشغيل seed_demo)

| الدور | اسم المستخدم | كلمة المرور | الصلاحيات |
|---|---|---|---|
| مدير النظام | `admin` | `Admin@2026` | كل الصفحات + لوحة إدارة Django (`/admin/`) لإدارة المستخدمين والصلاحيات |
| أمين المخزن | `warehouse1` | `Warehouse@2026` | المخزون (إضافة شحنات، تعديل، فرز للصيانة) |
| موظف المبيعات | `sales1` | `Sales@2026` | إصدار فواتير البيع |
| المحاسب | `accountant1` | `Account@2026` | العملاء/الموردين، تسوية الحسابات، التقارير |

> **مهم أمنياً:** غيّر هذه الكلمات فوراً بعد أول تسجيل دخول عبر صفحة تغيير كلمة
> المرور في `/admin/`، خصوصاً قبل أي عرض أو نشر فعلي للمشروع.

## 4. التبديل إلى PostgreSQL أو MySQL

المشروع يستخدم SQLite افتراضياً لتسهيل التشغيل والتسليم دون إعداد خادم قاعدة
بيانات منفصل. للتبديل إلى ما هو مذكور في أدوات البحث (PostgreSQL/MySQL)، عرّف
متغيرات البيئة التالية قبل تشغيل `migrate`:

```bash
# مثال PostgreSQL
export DJANGO_DB_ENGINE=django.db.backends.postgresql
export DJANGO_DB_NAME=emdad_db
export DJANGO_DB_USER=postgres
export DJANGO_DB_PASSWORD=your_password
export DJANGO_DB_HOST=127.0.0.1
export DJANGO_DB_PORT=5432
pip install psycopg2-binary
python manage.py migrate
python manage.py seed_demo
```

نفس الفكرة لـ MySQL مع `DJANGO_DB_ENGINE=django.db.backends.mysql` وتثبيت
`mysqlclient`.

## 5. بنية المشروع

```
emdad_project/
├── manage.py
├── requirements.txt
├── emdad/                 # إعدادات المشروع (settings, urls رئيسية)
├── core/                  # التطبيق الوحيد: النماذج، الفورمز، الفيوز، الأدمن
│   ├── models.py          # User, Account, Product, StockItem, Purchase, Sale, SaleItem, StockMovement
│   ├── forms.py
│   ├── views.py           # كل منطق الأعمال (تسجيل دخول، مبيعات، مخزون، عملاء، تقارير)
│   ├── decorators.py       # role_required: تقييد الوصول حسب الصلاحية
│   ├── context_processors.py
│   ├── admin.py           # يفعّل /admin/ لإدارة المستخدمين والبيانات مباشرة
│   ├── migrations/
│   └── management/commands/seed_demo.py
└── templates/
    ├── base.html          # القالب الأساسي (الشريط الجانبي) المشترك بين كل الصفحات
    ├── login.html
    ├── dashboard/dashboard.html
    ├── dashboard/reports.html
    ├── inventory/inventory.html
    ├── sales/sales.html
    └── partners/customers.html
```

## 6. ربط المتطلبات الوظيفية بالتنفيذ الفعلي

| المتطلب (الفصل الثالث، 3-7) | أين نُفّذ |
|---|---|
| تسجيل دخول المستخدمين | `core/views.py::EmdadLoginView` + `templates/login.html` |
| إدارة صلاحيات المستخدمين (للمدير فقط) | نموذج `User.role` + لوحة `/admin/` (تظهر فقط للمدير في الشريط الجانبي) |
| تسجيل شحنات الغاز الواردة | `add_stock` + نموذج `Purchase` + تحديث `StockItem` تلقائياً |
| إدارة المخزون / متابعة الكميات | `inventory_list`, `edit_stock_item`, `send_to_maintenance` |
| تنفيذ عمليات البيع والصرف | `sales_page` — يتحقق من الكمية المتاحة فعلياً قبل الحفظ، ويرفض الطلب إن لم تكفِ (تماماً كما ورد في مخطط الأنشطة 3-13) |
| إصدار الفواتير | نموذج `Sale`/`SaleItem`، ترقيم تلقائي `INV-xxxx` |
| إدارة بيانات العملاء والموردين | `customers_page` (نموذج موحّد `Account` بتصنيف: مورد/وكيل/عميل) |
| إصدار التقارير اليومية/الشهرية | `reports_page` + تصدير CSV فعلي عبر `export_sales_csv` |
| تنبيهات انخفاض المخزون | شارة حمراء في الشريط الجانبي + تنبيه أعلى لوحة التحكم، تُحسب من `min_stock_level` |
| لوحات معلومات تفاعلية | لوحة التحكم: KPIs + مخطط Chart.js (مبيعات فعلية مقابل تنبؤ بمتوسط أسي بسيط) |
| سجل كامل لكل العمليات | نموذج `StockMovement` يسجّل كل حركة وارد/صادر/صيانة |

## 7. ملاحظة حول خوارزمية "التنبؤ بالطلب" في لوحة التحكم

الخط المتقطع في مخطط لوحة التحكم يمثل تنبؤاً مبسطاً باستخدام طريقة **التمهيد
الأسي البسيط (Simple Exponential Smoothing، α=0.5)** المطبّقة على مبيعات آخر 6
أيام. هذا أسلوب إحصائي خفيف ومناسب لنطاق مشروع التخرّج، ويمكن استبداله لاحقاً
بنموذج تنبؤ أكثر تقدماً (مثل ARIMA أو نموذج تعلّم آلي) دون تعديل بقية النظام،
لأن دالة `_exponential_smoothing()` في `core/views.py` معزولة تماماً عن بقية
منطق لوحة التحكم.

## 8. تنبيه أمني قبل أي نشر فعلي (Production)

- غيّر `DJANGO_SECRET_KEY` بمفتاح جديد عشوائي.
- اضبط `DJANGO_DEBUG=False`.
- حدد `DJANGO_ALLOWED_HOSTS` بأسماء النطاقات الفعلية بدلاً من `*`.
- غيّر كل كلمات مرور المستخدمين التجريبيين.
