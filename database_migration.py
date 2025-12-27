# database_migration.py - Add audio support to memories table

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'circle_memories.db')

def migrate_add_audio_to_memories():
    """Add audio_filename column to memories table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(memories)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'audio_filename' not in columns:
            print("Adding audio_filename column to memories table...")
            cursor.execute('''ALTER TABLE memories 
                             ADD COLUMN audio_filename TEXT''')
            conn.commit()
            print("✓ Migration complete: audio_filename added")
        else:
            print("✓ Column audio_filename already exists")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_add_audio_to_memories()
