FROM python:3.13-slim

ENV DJANGO_DEBUG=0

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
RUN chown 1000:1000 /app /app/db.sqlite3
USER 1000

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn Restaurant.wsgi:application --bind 0.0.0.0:8000"]
