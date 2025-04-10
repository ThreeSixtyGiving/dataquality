from cove import settings
from lib360dataquality.cove.settings import COVE_CONFIG
import os
import environ

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env(  # set default values and casting
    DB_NAME=(str, os.path.join(BASE_DIR, 'db.sqlite3')),
    SENTRY_DSN=(str, ''),
    MEDIA_ROOT=(str, os.path.join(BASE_DIR, 'media')),

    RQ_REDIS_HOST=(str, 'localhost'),
    RQ_REDIS_PORT=(str, '6379'),
    RQ_REDIS_DB=(str, '0'),
    RQ_REDIS_USERNAME=(str, ''),
    RQ_REDIS_PASSWORD=(str, ''),
)

# We use the setting to choose whether to show the section about Sentry in the
# terms and conditions
SENTRY_DSN = env('SENTRY_DSN')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import ignore_logger

    ignore_logger('django.security.DisallowedHost')
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()]
    )

DEALER_TYPE = 'git'

PIWIK = settings.PIWIK

# We can't take MEDIA_ROOT and MEDIA_URL from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
MEDIA_ROOT = env("MEDIA_ROOT")
MEDIA_URL = '/media/'

SECRET_KEY = settings.SECRET_KEY
DEBUG = settings.DEBUG
ALLOWED_HOSTS = settings.ALLOWED_HOSTS
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'cove.middleware.CoveConfigCurrentApp',
    "dealer.contrib.django.Middleware",
)
ROOT_URLCONF = settings.ROOT_URLCONF
TEMPLATES = settings.TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append('cove_360.context_processors.additional_context')

WSGI_APPLICATION = settings.WSGI_APPLICATION

# We can't take DATABASES from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': env('DB_NAME'),
    }
}
LANGUAGE_CODE = settings.LANGUAGE_CODE
TIME_ZONE = settings.TIME_ZONE
USE_I18N = settings.USE_I18N
USE_L10N = settings.USE_L10N
USE_TZ = settings.USE_TZ

# We can't take STATIC_URL and STATIC_ROOT from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# and that doesn't work with our standard Apache setup.
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

LANGUAGES = settings.LANGUAGES
LOCALE_PATHS = settings.LOCALE_PATHS
LOCALE_PATHS += os.path.join(BASE_DIR, 'cove_360', 'locale'),
LOGGING = settings.LOGGING

if getattr(settings, 'RAVEN_CONFIG', None):
    RAVEN_CONFIG = settings.RAVEN_CONFIG

INSTALLED_APPS = (
    'cove_360',
    'cove',
    'cove.input',
    'bootstrap3',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_rq',
)

WSGI_APPLICATION = 'cove_project.wsgi.application'
ROOT_URLCONF = 'cove_project.urls'

COVE_CONFIG = COVE_CONFIG

# https://github.com/OpenDataServices/cove/issues/1098
FILE_UPLOAD_PERMISSIONS = 0o644


if os.environ.get("CACHE"):
    print("Filesystem based cache: Enabled")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/var/tmp/django_cache',
        }
    }

# https://docs.djangoproject.com/en/4.0/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


DATA_SUBMISSION_ENABLED = False

if "true" in os.environ.get("DATA_SUBMISSION_ENABLED", "").lower():
    DATA_SUBMISSION_ENABLED = True

DISABLE_COOKIE_POPUP = False

if "true" in os.environ.get("DISABLE_COOKIE_POPUP", "").lower():
    DISABLE_COOKIE_POPUP = True

# If enabled the grants data can be used in a template to create a browsable
# table of grants.
GRANTS_TABLE = False

# Django RQ Queues
RQ_QUEUES = {
    'default': {
        'HOST': env("RQ_REDIS_HOST"),
        'PORT': env("RQ_REDIS_PORT"),
        'DB': env("RQ_REDIS_DB"),
        'USERNAME': env("RQ_REDIS_USERNAME"),
        'PASSWORD': env("RQ_REDIS_PASSWORD"),
        'DEFAULT_TIMEOUT': 360,
        'DEFAULT_RESULT_TTL': 800,
    },
}