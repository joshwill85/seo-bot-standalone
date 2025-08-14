#!/bin/bash

# Frontend Production Build Optimization Script
# This script optimizes the frontend build for production deployment

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "🚀 Starting frontend production build optimization..."

# Change to frontend directory
cd "$FRONTEND_DIR"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
npm run clean

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm ci --only=production
fi

# Run type checking
echo "🔍 Running type checks..."
npm run type-check

# Run linting
echo "🧼 Running linting..."
npm run lint

# Build for production
echo "🏗️  Building for production..."
NODE_ENV=production npm run build:production

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

# Optimize images if they exist
if command -v imagemin &> /dev/null; then
    echo "🖼️  Optimizing images..."
    imagemin dist/images/* --out-dir=dist/images --plugin=imagemin-mozjpeg --plugin=imagemin-pngquant
fi

# Generate gzip files for static assets
echo "📦 Generating gzip files..."
find dist -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.json" \) -exec gzip -9 -k {} \;

# Generate brotli files if brotli is available
if command -v brotli &> /dev/null; then
    echo "📦 Generating brotli files..."
    find dist -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.json" \) -exec brotli -9 -k {} \;
fi

# Calculate bundle sizes
echo "📊 Analyzing bundle sizes..."
if command -v du &> /dev/null; then
    echo "Total build size:"
    du -sh dist/
    
    echo "JavaScript bundle sizes:"
    find dist -name "*.js" -not -name "*.gz" -not -name "*.br" -exec du -h {} \; | sort -hr | head -10
    
    echo "CSS bundle sizes:"
    find dist -name "*.css" -not -name "*.gz" -not -name "*.br" -exec du -h {} \; | sort -hr
fi

# Security check - remove source maps in production if they exist
if [ "$NODE_ENV" = "production" ]; then
    echo "🔒 Removing source maps for security..."
    find dist -name "*.map" -delete
fi

# Generate build manifest
echo "📋 Generating build manifest..."
cat > dist/build-manifest.json << EOF
{
  "buildTime": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "version": "$(npm pkg get version | tr -d '"')",
  "environment": "production",
  "node": "$(node --version)",
  "npm": "$(npm --version)",
  "commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')",
  "branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF

# Validate HTML files
echo "✅ Validating HTML files..."
if command -v html5validator &> /dev/null; then
    html5validator --root dist/ --show-warnings || echo "⚠️  HTML validation warnings found"
fi

# Check for security issues in dependencies
echo "🔐 Checking for security vulnerabilities..."
npm audit --audit-level=high || echo "⚠️  Security vulnerabilities found"

# Performance check
echo "⚡ Performance check..."
MAIN_JS=$(find dist/js -name "main*.js" -not -name "*.gz" -not -name "*.br" | head -1)
MAIN_CSS=$(find dist/css -name "main*.css" -not -name "*.gz" -not -name "*.br" | head -1)

if [ -f "$MAIN_JS" ]; then
    JS_SIZE=$(stat -f%z "$MAIN_JS" 2>/dev/null || stat -c%s "$MAIN_JS" 2>/dev/null || echo "0")
    if [ "$JS_SIZE" -gt 1048576 ]; then  # 1MB
        echo "⚠️  Main JavaScript bundle is large: $(($JS_SIZE / 1024))KB"
    fi
fi

if [ -f "$MAIN_CSS" ]; then
    CSS_SIZE=$(stat -f%z "$MAIN_CSS" 2>/dev/null || stat -c%s "$MAIN_CSS" 2>/dev/null || echo "0")
    if [ "$CSS_SIZE" -gt 102400 ]; then  # 100KB
        echo "⚠️  Main CSS bundle is large: $(($CSS_SIZE / 1024))KB"
    fi
fi

# Create deployment-ready archive
echo "📦 Creating deployment archive..."
cd dist
tar -czf "../seo-bot-frontend-$(date +%Y%m%d-%H%M%S).tar.gz" .
cd ..

echo "✅ Frontend build optimization completed!"
echo "📁 Build output: $FRONTEND_DIR/dist"
echo "📦 Archive created: $FRONTEND_DIR/seo-bot-frontend-*.tar.gz"

# Display deployment instructions
echo ""
echo "🚀 Deployment Instructions:"
echo "1. Upload the contents of 'dist/' to your web server"
echo "2. Configure your server to serve gzipped/brotli files"
echo "3. Set appropriate cache headers for static assets"
echo "4. Ensure fallback to index.html for SPA routing"

# Optional: Upload to CDN or S3
if [ ! -z "$AWS_S3_BUCKET" ]; then
    echo "☁️  Uploading to S3..."
    aws s3 sync dist/ "s3://$AWS_S3_BUCKET/" --delete --cache-control "max-age=31536000" --exclude "*.html" --exclude "*.json"
    aws s3 sync dist/ "s3://$AWS_S3_BUCKET/" --cache-control "max-age=0" --include "*.html" --include "*.json"
    echo "✅ S3 upload completed"
fi