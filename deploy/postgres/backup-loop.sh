#!/bin/sh
set -eu

interval="${BACKUP_INTERVAL_SECONDS:-86400}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
backup_dir="/backups"

mkdir -p "$backup_dir"

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  output="$backup_dir/${POSTGRES_DB}_${timestamp}.dump"

  pg_dump \
    --host=postgres \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --file="$output"

  find "$backup_dir" -type f -name "${POSTGRES_DB}_*.dump" -mtime +"$retention_days" -delete
  sleep "$interval"
done
