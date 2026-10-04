"""
إعدادات مشروع منصة إمداد الرقمية - نظام إدارة المخزون والتحليل المرئي
مجمع نابلس للغاز
"""
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# أمان المشروع
# ============================================================
# ملاحظة: قبل النشر الفعلي (Production) يجب استبدال المفتاح التالي
# بمفتاح سري جديد وتفعيل DEBUG=False وضبط ALLOWED_HOSTS.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-emdad-gas-platform-change-this-key-before-production'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# ============================================================
# التطبيقات المثبتة
# ============================================================
INSTALLED_APPS = [
    'jazzmin',                  # تم إضافة جازمن في المقدمة لتطبيق التنسيقات على لوحة الإدارة
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',   # لتنسيق الأرقام والتواريخ بصورة مقروءة
    'core',
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'emdad.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.low_stock_alerts',
            ],
        },
    },
]

WSGI_APPLICATION = 'emdad.wsgi.application'
ASGI_APPLICATION = 'emdad.asgi.application'

# ============================================================
# قاعدة البيانات
# ============================================================
DB_ENGINE = os.environ.get('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DJANGO_DB_NAME', 'emdad_db'),
            'USER': os.environ.get('DJANGO_DB_USER', 'root'),
            'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', ''),
            'HOST': os.environ.get('DJANGO_DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        }
    }

# ============================================================
# المستخدم المخصص
# ============================================================
AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ============================================================
# اللغة والمنطقة الزمنية
# ============================================================
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Khartoum'
USE_I18N = True
USE_TZ = True

# ============================================================
# الملفات الثابتة
# ============================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_TAGS = {
    10: 'info', 20: 'info', 25: 'success', 30: 'warning', 40: 'danger',
}

# ============================================================
# إعدادات Django Jazzmin - لوحة تحكم إمداد الاحترافية
# ============================================================
JAZZMIN_SETTINGS = {
    # النصوص والعناوين الرئيسيّة
    "site_title": "إمداد | لوحة النظام",
    "site_header": "منصة إمداد الرقمية",
    "site_brand": "منصة إمداد",
    "welcome_sign": "مرحباً بك في لوحة إدارة منصة إمداد - مجمع نابلس للغاز",
    "copyright": "منصة إمداد الرقمية © 2026",

    # الشعار ورابط العودة للواجهة الرئيسيّة
    "site_logo_classes": "img-circle",
    "user_avatar": None,
    "topmenu_links": [
        {"name": "لوحة التحكم الرئيسية", "url": "dashboard", "permissions": ["auth.view_user"]},
        {"name": "التقارير", "url": "reports_page", "permissions": ["auth.view_user"]},
    ],

    # خيارات القائمة الجانبية
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],

    # أيقونات الأقسام والنماذج (FontAwesome)
    "icons": {
        "auth": "fas fa-users-cog",
        "core.User": "fas fa-user-shield",
        "core.Group": "fas fa-users",
        "core.Product": "fas fa-gas-cylinder",
        "core.StockMovement": "fas fa-exchange-alt",
        "core.Inventory": "fas fa-boxes",
        "core.Supplier": "fas fa-truck-loading",
        "core.Customer": "fas fa-user-tie",
        "core.Sale": "fas fa-file-invoice-dollar",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",

    # تخصيص النموذج والشكل
    "related_modal_active": True,
    "custom_css": None,
    "custom_js": None,
    "use_google_fonts_rosettagothic": True,
    "show_ui_builder": False,
}

# تخصيص ألوان الهوية البصرية لمنصة إمداد
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark bg-primary",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}