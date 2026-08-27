"""
إعدادات مشروع منصة إمداد الرقمية - نظام إدارة المخزون والتحليل المرئي
مجمع نابلس للغاز
"""
import os
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
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
# افتراضياً يستخدم المشروع SQLite لتسهيل التشغيل المباشر والتسليم.
# بحسب أدوات البحث (الفصل الأول - 1-8) يمكن التحول إلى PostgreSQL أو MySQL
# بضبط متغيرات البيئة التالية، مثال لـ MySQL:
#
#   DJANGO_DB_ENGINE=django.db.backends.mysql
#   DJANGO_DB_NAME=emdad_db
#   DJANGO_DB_USER=root
#   DJANGO_DB_PASSWORD=your_password
#   DJANGO_DB_HOST=127.0.0.1
#   DJANGO_DB_PORT=3306
#
# ولاستخدام PostgreSQL غيّر DJANGO_DB_ENGINE إلى:
#   django.db.backends.postgresql
#
# ولا تنسَ تثبيت مشغّل قاعدة البيانات المناسب (راجع requirements.txt).
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_TAGS = {
    10: 'info', 20: 'info', 25: 'success', 30: 'warning', 40: 'danger',
}
