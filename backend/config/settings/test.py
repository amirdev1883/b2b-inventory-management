from .base import *

SECRET_KEY = "testing-only-secret-key-with-more-than-fifty-characters-for-jwt"
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]
