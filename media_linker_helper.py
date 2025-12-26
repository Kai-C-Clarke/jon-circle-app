#!/usr/bin/env python3
"""
Helper script for media linking operations
Use for testing, bulk operations, or data migration
"""

import sqlite3
import sys

def connect_db(db_path='circle.db'):
    """Connect to the database."""
    return sqlite3.connect(db_path)

def list_memories(conn):
    """List all memories with their IDs."""
    cursor = conn.execute('''
        SELECT id, substr(text, 1, 60), year, category 
        FROM memories 
        ORDER BY year DESC
    ''')
    
    print("\n=== MEMORIES ===")
    print(f"{'ID':<5} {'Year':<6} {'Category':<15} {'Text Preview':<60}")
    print("-" * 90)
    
    for row in cursor:
        mem_id, text, year, category = row
        year_str = str(year) if year else "N/A"
        category_str = category if category else "Uncategorized"
        print(f"{mem_id:<5} {year_str:<6} {category_str:<15} {text}...")

def list_media(conn):
    """List all media items."""
    cursor = conn.execute('''
        SELECT id, original_filename, year, title
        FROM media 
        ORDER BY year DESC
    ''')
    
    print("\n=== MEDIA ===")
    print(f"{'ID':<5} {'Year':<6} {'Title':<30} {'Filename':<40}")
    print("-" * 85)
    
    for row in cursor:
        media_id, filename, year, title = row
        year_str = str(year) if year else "N/A"
        title_str = title if title else "(no title)"
        print(f"{media_id:<5} {year_str:<6} {title_str:<30} {filename:<40}")

def link_media_to_memory(conn, memory_id, media_ids):
    """Link media items to a memory."""
    try:
        # Clear existing links
        conn.execute('DELETE FROM memory_media WHERE memory_id = ?', (memory_id,))
        
        # Add new links
        for order, media_id in enumerate(media_ids):
            conn.execute(
                'INSERT INTO memory_media (memory_id, media_id, display_order) VALUES (?, ?, ?)',
                (memory_id, media_id, order)
            )
        
        conn.commit()
        print(f"✓ Linked {len(media_ids)} media items to memory {memory_id}")
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"✗ Error linking media: {e}")
        return False

def show_memory_media(conn, memory_id):
    """Show all media linked to a memory."""
    cursor = conn.execute('''
        SELECT m.id, m.original_filename, m.title, mm.display_order
        FROM media m
        JOIN memory_media mm ON m.id = mm.media_id
        WHERE mm.memory_id = ?
        ORDER BY mm.display_order
    ''', (memory_id,))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"\nNo media linked to memory {memory_id}")
    else:
        print(f"\n=== MEDIA FOR MEMORY {memory_id} ===")
        print(f"{'Order':<7} {'Media ID':<10} {'Title':<30} {'Filename':<40}")
        print("-" * 90)
        
        for row in results:
            media_id, filename, title, order = row
            title_str = title if title else "(no title)"
            print(f"{order:<7} {media_id:<10} {title_str:<30} {filename:<40}")

def auto_link_by_year(conn, year_tolerance=2):
    """Automatically link media to memories by year proximity."""
    print(f"\n=== AUTO-LINKING BY YEAR (±{year_tolerance} years) ===")
    
    cursor = conn.execute('''
        SELECT id, text, year 
        FROM memories 
        WHERE year IS NOT NULL
    ''')
    
    memories = cursor.fetchall()
    
    for memory_id, text, memory_year in memories:
        # Find media within year range
        media_cursor = conn.execute('''
            SELECT id, year, title
            FROM media
            WHERE year IS NOT NULL 
              AND ABS(year - ?) <= ?
            ORDER BY ABS(year - ?), id
            LIMIT 2
        ''', (memory_year, year_tolerance, memory_year))
        
        media_matches = media_cursor.fetchall()
        
        if media_matches:
            media_ids = [m[0] for m in media_matches]
            
            print(f"\nMemory {memory_id} ({memory_year}): {text[:50]}...")
            print(f"  → Linking {len(media_ids)} photos: {', '.join(str(m[0]) for m in media_matches)}")
            
            link_media_to_memory(conn, memory_id, media_ids)

def unlink_all(conn):
    """Remove all media links."""
    try:
        cursor = conn.execute('SELECT COUNT(*) FROM memory_media')
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No links to remove")
            return
        
        confirm = input(f"Remove {count} links? (yes/no): ")
        if confirm.lower() == 'yes':
            conn.execute('DELETE FROM memory_media')
            conn.commit()
            print(f"✓ Removed {count} links")
        else:
            print("Cancelled")
    
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")

def interactive_link(conn):
    """Interactive linking interface."""
    print("\n=== INTERACTIVE MEDIA LINKING ===")
    
    list_memories(conn)
    
    memory_id = input("\nEnter memory ID to link media to: ")
    if not memory_id.isdigit():
        print("Invalid memory ID")
        return
    
    memory_id = int(memory_id)
    
    list_media(conn)
    
    media_ids = input("\nEnter media IDs to link (comma-separated, e.g., 1,3,5): ")
    try:
        media_ids = [int(x.strip()) for x in media_ids.split(',')]
        link_media_to_memory(conn, memory_id, media_ids)
        show_memory_media(conn, memory_id)
    except ValueError:
        print("Invalid media IDs")

def main():
    """Main menu."""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'circle.db'
    
    try:
        conn = connect_db(db_path)
        
        while True:
            print("\n" + "=" * 50)
            print("MEDIA LINKING HELPER")
            print("=" * 50)
            print("1. List all memories")
            print("2. List all media")
            print("3. Link media to memory (interactive)")
            print("4. Show media for a memory")
            print("5. Auto-link by year")
            print("6. Unlink all media")
            print("0. Exit")
            print("=" * 50)
            
            choice = input("\nChoice: ")
            
            if choice == '1':
                list_memories(conn)
            elif choice == '2':
                list_media(conn)
            elif choice == '3':
                interactive_link(conn)
            elif choice == '4':
                memory_id = input("Enter memory ID: ")
                if memory_id.isdigit():
                    show_memory_media(conn, int(memory_id))
            elif choice == '5':
                tolerance = input("Year tolerance (default 2): ") or "2"
                auto_link_by_year(conn, int(tolerance))
            elif choice == '6':
                unlink_all(conn)
            elif choice == '0':
                break
            else:
                print("Invalid choice")
        
        conn.close()
        print("\nGoodbye!")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
