"""
Logging Configuration for Jon Circle App
Provides structured logging for authentication, security events, and application monitoring.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional
import json


class SecurityLogger:
    """Specialized logger for security and authentication events"""

    def __init__(self, name: str = 'jon_circle_security'):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Configure logger with appropriate handlers and formatters"""
        # Set base level
        self.logger.setLevel(logging.DEBUG if os.environ.get('DEBUG') == 'true' else logging.INFO)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Console Handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File Handler for all logs
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # General application log
        app_log_file = os.path.join(log_dir, 'app.log')
        app_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        app_handler.setLevel(logging.DEBUG)
        app_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        app_handler.setFormatter(app_formatter)
        self.logger.addHandler(app_handler)

        # Security-specific log
        security_log_file = os.path.join(log_dir, 'security.log')
        security_handler = TimedRotatingFileHandler(
            security_log_file,
            when='midnight',
            interval=1,
            backupCount=30
        )
        security_handler.setLevel(logging.WARNING)
        security_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        security_handler.setFormatter(security_formatter)
        self.logger.addHandler(security_handler)

    def _log_event(self, level: str, event_type: str, message: str, **kwargs):
        """Log a structured event with additional context"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
            **kwargs
        }

        log_message = json.dumps(log_data)

        if level == 'debug':
            self.logger.debug(log_message)
        elif level == 'info':
            self.logger.info(log_message)
        elif level == 'warning':
            self.logger.warning(log_message)
        elif level == 'error':
            self.logger.error(log_message)
        elif level == 'critical':
            self.logger.critical(log_message)

    # Authentication Events
    def log_login_success(self, user_id: int, username: str, ip_address: Optional[str] = None):
        """Log successful login"""
        self._log_event(
            'info',
            'LOGIN_SUCCESS',
            f'User {username} logged in successfully',
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )

    def log_login_failure(self, username: str, reason: str, ip_address: Optional[str] = None):
        """Log failed login attempt"""
        self._log_event(
            'warning',
            'LOGIN_FAILURE',
            f'Failed login attempt for {username}: {reason}',
            username=username,
            reason=reason,
            ip_address=ip_address
        )

    def log_logout(self, user_id: int, username: str, ip_address: Optional[str] = None):
        """Log user logout"""
        self._log_event(
            'info',
            'LOGOUT',
            f'User {username} logged out',
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )

    def log_registration(self, user_id: int, username: str, email: str, ip_address: Optional[str] = None):
        """Log new user registration"""
        self._log_event(
            'info',
            'USER_REGISTRATION',
            f'New user registered: {username}',
            user_id=user_id,
            username=username,
            email=email,
            ip_address=ip_address
        )

    def log_password_change(self, user_id: int, username: str, ip_address: Optional[str] = None):
        """Log password change"""
        self._log_event(
            'info',
            'PASSWORD_CHANGE',
            f'Password changed for user {username}',
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )

    def log_password_reset_request(self, email: str, ip_address: Optional[str] = None):
        """Log password reset request"""
        self._log_event(
            'info',
            'PASSWORD_RESET_REQUEST',
            f'Password reset requested for {email}',
            email=email,
            ip_address=ip_address
        )

    def log_token_refresh(self, user_id: int, username: str, ip_address: Optional[str] = None):
        """Log token refresh"""
        self._log_event(
            'info',
            'TOKEN_REFRESH',
            f'Token refreshed for user {username}',
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )

    # Security Events
    def log_account_locked(self, user_id: int, username: str, reason: str):
        """Log account lockout"""
        self._log_event(
            'warning',
            'ACCOUNT_LOCKED',
            f'Account locked for {username}: {reason}',
            user_id=user_id,
            username=username,
            reason=reason
        )

    def log_suspicious_activity(self, description: str, user_id: Optional[int] = None,
                               username: Optional[str] = None, ip_address: Optional[str] = None):
        """Log suspicious activity"""
        self._log_event(
            'warning',
            'SUSPICIOUS_ACTIVITY',
            description,
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )

    def log_rate_limit_exceeded(self, endpoint: str, ip_address: Optional[str] = None):
        """Log rate limit violation"""
        self._log_event(
            'warning',
            'RATE_LIMIT_EXCEEDED',
            f'Rate limit exceeded for endpoint: {endpoint}',
            endpoint=endpoint,
            ip_address=ip_address
        )

    def log_invalid_token(self, token_type: str, reason: str, ip_address: Optional[str] = None):
        """Log invalid token usage"""
        self._log_event(
            'warning',
            'INVALID_TOKEN',
            f'Invalid {token_type} token: {reason}',
            token_type=token_type,
            reason=reason,
            ip_address=ip_address
        )

    def log_unauthorized_access(self, endpoint: str, user_id: Optional[int] = None,
                                ip_address: Optional[str] = None):
        """Log unauthorized access attempt"""
        self._log_event(
            'warning',
            'UNAUTHORIZED_ACCESS',
            f'Unauthorized access attempt to {endpoint}',
            endpoint=endpoint,
            user_id=user_id,
            ip_address=ip_address
        )

    # Application Events
    def log_error(self, error_message: str, exception: Optional[Exception] = None,
                  user_id: Optional[int] = None):
        """Log application error"""
        self._log_event(
            'error',
            'APPLICATION_ERROR',
            error_message,
            user_id=user_id,
            exception=str(exception) if exception else None
        )

    def log_debug(self, message: str, **kwargs):
        """Log debug information"""
        self._log_event('debug', 'DEBUG', message, **kwargs)

    def log_info(self, message: str, **kwargs):
        """Log informational message"""
        self._log_event('info', 'INFO', message, **kwargs)


# Global logger instance
security_logger = SecurityLogger()


def get_client_ip(request) -> str:
    """Extract client IP address from Flask request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or 'unknown'
