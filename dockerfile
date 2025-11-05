FROM python:3.12-slim

WORKDIR /app

# ✅ Install all required system dependencies
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

# ✅ Copy code into container
COPY . /app

# ✅ Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ Make wait_for_db.sh executable
RUN chmod +x /app/wait_for_db.sh

EXPOSE 8000

# ✅ Start server after ensuring DB is ready
CMD ["sh", "-c", "./wait_for_db.sh && python manage.py runserver 0.0.0.0:8000"]
