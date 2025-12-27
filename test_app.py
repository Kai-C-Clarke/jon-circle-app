"""
Comprehensive Authentication Tests for Jon Circle App
Tests all authentication endpoints and security features.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database_improved import (
    init_db, get_db, create_user, get_user_by_username,
    lock_account, increment_failed_login
)
from auth import AuthService
from security_config import SecurityConfig


class AuthenticationTestCase(unittest.TestCase):
    """Test suite for authentication functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test database and app."""
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        # Create temporary database
        cls.db_fd, cls.db_path = tempfile.mkstemp()

        # Override database path for testing
        import database_improved
        database_improved.DB_PATH = cls.db_path

        init_db()

    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        os.close(cls.db_fd)
        os.unlink(cls.db_path)

    def setUp(self):
        """Set up test fixtures."""
        # Clear database before each test
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM refresh_tokens")
        cursor.execute("DELETE FROM audit_log")
        conn.commit()
        conn.close()

    def test_01_register_valid_user(self):
        """Test user registration with valid data."""
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Test@1234',
            'full_name': 'Test User'
        })

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')

    def test_02_register_missing_fields(self):
        """Test registration with missing required fields."""
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_03_register_weak_password(self):
        """Test registration with weak password."""
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'weak'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_04_register_duplicate_username(self):
        """Test registration with duplicate username."""
        # Create first user
        create_user('testuser', 'test1@example.com', 'Test@1234')

        # Try to create duplicate
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test2@example.com',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already exists', data['error'].lower())

    def test_05_register_duplicate_email(self):
        """Test registration with duplicate email."""
        # Create first user
        create_user('testuser1', 'test@example.com', 'Test@1234')

        # Try to create duplicate email
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser2',
            'email': 'test@example.com',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already exists', data['error'].lower())

    def test_06_register_invalid_email(self):
        """Test registration with invalid email format."""
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_07_login_valid_credentials(self):
        """Test login with valid credentials."""
        # Create user
        create_user('testuser', 'test@example.com', 'Test@1234')

        # Login
        response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertIn('user', data)

    def test_08_login_invalid_username(self):
        """Test login with non-existent username."""
        response = self.client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_09_login_invalid_password(self):
        """Test login with incorrect password."""
        # Create user
        create_user('testuser', 'test@example.com', 'Test@1234')

        # Login with wrong password
        response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'WrongPassword123!'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_10_login_missing_credentials(self):
        """Test login with missing credentials."""
        response = self.client.post('/api/auth/login', json={
            'username': 'testuser'
        })

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_11_account_lockout_after_failed_attempts(self):
        """Test account locks after max failed login attempts."""
        # Create user
        user_id = create_user('testuser', 'test@example.com', 'Test@1234')
        user = get_user_by_username('testuser')

        # Simulate failed attempts
        for i in range(SecurityConfig.MAX_LOGIN_ATTEMPTS):
            increment_failed_login(user['id'])

        # Lock account
        locked_until = datetime.utcnow() + SecurityConfig.ACCOUNT_LOCKOUT_DURATION
        lock_account(user['id'], locked_until.isoformat())

        # Try to login
        response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })

        self.assertEqual(response.status_code, 423)
        data = json.loads(response.data)
        self.assertIn('locked', data['error'].lower())

    def test_12_access_protected_route_without_token(self):
        """Test accessing protected route without authentication."""
        response = self.client.get('/api/auth/me')

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_13_access_protected_route_with_valid_token(self):
        """Test accessing protected route with valid token."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # Access protected route
        response = self.client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {access_token}'
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_14_access_protected_route_with_invalid_token(self):
        """Test accessing protected route with invalid token."""
        response = self.client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid-token'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_15_refresh_token_valid(self):
        """Test refreshing access token with valid refresh token."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        refresh_token = login_data['refresh_token']

        # Refresh token
        response = self.client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

    def test_16_refresh_token_invalid(self):
        """Test refreshing with invalid refresh token."""
        response = self.client.post('/api/auth/refresh', json={
            'refresh_token': 'invalid-token'
        })

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_17_refresh_token_missing(self):
        """Test refresh endpoint without token."""
        response = self.client.post('/api/auth/refresh', json={})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_18_logout_authenticated_user(self):
        """Test logout with authenticated user."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # Logout
        response = self.client.post('/api/auth/logout',
            headers={'Authorization': f'Bearer {access_token}'},
            json={}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')

    def test_19_logout_without_authentication(self):
        """Test logout without authentication."""
        response = self.client.post('/api/auth/logout', json={})

        self.assertEqual(response.status_code, 401)

    def test_20_change_password_valid(self):
        """Test changing password with valid credentials."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # Change password
        response = self.client.post('/api/auth/change-password',
            headers={'Authorization': f'Bearer {access_token}'},
            json={
                'old_password': 'Test@1234',
                'new_password': 'NewTest@5678'
            }
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')

    def test_21_change_password_wrong_old_password(self):
        """Test changing password with incorrect old password."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # Try to change with wrong old password
        response = self.client.post('/api/auth/change-password',
            headers={'Authorization': f'Bearer {access_token}'},
            json={
                'old_password': 'WrongPassword!',
                'new_password': 'NewTest@5678'
            }
        )

        self.assertEqual(response.status_code, 401)

    def test_22_change_password_weak_new_password(self):
        """Test changing to weak password."""
        # Create and login user
        create_user('testuser', 'test@example.com', 'Test@1234')
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # Try to change to weak password
        response = self.client.post('/api/auth/change-password',
            headers={'Authorization': f'Bearer {access_token}'},
            json={
                'old_password': 'Test@1234',
                'new_password': 'weak'
            }
        )

        self.assertEqual(response.status_code, 400)

    def test_23_password_hashing(self):
        """Test that passwords are properly hashed."""
        password = 'Test@1234'
        hashed = AuthService.hash_password(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(AuthService.verify_password(password, hashed))
        self.assertFalse(AuthService.verify_password('wrong', hashed))

    def test_24_jwt_token_generation(self):
        """Test JWT token generation and verification."""
        user_id = 1
        username = 'testuser'
        role = 'user'

        # Generate token
        token = AuthService.generate_access_token(user_id, username, role)
        self.assertIsNotNone(token)

        # Verify token
        payload = AuthService.verify_token(token, 'access')
        self.assertEqual(payload['user_id'], user_id)
        self.assertEqual(payload['username'], username)
        self.assertEqual(payload['role'], role)

    def test_25_invalid_authorization_header_format(self):
        """Test various invalid authorization header formats."""
        # Missing Bearer prefix
        response = self.client.get('/api/auth/me', headers={
            'Authorization': 'invalid-token'
        })
        self.assertEqual(response.status_code, 401)

        # Empty header
        response = self.client.get('/api/auth/me', headers={
            'Authorization': ''
        })
        self.assertEqual(response.status_code, 401)

    def test_26_user_data_in_response(self):
        """Test that sensitive data is not exposed in responses."""
        # Register user
        response = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Test@1234'
        })

        data = json.loads(response.data)

        # Ensure password hash is not in response
        self.assertNotIn('password', data['user'])
        self.assertNotIn('password_hash', data['user'])

        # Login and check response
        login_response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'Test@1234'
        })

        login_data = json.loads(login_response.data)
        self.assertNotIn('password', login_data['user'])
        self.assertNotIn('password_hash', login_data['user'])


def run_tests():
    """Run all tests and print results."""
    print("\n" + "="*70)
    print("RUNNING AUTHENTICATION TESTS")
    print("="*70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(AuthenticationTestCase)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
