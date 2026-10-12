#!/bin/sh
set -e

echo "Waiting for MySQL database at $DB_HOST:$DB_PORT..."

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "MySQL is up and reachable!"

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static assets..."
python manage.py collectstatic --noinput --clear

echo "Checking if initial seed data is needed..."
python manage.py shell -c "
from crime_data.models import CrimeRecord
if CrimeRecord.objects.count() == 0:
    print('Empty database detected. Running seed_data...')
    from django.core.management import call_command
    call_command('seed_data')
else:
    print('Database already contains records. Skipping seed_data.')
"

echo "Starting application server..."
exec "$@"
