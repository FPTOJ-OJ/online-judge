import os
import logging
import socket

from celery import Celery
from celery.signals import task_failure

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')

app = Celery('dmoj')

from django.conf import settings  # noqa: E402
app.config_from_object(settings, namespace='CELERY')

app.conf.result_backend = app.conf.broker_url

if hasattr(settings, 'CELERY_BROKER_URL_SECRET'):
    app.conf.broker_url = settings.CELERY_BROKER_URL_SECRET
    app.conf.result_backend = settings.CELERY_BROKER_URL_SECRET
if hasattr(settings, 'CELERY_RESULT_BACKEND_SECRET'):
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND_SECRET

app.autodiscover_tasks()

logger = logging.getLogger('judge.celery')


@task_failure.connect()
def celery_failure_log(sender, task_id, exception, traceback, *args, **kwargs):
    logger.error('Celery Task %s: %s on %s', sender.name, task_id, socket.gethostname(),
                 exc_info=(type(exception), exception, traceback))
