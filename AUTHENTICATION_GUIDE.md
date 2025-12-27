# Authentication Guide - Jon Circle App

Complete guide for implementing and using the authentication system in Jon Circle App.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
4. [Security Features](#security-features)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Jon Circle App authentication system provides:

- **JWT-based authentication** with access and refresh tokens
- **Secure password hashing** using bcrypt
- **Account security** with lockout after failed attempts
- **Role-based access control** (user, admin)
- **Comprehensive logging** for security events
- **Password strength validation**
- **Token refresh mechanism**

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
JWT_SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=true
```

**Important:** Change `JWT_SECRET_KEY` to a secure random string in production.

### 3. Initialize Database

```bash
python database_improved.py
```

### 4. Create Admin User

```bash
python create_admin.py
```

Follow the prompts to create an administrator account.

### 5. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

---

## API Endpoints

### 1. Register User

**POST** `/api/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user"
  }
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

---

### 2. Login

**POST** `/api/auth/login`

Authenticate and receive access/refresh tokens.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `423 Locked` - Account locked due to failed attempts

---

### 3. Get Current User

**GET** `/api/auth/me`

Get authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": 1,
    "last_login": "2025-12-27T10:30:00",
    "created_at": "2025-12-20T08:15:00"
  }
}
```

---

### 4. Refresh Token

**POST** `/api/auth/refresh`

Get new access/refresh tokens using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Note:** Old refresh token is automatically revoked.

---

### 5. Change Password

**POST** `/api/auth/change-password`

Change user password.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "old_password": "SecurePass123!",
  "new_password": "NewSecurePass456!"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Password changed successfully"
}
```

---

### 6. Logout

**POST** `/api/auth/logout`

Logout and revoke refresh token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body (optional):**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Logout successful"
}
```

---

## Security Features

### 1. Password Security

- **Bcrypt hashing** with 12 rounds
- **Password strength validation**
- **No plain text storage**

### 2. Account Lockout

- **5 failed login attempts** trigger account lock
- **30-minute lockout period**
- Automatic unlock after period expires

### 3. JWT Tokens

- **Access tokens** expire after 24 hours
- **Refresh tokens** expire after 30 days
- Tokens include user ID, username, and role

### 4. Security Logging

All authentication events are logged:
- Login attempts (success/failure)
- Registration events
- Password changes
- Token refreshes
- Account lockouts
- Suspicious activity

Logs are stored in:
- `logs/app.log` - All application logs
- `logs/security.log` - Security-specific events

### 5. Audit Trail

Database audit log tracks:
- User actions
- IP addresses
- User agents
- Timestamps

---

## Configuration

### Security Settings

Edit `security_config.py` to customize:

```python
# JWT Configuration
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Password Requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGITS = True
PASSWORD_REQUIRE_SPECIAL = True

# Account Security
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)
```

### Environment Variables

```bash
# Required
JWT_SECRET_KEY=your-secret-key-here

# Optional
ENVIRONMENT=production          # or development
DEBUG=false                     # true for development
CORS_ORIGINS=https://example.com
```

---

## Using Authentication in Your Code

### Protecting Routes

Use the `@require_auth` decorator:

```python
from auth import require_auth
from flask import g

@app.route('/api/protected')
@require_auth
def protected_route():
    user = g.current_user  # Access authenticated user
    return jsonify({'message': f'Hello {user["username"]}'})
```

### Role-Based Access

Use the `@require_role` decorator:

```python
from auth import require_auth, require_role

@app.route('/api/admin/users')
@require_auth
@require_role('admin')
def admin_only():
    return jsonify({'message': 'Admin access granted'})
```

### Manual Authentication

```python
from auth import AuthService

# Authenticate user
result = AuthService.login('username', 'password')
access_token = result['access_token']

# Verify token
payload = AuthService.verify_token(access_token, 'access')
user_id = payload['user_id']
```

---

## Testing

### Run All Tests

```bash
python test_app.py
```

This runs 26 comprehensive tests covering:
- User registration
- Login/logout
- Token management
- Password changes
- Account lockout
- Security validations

### Example Test Output

```
RUNNING AUTHENTICATION TESTS
======================================================================

test_01_register_valid_user ... ok
test_02_register_missing_fields ... ok
test_03_register_weak_password ... ok
...
test_26_user_data_in_response ... ok

======================================================================
TEST SUMMARY
======================================================================
Tests run: 26
Successes: 26
Failures: 0
Errors: 0
======================================================================
```

---

## Client Integration Examples

### JavaScript/Fetch Example

```javascript
// Register
const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'john_doe',
    email: 'john@example.com',
    password: 'SecurePass123!',
    full_name: 'John Doe'
  })
});

// Login
const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'john_doe',
    password: 'SecurePass123!'
  })
});

const { access_token, refresh_token } = await loginResponse.json();

// Store tokens
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// Use token for authenticated requests
const response = await fetch('http://localhost:5000/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

### Python/Requests Example

```python
import requests

# Register
response = requests.post('http://localhost:5000/api/auth/register', json={
    'username': 'john_doe',
    'email': 'john@example.com',
    'password': 'SecurePass123!',
    'full_name': 'John Doe'
})

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'username': 'john_doe',
    'password': 'SecurePass123!'
})

data = response.json()
access_token = data['access_token']

# Authenticated request
response = requests.get('http://localhost:5000/api/auth/me', headers={
    'Authorization': f'Bearer {access_token}'
})
```

---

## Troubleshooting

### Issue: "Invalid token" error

**Solution:**
- Check token hasn't expired
- Verify Authorization header format: `Bearer <token>`
- Ensure JWT_SECRET_KEY matches between sessions

### Issue: Account locked

**Solution:**
- Wait 30 minutes for automatic unlock
- Or manually unlock in database:
  ```sql
  UPDATE users SET account_locked_until = NULL, failed_login_attempts = 0 WHERE username = 'username';
  ```

### Issue: "Username already exists"

**Solution:**
- Choose a different username
- Or check if user already exists:
  ```sql
  SELECT * FROM users WHERE username = 'username';
  ```

### Issue: Weak password error

**Solution:**
Ensure password meets all requirements:
- Minimum 8 characters
- Contains uppercase letter
- Contains lowercase letter
- Contains digit
- Contains special character

### Issue: Tests failing

**Solution:**
1. Check all dependencies installed: `pip install -r requirements.txt`
2. Ensure no other app instance running on port 5000
3. Delete `circle_memories.db` and reinitialize
4. Check logs in `logs/` directory

---

## Production Deployment Checklist

- [ ] Set strong `JWT_SECRET_KEY` (use `secrets.token_urlsafe(32)`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS for your domain
- [ ] Set up log rotation
- [ ] Regular database backups
- [ ] Monitor security logs
- [ ] Use environment variables (not hardcoded secrets)
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting

---

## Support

For issues or questions:
1. Check this guide
2. Review logs in `logs/` directory
3. Run tests: `python test_app.py`
4. Check database: `sqlite3 circle_memories.db`

---

**Version:** 1.0.0
**Last Updated:** December 2025
**License:** MIT
