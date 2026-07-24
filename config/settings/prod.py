"""Production settings — security headers ON, DEBUG=False."""
from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = env("ALLOWED_HOSTS")  # noqa: F405 — imported via base.*
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa: F405

# ---------- static files (no manifest needed — avoids missing staticfiles.json) ----------
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ---------- template caching (RAM/CPU lever, prod only) ----------
# Templates never change at runtime in prod, so parse each one ONCE and reuse
# the compiled form for the process's life. The cached loader wraps the normal
# filesystem + app-directory loaders; APP_DIRS must be False when loaders are
# set explicitly. Dev keeps auto-reloading loaders (base.py APP_DIRS=True).
TEMPLATES[0]["APP_DIRS"] = False  # noqa: F405 — imported via base.*
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa: F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ),
]

# ---------- security ----------
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------- email validation in prod ----------
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("PRODUCTION CONFIG ERROR: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD environment variable is missing or blank!")
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "EMAIL_HOST_USER and EMAIL_HOST_PASSWORD environment variables must be non-empty in production (DEBUG=False). "
        "Please set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your Render Environment settings."
    )

