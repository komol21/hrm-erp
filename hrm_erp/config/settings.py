"""
Django settings for HRM ERP project.
Production-ready configuration for Render deployment.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# BASE DIRECTORY
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
# Load local .env file (Render uses its own environment variables)
load_dotenv(BASE_DIR / '.env')

# ============================================================
# SECURITY SETTINGS
# ============================================================
# Secret Key
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-development-key-change-this'
)

# Debug Mode
DEBUG = os.getenv(
    'DEBUG',
    'True'
).lower() in ('true', '1', 'yes')

# Allowed Hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,.onrender.com'
    ).split(',')
    if host.strip()
]

# ============================================================
# CSRF SETTINGS
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # Render deployment
    'https://*.onrender.com',
]

# ============================================================
# APPLICATION DEFINITION
# ============================================================
INSTALLED_APPS = [
    # Django Default Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # HRM Apps
    'apps.accounts',
    'apps.organization',
    'apps.employees',
    'apps.attendance',
    'apps.leave_management',
    'apps.payroll',
    'apps.recruitment',
    'apps.assistant',
]

# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    # Django Security
    'django.middleware.security.SecurityMiddleware',

    # WhiteNoise for Static Files
    'whitenoise.middleware.WhiteNoiseMiddleware',

    # Django Middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Custom Middleware
    'apps.accounts.middleware.RoleMiddleware',
]

# ============================================================
# URL CONFIGURATION
# ============================================================
ROOT_URLCONF = 'config.urls'

# ============================================================
# TEMPLATE CONFIGURATION
# ============================================================
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
                'apps.accounts.context_processors.role_context',
            ],
        },
    },
]

# ============================================================
# WSGI CONFIGURATION
# ============================================================
WSGI_APPLICATION = 'config.wsgi.application'

# ============================================================
# DATABASE
# ============================================================
# SQLite Database
# Suitable for Demo / Assignment Deployment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# CUSTOM USER MODEL
# ============================================================
AUTH_USER_MODEL = 'accounts.User'

# ============================================================
# PASSWORD VALIDATION
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC FILES
# ============================================================
STATIC_URL = '/static/'

# Project Static Folder
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Static Files Collected by collectstatic
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise Static File Storage
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# ============================================================
# MEDIA FILES
# ============================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# LOGIN / LOGOUT
# ============================================================
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ============================================================
# SESSION SETTINGS
# ============================================================
# Session Duration: 24 Hours
SESSION_COOKIE_AGE = 86400

# Refresh Session on Every Request
SESSION_SAVE_EVERY_REQUEST = True

# ============================================================
# FILE UPLOAD LIMITS
# ============================================================
# Maximum File Upload Size: 2MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# Maximum Request Data Size: 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ============================================================
# EMAIL CONFIGURATION
# ============================================================
# Development Console Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'HRM ERP Portal <noreply@hrm.local>'

# ============================================================
# OPENAI CONFIGURATION
# ============================================================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# ============================================================
# GOOGLE GEMINI CONFIGURATION
# ============================================================
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

# ============================================================
# FIREBASE CONFIGURATION
# ============================================================
FIREBASE_SERVICE_ACCOUNT_KEY = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', '')

# ============================================================
# PRODUCTION SECURITY SETTINGS
# ============================================================
# Enable these only when DEBUG=False
if not DEBUG:
    # Secure Cookies over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Prevent MIME Type Sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Prevent Clickjacking
    X_FRAME_OPTIONS = 'DENY'

    # Secure Referrer Policy
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
