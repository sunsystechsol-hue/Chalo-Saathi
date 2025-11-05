import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chalosaathi.settings')

app = Celery('chalosaathi')

# 🔥 Explicitly set the broker and backend here
app.conf.broker_url = 'redis://redis_broker:6379/0'
app.conf.result_backend = 'redis://redis_broker:6379/0'

# Load config from Django settings (optional, good practice)
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
