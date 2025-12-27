#!/usr/bin/env python3
"""Quick fix for wrong memory categories"""

import sqlite3
import sys

db_path = 'circle_memories.db'
if len(sys.argv) > 1:
    db_path = sys.argv[1]

conn = sqlite3.connect(db_path)

fixes = [
    (4, 'work', '1986 - Eastbourne work'),
    (14, 'work', '1985 - Petrol station'),
    (8, 'music', '2000 - Bass band'),
    (6, 'music', '2009 - Big Dave band'),
    (7, 'music', '1974 - Punk rock'),
    (10, 'childhood', '1964 - Summer age 9'),
    (13, 'family', '1959 - Sister born'),
    (1, 'life-event', '1955 - Birth'),
    (5, 'family', '1931 - Mum born'),
    (11, 'education', '1968 - Canteen at Claverham'),
    (12, 'education', '1968 - First year A stream'),
    (2, 'education', '1967 - Started Claverham'),
    (15, 'education', '1965 - Battle and Langton Primary'),
    (9, 'childhood', '1963 - Summer age 8'),
    (3, 'teenage', '1975 - Hastings Pier age 20'),
]

print("Fixing memory categories...")
print("-" * 60)

for mem_id, correct_cat, desc in fixes:
    # Get current category
    cursor = conn.execute('SELECT category FROM memories WHERE id = ?', (mem_id,))
    result = cursor.fetchone()
    
    if result:
        old_cat = result[0]
        if old_cat != correct_cat:
            conn.execute('UPDATE memories SET category = ? WHERE id = ?', (correct_cat, mem_id))
            print(f"✓ {mem_id}: {desc}")
            print(f"  {old_cat} → {correct_cat}")
        else:
            print(f"○ {mem_id}: {desc} (already {correct_cat})")

conn.commit()
conn.close()
print("-" * 60)
print("✓ All categories fixed!")
