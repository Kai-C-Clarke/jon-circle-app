# How to Update app.py for Better Categorization

## Step 1: Replace utils.py

```bash
cd "/Users/jonstiles/Desktop/Jon's memories in the circle app"
cp utils.py utils_backup.py
cp ~/Downloads/utils_improved.py utils.py
```

## Step 2: Update app.py Line 186

**Find this line (around line 186):**
```python
category = categorize_memory(text)
```

**Replace with:**
```python
category = categorize_memory(text, year=year)
```

This passes the year so the AI knows your age when categorizing.

## Step 3: Fix Existing Wrong Categories

Run this SQL to fix the obvious mistakes:

```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('circle_memories.db')

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
]

for mem_id, correct_cat, desc in fixes:
    conn.execute('UPDATE memories SET category = ? WHERE id = ?', (correct_cat, mem_id))
    print(f"✓ {mem_id}: {desc} → {correct_cat}")

conn.commit()
conn.close()
print("\n✓ All categories fixed!")
EOF
```

## Step 4: Recategorize Everything (Optional)

If you want to recategorize ALL memories with the improved system:

```bash
python3 << 'EOF'
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
EOF
```

## What Changed

### Old utils.py
- Simple keyword matching only
- No age awareness
- Categories: childhood, education, work, family, travel, hobbies, other

### New utils.py  
- Uses DeepSeek AI for intelligent categorization
- Considers your age when the memory happened
- Falls back to improved keyword matching if AI unavailable
- Better keywords (e.g., "band", "bass" → music; "petrol", "serving" → work)
- More categories: childhood, teenage, education, work, music, family, travel, military, hobbies, life-event, other

### Why Your Categories Were Wrong

1. **Memory 4 (1986 work)** → "education"
   - Has "Eastbourne" which might have matched education keywords
   - New system sees "worked" and knows you were 31 (adult)

2. **Memory 14 (1985 petrol)** → "childhood"  
   - Old system had "serving" but no context
   - New system sees "serving petrol" + age 30 → work

3. **Memory 6, 8 (bands)** → "early-life"/"work"
   - Old system didn't have "music" category
   - New system detects "band", "bass" → music

## Test It

After updating:
```bash
# Restart Flask
python3 app.py

# Create a test memory
# Go to http://localhost:5000 and add:
# "In 2010 I played guitar in a blues band at the local pub"
# Should categorize as "music" not "hobbies" or "other"
```
