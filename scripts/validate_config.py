#!/usr/bin/env python3
"""
Environment Configuration Validator for SEO Bot
Validates that all required environment variables are set for each environment.
"""

import os
import sys
from typing import Dict, List, Set
from pathlib import Path


class ConfigValidator:
    """Validates environment configuration."""
    
    # Required variables for all environments
    REQUIRED_COMMON = {
        'NODE_ENV',
        'ENVIRONMENT', 
        'APP_NAME',
        'APP_URL',
        'DATABASE_URL',
        'SECRET_KEY',
        'JWT_SECRET_KEY'
    }
    
    # Required for production only
    REQUIRED_PRODUCTION = {
        'VITE_SUPABASE_URL',
        'VITE_SUPABASE_ANON_KEY',
        'SMTP_HOST',
        'SMTP_PORT',
        'REDIS_URL',
        'ALLOWED_HOSTS',
        'CORS_ORIGINS'
    }
    
    # Recommended for production
    RECOMMENDED_PRODUCTION = {
        'SENTRY_DSN',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'BACKUP_S3_BUCKET',
        'OPENAI_API_KEY',
        'GOOGLE_API_KEY',
        'SERP_API_KEY'
    }
    
    # Security-sensitive variables that should be strong
    SECURITY_VARS = {
        'SECRET_KEY': 32,  # Minimum length
        'JWT_SECRET_KEY': 32,
        'DATABASE_URL': 20
    }
    
    def __init__(self, env_file: str = None):
        """Initialize with optional environment file."""
        self.env_file = env_file
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        if env_file:
            self.load_env_file(env_file)
    
    def load_env_file(self, env_file: str):
        """Load environment variables from file."""
        env_path = Path(env_file)
        if not env_path.exists():
            self.errors.append(f"Environment file not found: {env_file}")
            return
        
        with open(env_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if value:  # Only set non-empty values
                        os.environ[key] = value
    
    def validate_required_vars(self, environment: str) -> bool:
        """Validate that all required variables are set."""
        missing_vars = []
        required_vars = self.REQUIRED_COMMON.copy()
        
        if environment == 'production':
            required_vars.update(self.REQUIRED_PRODUCTION)
        
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.errors.append(f"Missing required variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    def validate_security_vars(self) -> bool:
        """Validate security-sensitive variables."""
        valid = True
        
        for var, min_length in self.SECURITY_VARS.items():
            value = os.environ.get(var, '')
            if len(value) < min_length:
                self.errors.append(f"{var} must be at least {min_length} characters long")
                valid = False
            
            # Check for common weak values
            if var in ['SECRET_KEY', 'JWT_SECRET_KEY']:
                weak_patterns = ['password', '123456', 'secret', 'key', 'dev', 'test']
                if any(pattern in value.lower() for pattern in weak_patterns):
                    self.warnings.append(f"{var} appears to use a weak pattern")
        
        return valid
    
    def validate_database_url(self) -> bool:
        """Validate database URL format."""
        db_url = os.environ.get('DATABASE_URL', '')
        
        if not db_url.startswith(('postgresql://', 'postgres://', 'sqlite:///')):
            self.errors.append("DATABASE_URL must start with postgresql://, postgres://, or sqlite:///")
            return False
        
        # Check for production database in non-production environments
        environment = os.environ.get('ENVIRONMENT', '')
        if environment != 'production' and '_prod' in db_url:
            self.warnings.append("Non-production environment using production database")
        
        return True
    
    def validate_urls(self) -> bool:
        """Validate URL formats."""
        url_vars = ['APP_URL', 'VITE_APP_URL', 'VITE_SUPABASE_URL']
        valid = True
        
        for var in url_vars:
            url = os.environ.get(var, '')
            if url and not url.startswith(('http://', 'https://')):
                self.errors.append(f"{var} must be a valid URL starting with http:// or https://")
                valid = False
        
        # Check for localhost in production
        environment = os.environ.get('ENVIRONMENT', '')
        if environment == 'production':
            for var in url_vars:
                url = os.environ.get(var, '')
                if 'localhost' in url or '127.0.0.1' in url:
                    self.warnings.append(f"{var} uses localhost in production environment")
        
        return valid
    
    def check_recommended_vars(self, environment: str):
        """Check for recommended variables."""
        if environment == 'production':
            missing_recommended = []
            for var in self.RECOMMENDED_PRODUCTION:
                if not os.environ.get(var):
                    missing_recommended.append(var)
            
            if missing_recommended:
                self.warnings.append(f"Missing recommended production variables: {', '.join(missing_recommended)}")
    
    def validate_environment_consistency(self):
        """Validate consistency between environment variables."""
        node_env = os.environ.get('NODE_ENV', '')
        environment = os.environ.get('ENVIRONMENT', '')
        
        if node_env and environment and node_env != environment:
            self.warnings.append(f"NODE_ENV ({node_env}) and ENVIRONMENT ({environment}) don't match")
        
        # Check SSL settings for production
        if environment == 'production':
            ssl_vars = ['SECURE_SSL_REDIRECT', 'SECURE_COOKIES', 'SESSION_COOKIE_SECURE']
            for var in ssl_vars:
                value = os.environ.get(var, '').lower()
                if value not in ['true', '1', 'yes']:
                    self.warnings.append(f"{var} should be true in production")
    
    def validate(self, environment: str = None) -> bool:
        """Run all validations."""
        if not environment:
            environment = os.environ.get('ENVIRONMENT', 'development')
        
        print(f"Validating configuration for environment: {environment}")
        
        # Run all validation checks
        checks = [
            self.validate_required_vars(environment),
            self.validate_security_vars(),
            self.validate_database_url(),
            self.validate_urls()
        ]
        
        # Non-critical checks
        self.check_recommended_vars(environment)
        self.validate_environment_consistency()
        
        # Print results
        if self.errors:
            print("\n❌ Configuration Errors:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        is_valid = all(checks) and not self.errors
        
        if is_valid:
            print("\n✅ Configuration validation passed!")
        else:
            print("\n❌ Configuration validation failed!")
        
        return is_valid


def main():
    """Main validation function."""
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
        validator = ConfigValidator(env_file)
        environment = os.path.basename(env_file).replace('.env.', '').replace('.env', 'development')
    else:
        validator = ConfigValidator()
        environment = os.environ.get('ENVIRONMENT', 'development')
    
    is_valid = validator.validate(environment)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()