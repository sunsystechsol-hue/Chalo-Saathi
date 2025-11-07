# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# ✅ Install system dependencies for MySQL + Pillow + SSL + Celery
RUN apt-get update -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        gcc \
        netcat-openbsd \
        libssl-dev \
        libffi-dev \
        libjpeg-dev \
        zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Copy code
COPY . /app

# ✅ Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ Collect static files (ignore errors)
RUN python manage.py collectstatic --noinput || true

# ✅ Expose port (Render auto-assigns)
EXPOSE 8000

# ✅ Run database migrations automatically before starting Gunicorn
CMD ["sh", "-c", "for i in 1 2 3 4 5; do python manage.py migrate --noinput && break || sleep 5; done && gunicorn chalosaathi.wsgi:application --bind 0.0.0.0:$PORT"]
