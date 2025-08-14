#!/bin/bash

# Database backup script for SEO Bot
# Usage: ./backup_database.sh [environment]

set -e

# Configuration
BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENVIRONMENT=${1:-production}

# Load environment variables
if [ "$ENVIRONMENT" = "production" ]; then
    DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@postgres:5432/seo_bot"}
else
    DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@localhost:5432/seo_bot"}
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Extract connection details from DATABASE_URL
DB_HOST=$(echo $DATABASE_URL | sed 's/.*@\([^:]*\):.*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed 's/.*:\([0-9]*\)\/.*/\1/')
DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
DB_USER=$(echo $DATABASE_URL | sed 's/.*\/\/\([^:]*\):.*/\1/')
DB_PASS=$(echo $DATABASE_URL | sed 's/.*\/\/[^:]*:\([^@]*\)@.*/\1/')

# Set PostgreSQL password
export PGPASSWORD="$DB_PASS"

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/seo_bot_backup_${ENVIRONMENT}_${DATE}.sql"

echo "Creating database backup..."
echo "Environment: $ENVIRONMENT"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"

# Create the backup
pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --blobs \
    --verbose \
    --file="$BACKUP_FILE.custom"

# Also create a plain text backup for readability
pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=plain \
    --inserts \
    --file="$BACKUP_FILE"

# Compress the plain text backup
gzip "$BACKUP_FILE"

echo "Backup completed successfully!"
echo "Files created:"
echo "  - $BACKUP_FILE.custom (PostgreSQL custom format)"
echo "  - $BACKUP_FILE.gz (Compressed SQL)"

# Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -name "seo_bot_backup_${ENVIRONMENT}_*.sql.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "seo_bot_backup_${ENVIRONMENT}_*.sql.custom" -mtime +7 -delete

echo "Cleanup completed - old backups removed"

# Upload to cloud storage if configured
if [ ! -z "$BACKUP_S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE.custom" "s3://$BACKUP_S3_BUCKET/database-backups/" || echo "S3 upload failed"
    aws s3 cp "$BACKUP_FILE.gz" "s3://$BACKUP_S3_BUCKET/database-backups/" || echo "S3 upload failed"
fi

echo "Backup process completed!"