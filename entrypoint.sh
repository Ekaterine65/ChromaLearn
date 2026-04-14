#!/bin/sh

echo "Waiting for MySQL..."

while ! nc -z db 3306; do
  sleep 1
done

echo "MySQL started"

echo "Running migrations..."
flask db upgrade

echo "Checking seed..."

SEED=$(python - <<END
from app import app
from models import Color, db

with app.app_context():
    exists = db.session.query(Color).first() is not None
    print(not exists)
END
)

if [ "$SEED" = "True" ]; then
    echo "Seeding colors..."
    python seed_colors.py
else
    echo "Seed already done"
fi

echo "Starting Flask..."
flask run --host=0.0.0.0 --port=5000