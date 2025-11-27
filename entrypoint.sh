#!/bin/sh
set -e

# Configurações padrão para o QR Reader
export QR_SOURCE="${QR_SOURCE:-0}"
export QR_PORT="${QR_PORT:-5001}"
export QR_BACKEND_URL="${QR_BACKEND_URL:-http://127.0.0.1:8000/api/arduino/pacote/}"
export QR_TUNNEL="${QR_TUNNEL:-false}"

# Run migrations and start the Django development server
echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting server on 0.0.0.0:8000"
echo "QR Reader service will start automatically with Django"
python manage.py runserver 0.0.0.0:8000
