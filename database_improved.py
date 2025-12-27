"""
Enhanced Database Module with Authentication Support
Extends the original database.py with user authentication capabilities.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'circle_memories.db')


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with all tables including authentication."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users table for authentication
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'user',
        is_active INTEGER DEFAULT 1,
        is_verified INTEGER DEFAULT 0,
        failed_login_attempts INTEGER DEFAULT 0,
        account_locked_until TEXT,
        last_login TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )''')

    # Password reset tokens
    cursor.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    # Email verification tokens
    cursor.execute('''CREATE TABLE IF NOT EXISTS email_verification_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    # Refresh tokens for JWT
    cursor.execute('''CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        revoked INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    # Audit log for security events
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # User profile (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        birth_date TEXT,
        family_role TEXT,
        birth_place TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Memories (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT NOT NULL,
        category TEXT,
        memory_date TEXT,
        year INTEGER,
        people TEXT,
        places TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Media (from original database.py with file_size)
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT NOT NULL,
        original_filename TEXT,
        file_type TEXT,
        file_size INTEGER,
        title TEXT,
        description TEXT,
        memory_date TEXT,
        year INTEGER,
        people TEXT,
        uploaded_by TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Comments (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        user_id INTEGER,
        author_name TEXT,
        author_relation TEXT,
        comment_text TEXT,
        created_at TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Audio transcriptions (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS audio_transcriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        audio_filename TEXT,
        transcription_text TEXT,
        confidence REAL,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Tags for enhanced search (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        tag TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
    )''')

    # People mentioned (from original database.py)
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory_people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        person_name TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
    )''')

    # Create indices for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)')

    conn.commit()
    conn.close()
    print(f"✓ Database initialized at: {DB_PATH}")


def migrate_db():
    """Add new authentication columns to existing tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        # If users table doesn't exist, run full init
        if 'users' not in existing_tables:
            conn.close()
            init_db()
            return

        # Add user_id to existing tables if they don't have it
        tables_to_migrate = ['memories', 'media', 'comments', 'audio_transcriptions', 'user_profile']

        for table in tables_to_migrate:
            if table in existing_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]

                if 'user_id' not in columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
                    print(f"✓ Added user_id column to {table} table")

        # Add file_size to media if it doesn't exist
        if 'media' in existing_tables:
            cursor.execute("PRAGMA table_info(media)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'file_size' not in columns:
                cursor.execute("ALTER TABLE media ADD COLUMN file_size INTEGER")
                print("✓ Added file_size column to media table")

        conn.commit()
        conn.close()
        print("✓ Database migration completed successfully")

    except Exception as e:
        print(f"Migration error: {e}")
        raise


# User CRUD Operations
def create_user(username: str, email: str, password: str, full_name: Optional[str] = None,
                role: str = 'user') -> Optional[int]:
    """
    Create a new user with hashed password.
    Returns user_id if successful, None otherwise.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, role, datetime.utcnow().isoformat()))

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return user_id

    except sqlite3.IntegrityError as e:
        print(f"User creation failed: {e}")
        return None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def update_user_last_login(user_id: int):
    """Update user's last login timestamp."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET last_login = ?, failed_login_attempts = 0, updated_at = ?
            WHERE id = ?
        ''', (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating last login: {e}")


def increment_failed_login(user_id: int):
    """Increment failed login attempts."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET failed_login_attempts = failed_login_attempts + 1, updated_at = ?
            WHERE id = ?
        ''', (datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error incrementing failed login: {e}")


def lock_account(user_id: int, locked_until: str):
    """Lock user account until specified time."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET account_locked_until = ?, updated_at = ?
            WHERE id = ?
        ''', (locked_until, datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error locking account: {e}")


def unlock_account(user_id: int):
    """Unlock user account."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET account_locked_until = NULL, failed_login_attempts = 0, updated_at = ?
            WHERE id = ?
        ''', (datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error unlocking account: {e}")


# Audit logging
def log_audit(user_id: Optional[int], action: str, ip_address: Optional[str] = None,
              user_agent: Optional[str] = None, details: Optional[str] = None):
    """Log security audit event."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, ip_address, user_agent, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, action, ip_address, user_agent, details, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging audit: {e}")


if __name__ == '__main__':
    # Initialize database when run directly
    init_db()
