#!/bin/bash

# SSL Certificate Renewal Script
# Automatically renews Let's Encrypt certificates

set -e

echo "Starting SSL certificate renewal process..."

# Check if certbot is available
if ! command -v certbot &> /dev/null; then
    echo "Error: certbot is not installed"
    exit 1
fi

# Renew certificates
echo "Attempting to renew certificates..."
certbot renew --quiet

# Check if any certificates were renewed
if [ $? -eq 0 ]; then
    echo "Certificate renewal check completed"
    
    # Test nginx configuration
    nginx -t
    
    if [ $? -eq 0 ]; then
        echo "Nginx configuration is valid, reloading..."
        systemctl reload nginx
        echo "Nginx reloaded successfully"
    else
        echo "Error: Nginx configuration test failed"
        exit 1
    fi
else
    echo "Error during certificate renewal"
    exit 1
fi

# Log renewal status
echo "SSL certificate renewal completed at $(date)" >> /var/log/ssl-renewal.log

echo "SSL renewal process completed successfully!"