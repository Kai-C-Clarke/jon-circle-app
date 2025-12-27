# fix_database.py
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'circle_memories.db')

def fix_database():
    """Add missing file_size column to media table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if file_size column exists
        cursor.execute("PRAGMA table_info(media)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("Current media table columns:", columns)
        
        if 'file_size' not in columns:
            print("Adding file_size column to media table...")
            cursor.execute("ALTER TABLE media ADD COLUMN file_size INTEGER")
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("✅ file_size column already exists.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()