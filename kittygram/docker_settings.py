"""Settings for the local Docker deployment."""
import os

from .settings import *  # noqa: F401,F403

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/data/db.sqlite3',
    }
}
