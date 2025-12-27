"""
Authentication Module for Jon Circle App
Provides comprehensive authentication services including JWT tokens, password management,
user registration, login/logout, and security features.
"""

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, jsonify, g

from security_config import SecurityConfig
from logger_config import security_logger, get_client_ip
from database_improved import (
    get_db, get_user_by_username, get_user_by_email, get_user_by_id,
    create_user, update_user_last_login, increment_failed_login,
    lock_account, unlock_account, log_audit
)


class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid"""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked"""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired"""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid"""
    pass


class AuthService:
    """Main authentication service class"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=SecurityConfig.PASSWORD_HASH_ROUNDS)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            security_logger.log_error(f"Password verification error: {str(e)}")
            return False

    @staticmethod
    def generate_access_token(user_id: int, username: str, role: str = 'user') -> str:
        """Generate a JWT access token."""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'type': 'access',
            'exp': datetime.utcnow() + SecurityConfig.JWT_ACCESS_TOKEN_EXPIRES,
            'iat': datetime.utcnow()
        }

        token = jwt.encode(
            payload,
            SecurityConfig.JWT_SECRET_KEY,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )

        return token

    @staticmethod
    def generate_refresh_token(user_id: int, username: str) -> str:
        """Generate a JWT refresh token."""
        payload = {
            'user_id': user_id,
            'username': username,
            'type': 'refresh',
            'exp': datetime.utcnow() + SecurityConfig.JWT_REFRESH_TOKEN_EXPIRES,
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(32)  # Unique token ID
        }

        token = jwt.encode(
            payload,
            SecurityConfig.JWT_SECRET_KEY,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )

        # Store refresh token in database
        AuthService._store_refresh_token(user_id, token, payload['exp'])

        return token

    @staticmethod
    def _store_refresh_token(user_id: int, token: str, expires_at: datetime):
        """Store refresh token in database."""
        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO refresh_tokens (user_id, token, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, token, expires_at.isoformat(), datetime.utcnow().isoformat()))

            conn.commit()
            conn.close()
        except Exception as e:
            security_logger.log_error(f"Error storing refresh token: {str(e)}")

    @staticmethod
    def verify_token(token: str, token_type: str = 'access') -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        Returns payload if valid, raises exception otherwise.
        """
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET_KEY,
                algorithms=[SecurityConfig.JWT_ALGORITHM]
            )

            if payload.get('type') != token_type:
                raise InvalidTokenError(f"Invalid token type. Expected {token_type}")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
        """
        Generate new access token using refresh token.
        Returns (access_token, new_refresh_token)
        """
        try:
            # Verify refresh token
            payload = AuthService.verify_token(refresh_token, token_type='refresh')

            # Check if refresh token is revoked
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT revoked FROM refresh_tokens WHERE token = ?',
                (refresh_token,)
            )
            result = cursor.fetchone()
            conn.close()

            if not result or result['revoked']:
                raise InvalidTokenError("Refresh token has been revoked")

            # Get user data
            user = get_user_by_id(payload['user_id'])
            if not user or not user['is_active']:
                raise InvalidCredentialsError("User not found or inactive")

            # Generate new tokens
            new_access_token = AuthService.generate_access_token(
                user['id'], user['username'], user['role']
            )
            new_refresh_token = AuthService.generate_refresh_token(
                user['id'], user['username']
            )

            # Revoke old refresh token
            AuthService._revoke_refresh_token(refresh_token)

            # Log token refresh
            security_logger.log_token_refresh(
                user['id'],
                user['username'],
                get_client_ip(request) if request else None
            )

            return new_access_token, new_refresh_token

        except Exception as e:
            security_logger.log_invalid_token('refresh', str(e))
            raise

    @staticmethod
    def _revoke_refresh_token(token: str):
        """Revoke a refresh token."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE refresh_tokens SET revoked = 1 WHERE token = ?',
                (token,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            security_logger.log_error(f"Error revoking token: {str(e)}")

    @staticmethod
    def register_user(username: str, email: str, password: str,
                     full_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user.
        Returns user data if successful, raises exception otherwise.
        """
        # Validate username
        is_valid, error_msg = SecurityConfig.validate_password(password)
        if not is_valid:
            raise ValueError(error_msg)

        # Validate email
        from security_config import validate_email, validate_username
        if not validate_email(email):
            raise ValueError("Invalid email format")

        is_valid, error_msg = validate_username(username)
        if not is_valid:
            raise ValueError(error_msg)

        # Check if user exists
        if get_user_by_username(username):
            raise ValueError("Username already exists")

        if get_user_by_email(email):
            raise ValueError("Email already exists")

        # Create user
        user_id = create_user(username, email, password, full_name)

        if not user_id:
            raise Exception("Failed to create user")

        # Log registration
        ip_address = get_client_ip(request) if request else None
        security_logger.log_registration(user_id, username, email, ip_address)
        log_audit(user_id, 'USER_REGISTERED', ip_address)

        # Get user data
        user = get_user_by_id(user_id)

        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role']
        }

    @staticmethod
    def login(username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and generate tokens.
        Returns user data and tokens if successful, raises exception otherwise.
        """
        ip_address = get_client_ip(request) if request else None

        # Get user
        user = get_user_by_username(username)

        if not user:
            security_logger.log_login_failure(username, 'User not found', ip_address)
            raise InvalidCredentialsError("Invalid username or password")

        # Check if account is active
        if not user['is_active']:
            security_logger.log_login_failure(username, 'Account inactive', ip_address)
            raise AccountLockedError("Account is inactive")

        # Check if account is locked
        if user['account_locked_until']:
            locked_until = datetime.fromisoformat(user['account_locked_until'])
            if locked_until > datetime.utcnow():
                security_logger.log_login_failure(
                    username,
                    f"Account locked until {locked_until}",
                    ip_address
                )
                raise AccountLockedError(
                    f"Account is locked until {locked_until.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
            else:
                # Unlock account if lock period has passed
                unlock_account(user['id'])

        # Verify password
        if not AuthService.verify_password(password, user['password_hash']):
            # Increment failed login attempts
            increment_failed_login(user['id'])

            # Check if should lock account
            failed_attempts = user['failed_login_attempts'] + 1
            if failed_attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
                locked_until = datetime.utcnow() + SecurityConfig.ACCOUNT_LOCKOUT_DURATION
                lock_account(user['id'], locked_until.isoformat())
                security_logger.log_account_locked(
                    user['id'],
                    username,
                    f"Too many failed login attempts ({failed_attempts})"
                )
                raise AccountLockedError(
                    f"Account locked due to too many failed login attempts. "
                    f"Try again after {SecurityConfig.ACCOUNT_LOCKOUT_DURATION.total_seconds() / 60} minutes."
                )

            security_logger.log_login_failure(
                username,
                f"Invalid password (attempt {failed_attempts})",
                ip_address
            )
            raise InvalidCredentialsError("Invalid username or password")

        # Generate tokens
        access_token = AuthService.generate_access_token(
            user['id'], user['username'], user['role']
        )
        refresh_token = AuthService.generate_refresh_token(
            user['id'], user['username']
        )

        # Update last login
        update_user_last_login(user['id'])

        # Log successful login
        security_logger.log_login_success(user['id'], username, ip_address)
        log_audit(user['id'], 'USER_LOGIN', ip_address)

        return {
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role']
            },
            'access_token': access_token,
            'refresh_token': refresh_token
        }

    @staticmethod
    def logout(user_id: int, refresh_token: Optional[str] = None):
        """Logout user and revoke refresh token."""
        user = get_user_by_id(user_id)

        if user:
            ip_address = get_client_ip(request) if request else None
            security_logger.log_logout(user_id, user['username'], ip_address)
            log_audit(user_id, 'USER_LOGOUT', ip_address)

        # Revoke refresh token if provided
        if refresh_token:
            AuthService._revoke_refresh_token(refresh_token)

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str):
        """Change user password."""
        # Get user
        user = get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify old password
        if not AuthService.verify_password(old_password, user['password_hash']):
            raise InvalidCredentialsError("Current password is incorrect")

        # Validate new password
        is_valid, error_msg = SecurityConfig.validate_password(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        # Update password
        new_hash = AuthService.hash_password(new_password)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
            (new_hash, datetime.utcnow().isoformat(), user_id)
        )
        conn.commit()
        conn.close()

        # Log password change
        ip_address = get_client_ip(request) if request else None
        security_logger.log_password_change(user_id, user['username'], ip_address)
        log_audit(user_id, 'PASSWORD_CHANGED', ip_address)

    @staticmethod
    def generate_password_reset_token(email: str) -> str:
        """Generate password reset token."""
        user = get_user_by_email(email)

        if not user:
            # Don't reveal if email exists
            security_logger.log_password_reset_request(
                email,
                get_client_ip(request) if request else None
            )
            return secrets.token_urlsafe(32)

        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + SecurityConfig.PASSWORD_RESET_TOKEN_EXPIRES

        # Store token
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user['id'], token, expires_at.isoformat(), datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        # Log reset request
        ip_address = get_client_ip(request) if request else None
        security_logger.log_password_reset_request(email, ip_address)

        return token


def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'No authorization token provided'}), 401

        try:
            # Extract token (format: "Bearer <token>")
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization header format'}), 401

            token = parts[1]

            # Verify token
            payload = AuthService.verify_token(token, token_type='access')

            # Get user from database
            user = get_user_by_id(payload['user_id'])

            if not user or not user['is_active']:
                return jsonify({'error': 'User not found or inactive'}), 401

            # Store user in Flask g object for access in route
            g.current_user = user

        except TokenExpiredError:
            return jsonify({'error': 'Token has expired'}), 401
        except InvalidTokenError as e:
            security_logger.log_invalid_token('access', str(e), get_client_ip(request))
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            security_logger.log_error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401

        return f(*args, **kwargs)

    return decorated_function


def require_role(role: str):
    """Decorator to require specific role for routes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401

            if g.current_user['role'] != role and g.current_user['role'] != 'admin':
                security_logger.log_unauthorized_access(
                    request.path,
                    g.current_user['id'],
                    get_client_ip(request)
                )
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
