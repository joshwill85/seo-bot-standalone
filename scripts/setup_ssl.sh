#!/bin/bash

# SSL Certificate Setup Script for SEO Bot
# Supports both Let's Encrypt and self-signed certificates

set -e

# Configuration
DOMAIN=${1:-"localhost"}
EMAIL=${2:-"admin@example.com"}
CERT_DIR="/etc/nginx/ssl"
LETSENCRYPT_DIR="/etc/letsencrypt"
ENVIRONMENT=${ENVIRONMENT:-"development"}

echo "Setting up SSL certificates for domain: $DOMAIN"
echo "Environment: $ENVIRONMENT"

# Create certificate directory
mkdir -p "$CERT_DIR"

if [ "$ENVIRONMENT" = "production" ] && [ "$DOMAIN" != "localhost" ]; then
    echo "Setting up Let's Encrypt certificates for production..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y certbot python3-certbot-nginx
        elif command -v yum &> /dev/null; then
            yum install -y certbot python3-certbot-nginx
        else
            echo "Please install certbot manually"
            exit 1
        fi
    fi
    
    # Stop nginx temporarily for standalone authentication
    if systemctl is-active --quiet nginx; then
        systemctl stop nginx
        RESTART_NGINX=true
    fi
    
    # Generate certificate
    certbot certonly \
        --standalone \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --domain "$DOMAIN" \
        --non-interactive
    
    # Link certificates to nginx directory
    ln -sf "$LETSENCRYPT_DIR/live/$DOMAIN/fullchain.pem" "$CERT_DIR/cert.pem"
    ln -sf "$LETSENCRYPT_DIR/live/$DOMAIN/privkey.pem" "$CERT_DIR/key.pem"
    
    # Set up auto-renewal
    if ! crontab -l | grep -q certbot; then
        (crontab -l 2>/dev/null; echo "0 2 * * 0 certbot renew --quiet && systemctl reload nginx") | crontab -
        echo "Set up automatic certificate renewal"
    fi
    
    # Restart nginx if it was running
    if [ "$RESTART_NGINX" = "true" ]; then
        systemctl start nginx
    fi
    
    echo "Let's Encrypt certificate setup completed!"
    
else
    echo "Setting up self-signed certificates for development..."
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    # Set proper permissions
    chmod 600 "$CERT_DIR/key.pem"
    chmod 644 "$CERT_DIR/cert.pem"
    
    echo "Self-signed certificate setup completed!"
    echo "WARNING: Self-signed certificates are not trusted by browsers in production"
fi

# Verify certificate
echo "Certificate information:"
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"

echo "SSL setup completed successfully!"