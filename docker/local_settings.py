import os
import datetime

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = 'django-insecure-' + secrets.token_urlsafe(50)

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database Config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'dmoj'),
        'USER': os.environ.get('MYSQL_USER', 'dmoj'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'fake_password'),
        'HOST': os.environ.get('MYSQL_HOST', '127.0.0.1'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION',
        },
    },
}

# Cấu hình cache Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'vi')
DEFAULT_USER_TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_L10N = True
USE_TZ = True

COMPRESS_OUTPUT_DIR = 'cache'
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'
STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)

DMOJ_TMP_DIR = '/tmp'

# SMTP Configuration
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '')
    SERVER_EMAIL = os.environ.get('SERVER_EMAIL', '')

STATIC_ROOT = '/app/static'
STATIC_URL = '/static/'

SITE_NAME = os.environ.get('SITE_NAME', 'FPTOJ')
SITE_LONG_NAME = os.environ.get('SITE_LONG_NAME', 'FPTOJ: FPT Online Judge')
SITE_ADMIN_EMAIL = os.environ.get('SITE_ADMIN_EMAIL', '')
TERMS_OF_SERVICE_URL = '/about/tos/'

# Cấu hình máy chấm kết nối
BRIDGED_JUDGE_ADDRESS = [('0.0.0.0', 10000)]
DMOJ_PROBLEM_DATA_ROOT = "/data/problems"

# Event Server
EVENT_DAEMON_USE = True
EVENT_DAEMON_POST = os.environ.get('EVENT_DAEMON_POST', 'ws://127.0.0.1:15102/')
EVENT_DAEMON_GET = os.environ.get('EVENT_DAEMON_GET', 'ws://localhost/event/')
EVENT_DAEMON_GET_SSL = os.environ.get('EVENT_DAEMON_GET_SSL', 'wss://localhost/event/')
EVENT_DAEMON_POLL = '/channels/'

# Celery Broker
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
# result_backend is derived from broker_url in dmoj/celery.py

ACE_URL = '//cdnjs.cloudflare.com/ajax/libs/ace/1.43.3/'
JQUERY_JS = '//cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'
SELECT2_JS_URL = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.min.js'
SELECT2_CSS_URL = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css'

TIMEZONE_MAP = 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Blue_Marble_2002.png/1024px-Blue_Marble_2002.png'

DMOJ_HTTPS = 2

# Xuất PDF
DMOJ_PDF_PDFOID_URL = os.environ.get('DMOJ_PDF_PDFOID_URL', 'http://localhost:8889')
DMOJ_PDF_PROBLEM_CACHE = '/data/pdfcache'
DMOJ_PDF_PROBLEM_INTERNAL = '/pdfcache'

DMOJ_USER_DATA_DOWNLOAD = True
DMOJ_USER_DATA_CACHE = '/data/datacache'
DMOJ_USER_DATA_INTERNAL = '/datacache'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
    },
    'handlers': {
        'bridge': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/web.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'file',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'file',
        },
    },
    'loggers': {
        'judge.bridge': {
            'handlers': ['bridge'],
            'level': 'INFO',
            'propagate': True,
        },
        '': {
            'handlers': ['console'],
        },
    },
}

# Social Auth keys
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')
SOCIAL_AUTH_GITHUB_SECURE_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_SECURE_KEY', '')
SOCIAL_AUTH_GITHUB_SECURE_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECURE_SECRET', '')

# Turnstile site key
TURNSTILE_SITEKEY = os.environ.get('TURNSTILE_SITEKEY', '') or None
TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET', '') or None
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
LOGIN_URL = '/accounts/login/'
