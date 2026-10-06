FROM python:3.12-slim

WORKDIR /app

# mysqlclient compila contra libmysqlclient (requiere pkg-config + headers).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config default-libmysqlclient-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY . .
RUN mkdir -p logs media \
    && git config --system --add safe.directory "*"

ENV PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=eje_central_back.settings

EXPOSE 8000

CMD ["gunicorn", "eje_central_back.wsgi:application", "-c", "gunicorn.conf.py"]
