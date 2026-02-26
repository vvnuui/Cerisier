import os
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "django_filters",
    # Local apps
    "apps.users",
    "apps.blog",
    "apps.quant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="cerisier"),
        "USER": config("POSTGRES_USER", default="cerisier"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="devpassword"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Shanghai"

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    "sync-stock-list-daily": {
        "task": "quant.sync_stock_list",
        "schedule": crontab(hour=9, minute=0),
    },
    "sync-daily-kline": {
        "task": "quant.sync_daily_kline",
        "schedule": crontab(hour=16, minute=0),
    },
    "sync-money-flow": {
        "task": "quant.sync_money_flow",
        "schedule": crontab(hour=16, minute=30),
    },
    "sync-margin-data": {
        "task": "quant.sync_margin_data",
        "schedule": crontab(hour=17, minute=0),
    },
    "sync-news-hourly": {
        "task": "quant.sync_news",
        "schedule": crontab(minute=0, hour="9-18"),
    },
    "sync-financial-reports-weekly": {
        "task": "quant.sync_financial_reports",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3am
    },
    "validate-data-daily": {
        "task": "quant.validate_data",
        "schedule": crontab(hour=2, minute=0),
    },
    "run-analysis-pipeline": {
        "task": "quant.run_analysis_pipeline",
        "schedule": crontab(hour=17, minute=30),
        "kwargs": {"style": "swing"},
    },
}

# AI Service
DEEPSEEK_API_KEY = config("DEEPSEEK_API_KEY", default="")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
AI_DAILY_BUDGET = config("AI_DAILY_BUDGET", default=5.0, cast=float)
