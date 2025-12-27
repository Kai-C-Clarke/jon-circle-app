"""
Security Configuration for Jon Circle App
Handles all security-related settings including JWT, password hashing, and rate limiting.
"""

import os
from datetime import timedelta
from typing import Dict, Any

class SecurityConfig:
    """Central configuration for all security settings"""

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Password Configuration
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_HASH_ROUNDS = 12  # bcrypt rounds

    # Session Configuration
    SESSION_COOKIE_SECURE = True  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT = False

    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    LOGIN_RATE_LIMIT = "5 per minute"  # Max 5 login attempts per minute
    REGISTER_RATE_LIMIT = "3 per hour"  # Max 3 registrations per hour
    API_RATE_LIMIT = "100 per minute"  # General API rate limit

    # Account Security
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)
    PASSWORD_RESET_TOKEN_EXPIRES = timedelta(hours=1)
    EMAIL_VERIFICATION_TOKEN_EXPIRES = timedelta(days=1)

    # CORS Configuration
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS_ALLOW_CREDENTIALS = True

    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'"
    }

    # Environment
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    DEBUG = ENVIRONMENT == 'development'

    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        """
        Validate password against security requirements
        Returns: (is_valid, error_message)
        """
        if len(password) < cls.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {cls.PASSWORD_MIN_LENGTH} characters"

        if cls.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if cls.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if cls.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        if cls.PASSWORD_REQUIRE_SPECIAL:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                return False, "Password must contain at least one special character"

        return True, ""

    @classmethod
    def get_jwt_config(cls) -> Dict[str, Any]:
        """Get JWT configuration dictionary"""
        return {
            'secret_key': cls.JWT_SECRET_KEY,
            'algorithm': cls.JWT_ALGORITHM,
            'access_token_expires': cls.JWT_ACCESS_TOKEN_EXPIRES,
            'refresh_token_expires': cls.JWT_REFRESH_TOKEN_EXPIRES
        }

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return cls.ENVIRONMENT == 'production'

    @classmethod
    def get_cookie_config(cls) -> Dict[str, Any]:
        """Get session cookie configuration"""
        return {
            'secure': cls.SESSION_COOKIE_SECURE if cls.is_production() else False,
            'httponly': cls.SESSION_COOKIE_HTTPONLY,
            'samesite': cls.SESSION_COOKIE_SAMESITE
        }


# Security utility functions
def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent injection attacks
    """
    if not input_string:
        return ""

    # Trim to max length
    sanitized = input_string[:max_length]

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    return sanitized.strip()


def validate_email(email: str) -> bool:
    """
    Basic email validation
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format
    Returns: (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be less than 50 characters"

    if not username[0].isalpha():
        return False, "Username must start with a letter"

    if not all(c.isalnum() or c in '_-' for c in username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"

    return True, ""
