# 🚀 Deployment Guide: SEO Bot → Production

## Prerequisites

Before deploying, ensure you have:

1. **Supabase Project**
   - Created in your "SEO-Bot" organization
   - Database schema deployed
   - API keys ready

2. **Vercel Account**
   - Connected to your GitHub account
   - Ready for deployment

3. **Domain** (Optional)
   - If you want a custom domain instead of vercel.app

## Step 1: Setup Supabase Database

### 1.1 Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Navigate to your "SEO-Bot" organization
3. Create a new project:
   - Name: `central-florida-seo`
   - Region: Choose closest to your users
   - Database password: Generate secure password

### 1.2 Deploy Database Schema
1. Open Supabase SQL Editor
2. Copy contents of `website/api/supabase_schema.sql`
3. Execute the script to create all tables and functions
4. Verify tables are created:
   - `users`
   - `businesses` 
   - `seo_reports`
   - `seo_logs`

### 1.3 Get API Keys
1. Go to Project Settings → API
2. Copy these values:
   - **Project URL**: `https://xxx.supabase.co`
   - **Anon Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **Service Role Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## Step 2: Deploy Supabase Edge Functions

### 2.1 Install Supabase CLI
```bash
npm install -g supabase
```

### 2.2 Login and Link Project
```bash
supabase login
supabase link --project-ref your-project-ref
```

### 2.3 Deploy Functions
```bash
cd /Users/petpawlooza/seo-bot-standalone
supabase functions deploy auth
supabase functions deploy businesses
supabase functions deploy seo-tools
supabase functions deploy payments
supabase functions deploy admin
```

### 2.4 Set Environment Variables for Functions
```bash
supabase secrets set STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Step 3: Deploy Frontend to Vercel

### 3.1 Install Vercel CLI
```bash
npm install -g vercel
```

### 3.2 Prepare Environment Variables
Create these in Vercel dashboard or CLI:

```bash
# Required for frontend
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
VITE_APP_URL=https://your-domain.vercel.app

# Optional
VITE_APP_NAME="Central Florida SEO Services"
VITE_ENABLE_ANALYTICS=true
```

### 3.3 Deploy to Vercel
```bash
cd /Users/petpawlooza/seo-bot-standalone
vercel
```

Follow prompts:
- **Project name**: `seo-bot-standalone` or your preferred name
- **Framework**: Vite
- **Output directory**: `dist`
- **Build command**: `npm run build`
- **Install command**: `npm install`

### 3.4 Set Environment Variables
Either use Vercel dashboard or CLI:

```bash
vercel env add VITE_SUPABASE_URL production
vercel env add VITE_SUPABASE_ANON_KEY production
vercel env add VITE_STRIPE_PUBLISHABLE_KEY production
vercel env add VITE_APP_URL production
```

### 3.5 Deploy to Production
```bash
vercel --prod
```

## Step 4: Configure CORS and Redirects

### 4.1 Update Supabase Auth URLs
1. Go to Supabase Dashboard → Authentication → URL Configuration
2. Add your Vercel URL to **Redirect URLs**:
   ```
   https://your-app.vercel.app
   https://your-app.vercel.app/**
   ```

### 4.2 Update CORS in Edge Functions
The functions are already configured for Vercel deployment, but verify:
- `supabase/functions/_shared/cors.ts` includes your domain

## Step 5: Test Deployment

### 5.1 Frontend Tests
Visit your Vercel URL and test:
- [ ] Homepage loads correctly
- [ ] User registration works
- [ ] User login works
- [ ] Dashboard is accessible
- [ ] Business creation works

### 5.2 API Tests
Test Edge Functions directly:
```bash
# Test auth
curl -X POST https://your-project.supabase.co/functions/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","first_name":"Test","last_name":"User"}'

# Test businesses (requires auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-project.supabase.co/functions/v1/businesses
```

### 5.3 Database Tests
Check Supabase Dashboard:
- [ ] Users table populated
- [ ] Businesses table working
- [ ] SEO reports generated
- [ ] Logs recorded

## Step 6: Optional - Custom Domain

### 6.1 Add Domain to Vercel
1. Go to Vercel Dashboard → Project → Settings → Domains
2. Add your custom domain
3. Configure DNS records as shown

### 6.2 Update Environment Variables
```bash
vercel env add VITE_APP_URL production
# Set to your custom domain: https://yourdomain.com
```

### 6.3 Update Supabase CORS
Add your custom domain to:
- Supabase Auth redirect URLs
- Edge Functions CORS settings

## Step 7: Monitoring & Maintenance

### 7.1 Set Up Monitoring
- **Vercel Analytics**: Enable in project settings
- **Supabase Monitoring**: Check database performance
- **Error Tracking**: Consider Sentry integration

### 7.2 Regular Tasks
- Monitor Supabase usage and upgrade plan if needed
- Check Vercel function usage
- Update dependencies regularly
- Monitor SEO tool performance

## Troubleshooting

### Common Issues

**Frontend won't load:**
- Check environment variables are set correctly
- Verify Vite build completed successfully
- Check browser console for errors

**Auth not working:**
- Verify Supabase URL and keys
- Check CORS settings
- Ensure redirect URLs are configured

**Edge Functions failing:**
- Check function logs in Supabase dashboard
- Verify environment variables for functions
- Test functions individually

**Database errors:**
- Check Row Level Security policies
- Verify user permissions
- Check table structure matches schema

### Getting Help

1. **Vercel**: Check deployment logs in dashboard
2. **Supabase**: Use built-in logging and monitoring  
3. **Debug mode**: Set `VITE_DEV_MODE=true` for detailed logs

## Success Metrics

Once deployed, you should see:
- ✅ **Fast loading times** (< 2 seconds)
- ✅ **Mobile responsive** design
- ✅ **SEO optimized** (meta tags, structured data)
- ✅ **Analytics tracking** (if enabled)
- ✅ **Error-free** user flows

## Production Checklist

Before going live:
- [ ] Database schema deployed
- [ ] Edge functions working
- [ ] Frontend deployed to Vercel
- [ ] Environment variables set
- [ ] CORS configured
- [ ] Custom domain (optional)
- [ ] SSL certificate active
- [ ] Analytics configured
- [ ] Error monitoring set up
- [ ] User registration flow tested
- [ ] Payment processing tested (if using real Stripe keys)
- [ ] SEO tools functional
- [ ] Admin panel accessible

🎉 **Your SEO Bot is now live and ready to serve Central Florida businesses!**

---

# Advanced Production Deployment & Monitoring

## Docker Production Deployment

### System Requirements for Production
- **CPU**: 8+ cores
- **Memory**: 16GB+ RAM 
- **Storage**: 100GB+ SSD
- **OS**: Ubuntu 22.04 LTS or RHEL 8+

### Production Docker Setup

#### 1. Create Production Environment
```bash
# Create production directory
sudo mkdir -p /opt/seo-bot-production
cd /opt/seo-bot-production

# Clone repository
git clone https://github.com/your-org/seo-bot-standalone.git .

# Create production environment file
cp .env.example .env.production
```

#### 2. Production Environment Variables
```env
# Application
NODE_ENV=production
APP_PORT=8000
WORKERS=4

# Database (Production)
DATABASE_URL=postgresql://seobot:secure_password@postgres:5432/seobot_prod
REDIS_URL=redis://redis:6379/0

# Supabase Production
SUPABASE_URL=https://your-prod-project.supabase.co
SUPABASE_ANON_KEY=your_production_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_production_service_key

# Security
SECRET_KEY=your_ultra_secure_secret_key_here
JWT_SECRET=your_jwt_secret_here
ENCRYPTION_KEY=your_32_byte_encryption_key

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
SENTRY_DSN=https://your_sentry_dsn

# Storage & Backups
S3_BACKUP_BUCKET=seobot-prod-backups
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=90

# External APIs
OPENAI_API_KEY=your_openai_production_key
GOOGLE_API_KEY=your_google_api_key
STRIPE_SECRET_KEY=sk_live_your_stripe_secret

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/your/webhook
EMAIL_SMTP_HOST=smtp.sendgrid.net
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=apikey
EMAIL_PASSWORD=your_sendgrid_api_key
```

#### 3. Production Docker Compose
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILD_ENV: production
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/seobot_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./exports:/app/exports
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-secure_password_here}
      - POSTGRES_DB=seobot_prod
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./database/init-prod.sql:/docker-entrypoint-initdb.d/init.sql
      - ./backups/postgres:/backups
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d seobot_prod"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./static:/usr/share/nginx/html
    depends_on:
      - app
    restart: unless-stopped

  # Background Workers
  worker-general:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - WORKER_TYPE=general
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/seobot_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    command: ["python", "-m", "src.worker", "--worker-type", "general"]

  worker-seo:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - WORKER_TYPE=seo
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/seobot_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1.5G
        reservations:
          memory: 1G
    command: ["python", "-m", "src.worker", "--worker-type", "seo"]

  # Scheduled Tasks
  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/seobot_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./backups:/app/backups
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: ["python", "-m", "src.scheduler"]

  # Monitoring Stack
  prometheus:
    image: prom/prometheus:v2.40.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:9.3.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.25.0
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
    restart: unless-stopped

volumes:
  postgres_prod_data:
  redis_prod_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### 4. Production Deployment Script
Create `deploy-production.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Starting SEO Bot Production Deployment..."

# Configuration
BACKUP_DIR="/opt/seo-bot-backups/$(date +%Y%m%d_%H%M%S)"
COMPOSE_FILE="docker-compose.prod.yml"

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."
if [ ! -f ".env.production" ]; then
    echo "❌ Production environment file not found!"
    exit 1
fi

if [ ! -f "nginx/ssl/cert.pem" ]; then
    echo "❌ SSL certificate not found!"
    exit 1
fi

# Create backup
echo "💾 Creating backup..."
mkdir -p $BACKUP_DIR
docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U postgres seobot_prod > $BACKUP_DIR/database.sql
docker-compose -f $COMPOSE_FILE exec -T redis redis-cli SAVE

# Build new images
echo "🔨 Building new images..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Rolling deployment
echo "🔄 Performing rolling deployment..."

# Update workers first
docker-compose -f $COMPOSE_FILE up -d --no-deps worker-general worker-seo scheduler

# Update main application
docker-compose -f $COMPOSE_FILE up -d --no-deps app

# Update nginx last
docker-compose -f $COMPOSE_FILE up -d --no-deps nginx

# Run health checks
echo "🏥 Running health checks..."
sleep 30

# Check application health
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Health check failed! Rolling back..."
    # Rollback logic here
    exit 1
fi

# Check database connectivity
if ! docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "❌ Database check failed!"
    exit 1
fi

echo "✅ Production deployment completed successfully!"
echo "🔍 Monitor logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "📊 Grafana: http://localhost:3000"
echo "🎯 Prometheus: http://localhost:9090"
```

Make it executable:
```bash
chmod +x deploy-production.sh
```

## Comprehensive Monitoring Setup

### 1. Application Performance Monitoring

#### Custom Metrics Implementation
Add to `src/seo_bot/utils/metrics.py`:
```python
import time
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
DATABASE_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')
CACHE_HIT_RATE = Gauge('cache_hit_rate_percent', 'Cache hit rate percentage')
SEO_JOBS_QUEUE = Gauge('seo_jobs_in_queue', 'Number of SEO jobs in queue')
KEYWORD_PROCESSING_TIME = Histogram('keyword_processing_seconds', 'Keyword processing time')

def track_request_metrics(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await f(*args, **kwargs)
            REQUEST_COUNT.labels(method='GET', endpoint=f.__name__, status='200').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint=f.__name__, status='500').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper
```

#### 2. Alertmanager Configuration
Create `monitoring/alertmanager.yml`:
```yaml
global:
  smtp_smarthost: 'smtp.sendgrid.net:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_auth_username: 'apikey'
  smtp_auth_password: 'your_sendgrid_api_key'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'

- name: 'critical-alerts'
  email_configs:
  - to: 'admin@your-domain.com'
    subject: '🚨 CRITICAL: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      Severity: {{ .Labels.severity }}
      Instance: {{ .Labels.instance }}
      {{ end }}
  slack_configs:
  - api_url: 'https://hooks.slack.com/your/webhook'
    channel: '#critical-alerts'
    title: '🚨 Critical Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

- name: 'warning-alerts'
  email_configs:
  - to: 'team@your-domain.com'
    subject: '⚠️ WARNING: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

#### 3. Grafana Dashboards
Create pre-configured dashboards in `monitoring/grafana/dashboards/`:

**Application Performance Dashboard:**
```json
{
  "dashboard": {
    "title": "SEO Bot Application Performance",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{ method }} {{ endpoint }}"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

## Backup and Disaster Recovery

### 1. Automated Backup System
Create `scripts/backup-system.sh`:
```bash
#!/bin/bash

# Configuration
BACKUP_ROOT="/opt/seo-bot-backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=90
S3_BUCKET="seobot-prod-backups"

echo "🗄️ Starting automated backup process..."

# Create backup directory
BACKUP_DIR="$BACKUP_ROOT/$DATE"
mkdir -p $BACKUP_DIR

# Database backup
echo "📊 Backing up PostgreSQL database..."
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
  -U postgres -h localhost seobot_prod \
  --verbose --clean --no-owner --no-privileges \
  > $BACKUP_DIR/database.sql

# Redis backup
echo "💾 Backing up Redis data..."
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli --rdb /tmp/dump.rdb
docker-compose -f docker-compose.prod.yml cp redis:/tmp/dump.rdb $BACKUP_DIR/redis.rdb

# Application data
echo "📁 Backing up application data..."
tar -czf $BACKUP_DIR/app-data.tar.gz data/ logs/ exports/

# Configuration backup
echo "⚙️ Backing up configuration..."
tar -czf $BACKUP_DIR/config.tar.gz \
  docker-compose.prod.yml \
  nginx/ \
  monitoring/ \
  .env.production

# Create manifest
echo "📋 Creating backup manifest..."
cat > $BACKUP_DIR/manifest.json << EOF
{
  "backup_date": "$DATE",
  "backup_type": "full",
  "components": {
    "database": "database.sql",
    "redis": "redis.rdb", 
    "application_data": "app-data.tar.gz",
    "configuration": "config.tar.gz"
  },
  "size_mb": $(du -sm $BACKUP_DIR | cut -f1)
}
EOF

# Compress entire backup
echo "🗜️ Compressing backup..."
cd $BACKUP_ROOT
tar -czf "$DATE.tar.gz" $DATE/
rm -rf $DATE/

# Upload to S3
if [ ! -z "$S3_BUCKET" ]; then
    echo "☁️ Uploading to S3..."
    aws s3 cp "$DATE.tar.gz" "s3://$S3_BUCKET/daily/$DATE.tar.gz"
fi

# Cleanup old backups
echo "🧹 Cleaning up old backups..."
find $BACKUP_ROOT -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup completed: $DATE.tar.gz"
```

### 2. Disaster Recovery Procedure
Create `scripts/disaster-recovery.sh`:
```bash
#!/bin/bash

BACKUP_FILE=$1
RESTORE_TYPE=${2:-full}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file> [full|database_only|config_only]"
    exit 1
fi

echo "🚨 Starting disaster recovery process..."
echo "Backup file: $BACKUP_FILE"
echo "Restore type: $RESTORE_TYPE"

# Stop services
echo "🛑 Stopping services..."
docker-compose -f docker-compose.prod.yml down

# Extract backup
echo "📦 Extracting backup..."
RESTORE_DIR="/tmp/seobot-restore-$(date +%s)"
mkdir -p $RESTORE_DIR
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# Restore database
if [ "$RESTORE_TYPE" = "full" ] || [ "$RESTORE_TYPE" = "database_only" ]; then
    echo "📊 Restoring database..."
    
    # Start only database
    docker-compose -f docker-compose.prod.yml up -d postgres
    sleep 30
    
    # Restore data
    docker-compose -f docker-compose.prod.yml exec -T postgres psql \
      -U postgres -d seobot_prod < $RESTORE_DIR/*/database.sql
fi

# Restore Redis
if [ "$RESTORE_TYPE" = "full" ]; then
    echo "💾 Restoring Redis data..."
    docker-compose -f docker-compose.prod.yml up -d redis
    sleep 10
    docker cp $RESTORE_DIR/*/redis.rdb $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb
    docker-compose -f docker-compose.prod.yml restart redis
fi

# Restore application data
if [ "$RESTORE_TYPE" = "full" ]; then
    echo "📁 Restoring application data..."
    tar -xzf $RESTORE_DIR/*/app-data.tar.gz
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose -f docker-compose.prod.yml up -d

# Verify restoration
echo "🔍 Verifying restoration..."
sleep 60

if curl -f http://localhost:8000/health; then
    echo "✅ Disaster recovery completed successfully!"
else
    echo "❌ Recovery verification failed!"
    exit 1
fi

# Cleanup
rm -rf $RESTORE_DIR
```

## Security Hardening

### 1. Container Security
Create `security/Dockerfile.security`:
```dockerfile
# Security-hardened production image
FROM python:3.9-slim AS security-base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /bin/false appuser

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Remove unnecessary packages
RUN apt-get autoremove -y && apt-get clean

# Set secure permissions
RUN chmod 750 /home/appuser
```

### 2. Network Security
Update `docker-compose.prod.yml` with network isolation:
```yaml
networks:
  frontend:
    driver: bridge
    internal: false
  backend:
    driver: bridge
    internal: true
  monitoring:
    driver: bridge
    internal: true

services:
  app:
    networks:
      - frontend
      - backend
    
  postgres:
    networks:
      - backend
    # Only accessible from backend network
    
  nginx:
    networks:
      - frontend
    # Only on frontend network
```

### 3. Security Scanning
Create `.github/workflows/security.yml`:
```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2 AM
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'seobot/seo-bot-standalone:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## Load Balancing and High Availability

### 1. HAProxy Configuration
Create `haproxy/haproxy.cfg`:
```
global
    daemon
    maxconn 4096
    log stdout local0

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog
    log global

frontend seobot_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/seobot.pem
    redirect scheme https if !{ ssl_fc }
    
    # Health check endpoint
    acl health_check path /health
    use_backend health_backend if health_check
    
    # API endpoints
    acl api_request path_beg /api
    use_backend api_backend if api_request
    
    # Default to app
    default_backend app_backend

backend app_backend
    balance roundrobin
    option httpchk GET /health
    server app1 app:8000 check
    server app2 app:8000 check

backend api_backend
    balance leastconn
    option httpchk GET /api/health
    server api1 app:8000 check
    server api2 app:8000 check

backend health_backend
    server health app:8000 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

## Performance Optimization

### 1. Database Optimization
Create `database/performance-tuning.sql`:
```sql
-- Production PostgreSQL optimization
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Reload configuration
SELECT pg_reload_conf();

-- Create performance monitoring views
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- Index monitoring
CREATE OR REPLACE VIEW unused_indexes AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_tup_read = 0
ORDER BY schemaname, tablename;
```

### 2. Redis Optimization
Create `redis/redis-prod.conf`:
```conf
# Production Redis configuration
maxmemory 4gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Performance settings
tcp-keepalive 60
timeout 300
databases 16

# Persistence
dir /data
dbfilename dump.rdb
rdbcompression yes
rdbchecksum yes

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Network
bind 0.0.0.0
port 6379
tcp-backlog 511

# Clients
maxclients 10000
```

---

## Final Production Checklist

### Pre-Launch Verification
- [ ] **Security**: SSL certificates, firewalls, container security
- [ ] **Performance**: Load testing completed, optimization applied
- [ ] **Monitoring**: All dashboards configured, alerts tested
- [ ] **Backup**: Automated backups working, recovery tested
- [ ] **High Availability**: Load balancing configured, failover tested
- [ ] **Documentation**: Deployment procedures documented
- [ ] **Team Training**: Operations team trained on procedures

### Go-Live Steps
1. **Final backup** of staging environment
2. **Deploy to production** using automated scripts
3. **Run smoke tests** on all critical paths
4. **Monitor closely** for first 24 hours
5. **Document any issues** and resolutions

🎯 **Your SEO Bot is now enterprise-ready with comprehensive monitoring, security, and high availability!**