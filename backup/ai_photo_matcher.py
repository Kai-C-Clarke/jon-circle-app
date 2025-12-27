#!/usr/bin/env python3
"""
AI-Powered Photo Matching for Memories
Uses DeepSeek's vision model to intelligently match photos to memories
"""

import os
import base64
import sqlite3
from openai import OpenAI

def get_ai_client():
    """Get DeepSeek client."""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def encode_image(image_path):
    """Encode image to base64."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def match_photo_to_memory(memory_text, memory_year, photo_path, photo_metadata):
    """
    Use AI vision to determine if a photo matches a memory.
    
    Returns: {
        'matches': bool,
        'confidence': float (0-100),
        'reasoning': str
    }
    """
    try:
        client = get_ai_client()
        
        # Encode image
        base64_image = encode_image(photo_path)
        
        # Extract metadata
        photo_title = photo_metadata.get('title', '')
        photo_desc = photo_metadata.get('description', '')
        photo_year = photo_metadata.get('year', '')
        
        # Build prompt
        prompt = f"""Analyze if this photo matches the memory described below.

MEMORY TEXT:
{memory_text[:500]}

MEMORY YEAR: {memory_year if memory_year else 'Unknown'}

PHOTO METADATA:
Title: {photo_title}
Description: {photo_desc}
Year: {photo_year if photo_year else 'Unknown'}

TASK:
1. Look at the photo carefully
2. Read the memory text
3. Consider the metadata
4. Determine if this photo relates to this memory

Respond in this exact format:
MATCH: YES or NO
CONFIDENCE: 0-100
REASONING: Brief explanation

Consider:
- Do people/places in photo match memory?
- Do years align (within 2-3 years)?
- Does photo title/description mention same events/people?
- Visual elements that support or contradict the connection
"""

        # Call AI with vision
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }],
            max_tokens=200,
            temperature=0.3
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        
        # Extract fields
        matches = "YES" in result_text.upper().split("MATCH:")[1].split("\n")[0]
        
        try:
            confidence_line = [line for line in result_text.split('\n') if 'CONFIDENCE:' in line][0]
            confidence = float(confidence_line.split(':')[1].strip().replace('%', ''))
        except:
            confidence = 50.0
        
        try:
            reasoning = result_text.split("REASONING:")[1].strip()
        except:
            reasoning = "Could not parse reasoning"
        
        return {
            'matches': matches,
            'confidence': confidence,
            'reasoning': reasoning,
            'raw_response': result_text
        }
    
    except Exception as e:
        print(f"Error in AI matching: {e}")
        return {
            'matches': False,
            'confidence': 0,
            'reasoning': f"Error: {str(e)}",
            'raw_response': ''
        }

def suggest_photos_for_memory(memory_id, db_path='circle_memories.db', confidence_threshold=60):
    """
    Suggest photos for a specific memory using AI.
    
    Returns list of suggestions sorted by confidence.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get memory
    cursor.execute('SELECT id, text, year FROM memories WHERE id = ?', (memory_id,))
    memory = cursor.fetchone()
    
    if not memory:
        print(f"Memory {memory_id} not found")
        return []
    
    mem_id, mem_text, mem_year = memory
    
    print(f"\n{'='*80}")
    print(f"Finding photos for Memory {mem_id}")
    print(f"Year: {mem_year}")
    print(f"Text: {mem_text[:100]}...")
    print(f"{'='*80}\n")
    
    # Get all photos
    cursor.execute('''
        SELECT id, filename, original_filename, title, description, year
        FROM media
        WHERE file_type = 'image'
    ''')
    
    photos = cursor.fetchall()
    suggestions = []
    
    for photo in photos:
        photo_id, filename, original, title, desc, year = photo
        
        # Build full path
        photo_path = os.path.join('uploads', filename)
        
        if not os.path.exists(photo_path):
            print(f"⚠ Photo not found: {photo_path}")
            continue
        
        print(f"Analyzing: {title or original} ({year})...", end=' ')
        
        # Get AI match
        metadata = {
            'title': title or '',
            'description': desc or '',
            'year': year
        }
        
        result = match_photo_to_memory(mem_text, mem_year, photo_path, metadata)
        
        if result['matches'] and result['confidence'] >= confidence_threshold:
            suggestions.append({
                'photo_id': photo_id,
                'filename': filename,
                'title': title or original,
                'confidence': result['confidence'],
                'reasoning': result['reasoning']
            })
            print(f"✓ {result['confidence']}% match")
        else:
            print(f"✗ {result['confidence']}% (below threshold)")
    
    conn.close()
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x['confidence'], reverse=True)
    
    return suggestions

def suggest_all_memories(db_path='circle_memories.db', confidence_threshold=70):
    """
    Process all memories and suggest photo matches.
    Returns dict of {memory_id: [suggestions]}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, text FROM memories')
    memories = cursor.fetchall()
    
    all_suggestions = {}
    
    for mem_id, mem_text in memories:
        print(f"\n\nProcessing Memory {mem_id}...")
        suggestions = suggest_photos_for_memory(mem_id, db_path, confidence_threshold)
        
        if suggestions:
            all_suggestions[mem_id] = suggestions
            print(f"\n✓ Found {len(suggestions)} suggestions for Memory {mem_id}")
        else:
            print(f"\n○ No suggestions for Memory {mem_id}")
    
    conn.close()
    return all_suggestions

def apply_suggestion(memory_id, photo_id, db_path='circle_memories.db'):
    """Accept an AI suggestion and link the photo."""
    conn = sqlite3.connect(db_path)
    
    # Get current max order
    cursor = conn.execute(
        'SELECT COALESCE(MAX(display_order), -1) FROM memory_media WHERE memory_id = ?',
        (memory_id,)
    )
    max_order = cursor.fetchone()[0]
    
    # Insert link
    conn.execute(
        'INSERT OR IGNORE INTO memory_media (memory_id, media_id, display_order) VALUES (?, ?, ?)',
        (memory_id, photo_id, max_order + 1)
    )
    
    conn.commit()
    conn.close()
    print(f"✓ Linked photo {photo_id} to memory {memory_id}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-powered photo matching for memories')
    parser.add_argument('--memory', type=int, help='Suggest photos for specific memory ID')
    parser.add_argument('--all', action='store_true', help='Process all memories')
    parser.add_argument('--threshold', type=int, default=70, help='Confidence threshold (0-100)')
    parser.add_argument('--database', default='circle_memories.db', help='Database path')
    
    args = parser.parse_args()
    
    if not os.getenv('DEEPSEEK_API_KEY'):
        print("❌ DEEPSEEK_API_KEY not set")
        print("Set it with: export DEEPSEEK_API_KEY='your-key'")
        exit(1)
    
    if args.memory:
        # Single memory
        suggestions = suggest_photos_for_memory(
            args.memory, 
            args.database, 
            args.threshold
        )
        
        if suggestions:
            print(f"\n{'='*80}")
            print(f"AI SUGGESTIONS FOR MEMORY {args.memory}")
            print(f"{'='*80}")
            
            for i, sug in enumerate(suggestions, 1):
                print(f"\n{i}. {sug['title']}")
                print(f"   Confidence: {sug['confidence']}%")
                print(f"   Reasoning: {sug['reasoning']}")
            
            print("\nApply suggestions:")
            print(f"  python3 ai_photo_matcher.py --apply {args.memory} <photo_id>")
        else:
            print(f"\n○ No suggestions above {args.threshold}% confidence")
    
    elif args.all:
        # All memories
        all_sug = suggest_all_memories(args.database, args.threshold)
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Processed {len(all_sug)} memories with suggestions")
        
        total_suggestions = sum(len(sug) for sug in all_sug.values())
        print(f"Total suggestions: {total_suggestions}")
    
    else:
        parser.print_help()
