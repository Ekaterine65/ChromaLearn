#!/bin/sh
set -e

echo "Waiting for MySQL..."

while ! nc -z "$MYSQL_HOST" "$MYSQL_PORT"; do
  sleep 1
done

echo "MySQL started"

echo "Running migrations..."
flask db upgrade

echo "Checking database data..."

COLOR_COUNT=$(mysql \
    --ssl=0 \
    -h "$MYSQL_HOST" \
    -P "$MYSQL_PORT" \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    -N -s \
    "$MYSQL_DATABASE" \
    -e "SELECT COUNT(*) FROM colors")

TRANSLATED_ASSOCIATION_COUNT=$(mysql \
    --ssl=0 \
    -h "$MYSQL_HOST" \
    -P "$MYSQL_PORT" \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    -N -s \
    "$MYSQL_DATABASE" \
    -e "SELECT COUNT(*) FROM emotions WHERE name_ru IS NOT NULL AND name_ru != ''")

if [ "$COLOR_COUNT" = "0" ]; then
    if [ ! -f "$DATA_DUMP_PATH" ]; then
        echo "Data dump not found: $DATA_DUMP_PATH"
        exit 1
    fi

    echo "Importing data dump..."
    IMPORT_DUMP_PATH="/tmp/chromalearn_data_import.sql"
    sed '/LOCK TABLES `alembic_version` WRITE;/,/UNLOCK TABLES;/d' "$DATA_DUMP_PATH" > "$IMPORT_DUMP_PATH"
    mysql \
        --ssl=0 \
        -h "$MYSQL_HOST" \
        -P "$MYSQL_PORT" \
        -u "$MYSQL_USER" \
        -p"$MYSQL_PASSWORD" \
        "$MYSQL_DATABASE" < "$IMPORT_DUMP_PATH"
elif [ "$TRANSLATED_ASSOCIATION_COUNT" = "0" ]; then
    echo "Database already has colors, but no translated associations were found."
    echo "The existing Docker volume likely contains old seed data."
    echo "Run: docker compose down -v"
    echo "Then: docker compose up --build"
    exit 1
else
    echo "Data already exists, skipping dump import"
fi

echo "Starting Flask..."
flask run --host=0.0.0.0 --port=5000
