# database.py - Database setup and connection
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'circle_memories.db')

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User profile
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        birth_date TEXT,
        family_role TEXT,
        birth_place TEXT,
        created_at TEXT
    )''')
    
    # Memories
    cursor.execute('''CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        category TEXT,
        memory_date TEXT,
        year INTEGER,
        people TEXT,
        places TEXT,
        created_at TEXT
    )''')
    
    # Media - FIXED: Added file_size column
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        created_at TEXT
    )''')
    
    # Comments (Love notes)
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        author_name TEXT,
        author_relation TEXT,
        comment_text TEXT,
        created_at TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id)
    )''')
    
    # Audio transcriptions
    cursor.execute('''CREATE TABLE IF NOT EXISTS audio_transcriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audio_filename TEXT,
        transcription_text TEXT,
        confidence REAL,
        created_at TEXT
    )''')
    
    # Tags for enhanced search
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        tag TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id)
    )''')
    
    # People mentioned
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory_people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        person_name TEXT,
        FOREIGN KEY (memory_id) REFERENCES memories(id)
    )''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

def migrate_db():
    """Add file_size column if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if file_size column exists
        cursor.execute("PRAGMA table_info(media)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'file_size' not in columns:
            cursor.execute("ALTER TABLE media ADD COLUMN file_size INTEGER")
            conn.commit()
            print("✓ Added file_size column to media table")
        
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")