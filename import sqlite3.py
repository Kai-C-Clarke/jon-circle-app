import sqlite3
from utils import categorize_memory

conn = sqlite3.connect('circle_memories.db')
cursor = conn.cursor()

# Get all memories
cursor.execute('SELECT id, text, year FROM memories')
memories = cursor.fetchall()

for mem_id, text, year in memories:
    # Recategorize with age context
    new_category = categorize_memory(text, year=year, birth_year=1955)
    
    # Update
    conn.execute('UPDATE memories SET category = ? WHERE id = ?', (new_category, mem_id))
    print(f"Memory {mem_id} ({year}): {new_category}")

conn.commit()
conn.close()
print("\n✓ All memories recategorized!")