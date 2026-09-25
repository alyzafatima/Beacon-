import os
from decouple import config
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "beacon.settings")

app = Celery("beacon")

app.conf.broker_url = config(
    "REDIS_URL"
)
app.config_from_object(
    "django.conf:settings",
    namespace="CELERY"
)

app.autodiscover_tasks()