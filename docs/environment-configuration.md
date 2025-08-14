# Environment Configuration Guide

This guide explains how to configure the SEO Bot application for different environments.

## Overview

The SEO Bot supports multiple environments with specific configuration files:

- **Development**: `.env.development` - Local development with minimal external dependencies
- **Staging**: `.env.staging` - Pre-production testing environment
- **Production**: `.env.production` - Live production environment

## Quick Start

1. Choose your environment configuration:
   ```bash
   # For development
   cp .env.development .env
   
   # For staging
   cp .env.staging .env
   
   # For production
   cp .env.production .env
   ```

2. Edit the `.env` file with your specific values

3. Validate your configuration:
   ```bash
   python scripts/validate_config.py .env
   ```

## Configuration Sections

### Application Configuration
Controls basic application behavior:

- `NODE_ENV`: Environment mode (development/staging/production)
- `ENVIRONMENT`: Application environment identifier
- `APP_NAME`: Display name for the application
- `APP_URL`: Base URL where the application is hosted
- `DEBUG`: Enable/disable debug mode
- `LOG_LEVEL`: Logging verbosity (debug/info/warning/error)

### Database Configuration
PostgreSQL database settings:

- `DATABASE_URL`: Full database connection string
- `DB_POOL_SIZE`: Connection pool size (5 for dev, 20 for prod)
- `DB_MAX_OVERFLOW`: Maximum pool overflow connections
- `DB_POOL_TIMEOUT`: Connection timeout in seconds

### Frontend Configuration
React application settings:

- `VITE_SUPABASE_URL`: Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Supabase anonymous access key
- `VITE_APP_URL`: Frontend application URL
- `VITE_ENABLE_ANALYTICS`: Enable/disable analytics tracking
- `VITE_STRIPE_PUBLISHABLE_KEY`: Stripe public key for payments

### Backend API Configuration
Server-side API settings:

- `SECRET_KEY`: Application secret key (min 32 characters)
- `JWT_SECRET_KEY`: JWT token signing key (min 32 characters)
- `JWT_ACCESS_TOKEN_EXPIRES`: Token expiration time in hours
- `API_V1_STR`: API version prefix

### External API Keys
Third-party service integrations:

- `GOOGLE_SEARCH_CONSOLE_CREDENTIALS_FILE`: GSC service account file
- `PAGESPEED_API_KEY`: Google PageSpeed Insights API key
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `SERP_API_KEY`: SERP API key for search data
- `STRIPE_SECRET_KEY`: Stripe secret key for payments

### Security Configuration
Security-related settings:

- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `SECURE_SSL_REDIRECT`: Force HTTPS redirects
- `SECURE_COOKIES`: Use secure cookies
- `SESSION_COOKIE_SECURE`: Secure session cookies
- `CSRF_COOKIE_SECURE`: Secure CSRF cookies

### Feature Flags
Enable/disable application features:

- `ENABLE_REGISTRATION`: Allow new user registration
- `ENABLE_AI_CONTENT`: Enable AI-powered content features
- `ENABLE_WEBHOOKS`: Enable webhook functionality
- `ENABLE_REALTIME_UPDATES`: Enable WebSocket real-time updates

## Environment-Specific Guidelines

### Development Environment

**Characteristics:**
- Relaxed security settings
- Local database and Redis
- Disabled external APIs by default
- Verbose logging enabled
- No SSL requirements

**Setup:**
1. Install local PostgreSQL and Redis
2. Copy `.env.development` to `.env`
3. Update database credentials
4. Start development servers

### Staging Environment

**Characteristics:**
- Production-like security settings
- Separate staging database
- Test API keys
- Email sandboxing (Mailtrap)
- SSL enabled

**Setup:**
1. Deploy to staging infrastructure
2. Copy `.env.staging` to `.env`
3. Configure staging database and Redis
4. Set up test API keys
5. Configure SSL certificates

### Production Environment

**Characteristics:**
- Maximum security settings
- Production database with backups
- Live API keys
- Email delivery enabled
- SSL required
- Monitoring enabled

**Setup:**
1. Deploy to production infrastructure
2. Copy `.env.production` to `.env`
3. Configure production database
4. Set up all external API keys
5. Configure SSL certificates
6. Enable monitoring and backups

## Security Best Practices

### Secret Management

1. **Never commit secrets to version control**
2. **Use strong, unique secrets** (minimum 32 characters)
3. **Rotate secrets regularly** in production
4. **Use environment-specific secrets**

### Database Security

1. **Use strong database passwords**
2. **Limit database access by IP**
3. **Enable SSL for database connections**
4. **Regular backups and encryption**

### API Key Management

1. **Use least-privilege API keys**
2. **Separate keys per environment**
3. **Monitor API key usage**
4. **Rotate keys periodically**

## Validation

Always validate your configuration before deployment:

```bash
# Validate specific environment file
python scripts/validate_config.py .env.production

# Validate current environment
python scripts/validate_config.py
```

The validator checks for:
- Required variables
- Security best practices
- URL formats
- Environment consistency
- Common misconfigurations

## Troubleshooting

### Common Issues

1. **Missing required variables**
   - Solution: Check validator output and add missing variables

2. **Database connection errors**
   - Check DATABASE_URL format
   - Verify database server is running
   - Check network connectivity

3. **Frontend build errors**
   - Ensure all VITE_ variables are set
   - Check for undefined environment variables

4. **SSL certificate errors**
   - Verify certificate files exist
   - Check certificate expiration
   - Validate domain configuration

### Debug Mode

Enable debug mode for troubleshooting:

```bash
export DEBUG=true
export LOG_LEVEL=debug
```

This will provide detailed logging for configuration issues.

## Docker Configuration

When using Docker, environment variables can be set in:

1. **Docker Compose files** (`docker-compose.yml`)
2. **Environment files** (`.env` files)
3. **Runtime environment** (`docker run -e`)

Example Docker Compose configuration:

```yaml
services:
  app:
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    env_file:
      - .env.production
```

## Migration Between Environments

When promoting between environments:

1. **Export configuration** from source environment
2. **Update environment-specific values**
3. **Validate new configuration**
4. **Test database migrations**
5. **Deploy with new configuration**

Never copy production secrets to non-production environments.