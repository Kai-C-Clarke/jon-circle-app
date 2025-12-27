#!/usr/bin/env python3
"""
Text-Based Photo Matching for Memories
Matches photos using metadata (year, titles, names, keywords) without requiring vision AI
"""

import os
import re
import sqlite3
from collections import Counter

def extract_names(text):
    """Extract potential names from text (capitalized words)."""
    # Find capitalized words that might be names
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    # Filter out common non-names
    stopwords = {'The', 'And', 'Or', 'But', 'In', 'On', 'At', 'To', 'For', 'From', 
                 'With', 'This', 'That', 'These', 'Those', 'It', 'He', 'She', 'They',
                 'Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Battle', 'Hastings', 'London',
                 'England', 'UK', 'USA', 'World', 'War', 'Year', 'Day', 'Month'}
    
    names = [w for w in words if w not in stopwords and len(w) > 2]
    
    # Return unique names
    return list(set(names))

def extract_keywords(text):
    """Extract important keywords from text."""
    # Remove common words
    stopwords = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                 'a', 'an', 'is', 'was', 'were', 'are', 'been', 'be', 'have', 'has', 'had',
                 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her',
                 'its', 'our', 'their', 'this', 'that', 'these', 'those'}
    
    # Get words, lowercase, filter stopwords
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    
    # Return most common keywords
    counter = Counter(keywords)
    return [word for word, count in counter.most_common(20)]

def score_photo_match(memory_text, memory_year, photo_metadata):
    """
    Score how well a photo matches a memory using text-only analysis.
    
    Returns: {
        'score': int (0-100),
        'reasons': [str] - list of match reasons
    }
    """
    score = 0
    reasons = []
    
    photo_title = (photo_metadata.get('title') or '').lower()
    photo_desc = (photo_metadata.get('description') or '').lower()
    photo_year = photo_metadata.get('year')
    
    # Combine photo text
    photo_text = f"{photo_title} {photo_desc}".strip()
    memory_lower = memory_text.lower()
    
    # 1. YEAR MATCHING (up to 30 points)
    if memory_year and photo_year:
        try:
            mem_y = int(memory_year)
            ph_y = int(photo_year)
            year_diff = abs(mem_y - ph_y)
            
            if year_diff == 0:
                score += 30
                reasons.append(f"Exact year match: {mem_y}")
            elif year_diff <= 1:
                score += 25
                reasons.append(f"Year within 1: {mem_y} vs {ph_y}")
            elif year_diff <= 2:
                score += 20
                reasons.append(f"Year within 2: {mem_y} vs {ph_y}")
            elif year_diff <= 5:
                score += 10
                reasons.append(f"Year within 5: {mem_y} vs {ph_y}")
        except:
            pass
    
    # 2. EXACT PHRASE MATCHING (up to 40 points) - CHECK THIS FIRST
    # If photo title/desc appears word-for-word in memory, that's a strong signal
    if photo_title and len(photo_title) > 10:
        # Check if entire title appears in memory
        if photo_title in memory_lower:
            score += 40
            reasons.append(f"Exact title match: '{photo_title}'")
        else:
            # Check for significant phrase overlap (at least 3 consecutive words)
            photo_words = photo_title.split()
            for i in range(len(photo_words) - 2):
                phrase = ' '.join(photo_words[i:i+3])
                if len(phrase) > 10 and phrase in memory_lower:
                    score += 30
                    reasons.append(f"Strong phrase match: '{phrase}'")
                    break
    
    # 3. NAME MATCHING (up to 30 points)
    memory_names = extract_names(memory_text)
    
    # Check for full name matches in photo text
    matched_names = []
    for name in memory_names:
        if name.lower() in photo_text:
            matched_names.append(name)
    
    if matched_names:
        # Score based on number and completeness of matched names
        if len(matched_names) >= 3:
            # Multiple names matched (like "Jon Mark Smith") = strong signal
            name_score = 30
            reasons.append(f"Multiple name matches: {', '.join(matched_names)}")
        elif len(matched_names) == 2:
            name_score = 25
            reasons.append(f"Two names matched: {', '.join(matched_names)}")
        else:
            name_score = 20
            reasons.append(f"Name matched: {matched_names[0]}")
        
        score += name_score
    
    # 4. KEYWORD MATCHING (up to 20 points)
    memory_keywords = extract_keywords(memory_text)
    
    matched_keywords = []
    for keyword in memory_keywords[:10]:  # Check top 10 keywords
        if keyword in photo_text:
            matched_keywords.append(keyword)
    
    if matched_keywords:
        # More keywords = higher confidence
        keyword_score = min(20, len(matched_keywords) * 4)
        score += keyword_score
        reasons.append(f"Matched keywords: {', '.join(matched_keywords[:3])}")
    
    # 5. BONUS: Combined name + keyword + year = very high confidence
    if matched_names and matched_keywords and memory_year and photo_year:
        try:
            year_diff = abs(int(memory_year) - int(photo_year))
            if year_diff <= 2:
                score += 10
                reasons.append("Strong combined match (names+keywords+year)")
        except:
            pass
    
    return {
        'score': min(100, score),  # Cap at 100
        'reasons': reasons
    }


def suggest_photos_for_memory(memory_id, db_path='circle_memories.db', confidence_threshold=40):
    """
    Suggest photos for a specific memory using text-based matching.
    
    Returns list of suggestions sorted by score.
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
    
    # Get all photos NOT already linked to this memory
    cursor.execute('''
        SELECT m.id, m.filename, m.original_filename, m.title, m.description, m.year
        FROM media m
        WHERE m.file_type = 'image'
        AND m.id NOT IN (
            SELECT media_id FROM memory_media WHERE memory_id = ?
        )
    ''', (memory_id,))
    
    photos = cursor.fetchall()
    suggestions = []
    
    for photo in photos:
        photo_id, filename, original, title, desc, year = photo
        
        print(f"Analyzing: {title or original} ({year})...", end=' ')
        
        # Score the match
        metadata = {
            'title': title or '',
            'description': desc or '',
            'year': year
        }
        
        result = score_photo_match(mem_text, mem_year, metadata)
        
        if result['score'] >= confidence_threshold:
            suggestions.append({
                'id': photo_id,
                'filename': filename,
                'original_filename': original,
                'title': title or original,
                'description': desc,
                'score': result['score'],
                'match_reason': ' | '.join(result['reasons']) if result['reasons'] else 'Potential match'
            })
            print(f"✓ {result['score']}% match")
        else:
            print(f"✗ {result['score']}% (below threshold)")
    
    conn.close()
    
    # Sort by score
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return suggestions

def suggest_all_memories(db_path='circle_memories.db', confidence_threshold=40):
    """
    Process all memories and suggest photo matches.
    Returns dict of {memory_id: [suggestions]}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM memories')
    memories = cursor.fetchall()
    conn.close()
    
    all_suggestions = {}
    
    for (mem_id,) in memories:
        print(f"\n\nProcessing Memory {mem_id}...")
        suggestions = suggest_photos_for_memory(mem_id, db_path, confidence_threshold)
        
        if suggestions:
            all_suggestions[mem_id] = suggestions
            print(f"\n✓ Found {len(suggestions)} suggestions for Memory {mem_id}")
        else:
            print(f"\n○ No suggestions for Memory {mem_id}")
    
    return all_suggestions

def apply_suggestion(memory_id, photo_id, db_path='circle_memories.db'):
    """Accept a suggestion and link the photo to memory."""
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

def get_linked_photos(memory_id, db_path='circle_memories.db'):
    """Get photos already linked to a memory."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT m.id, m.filename, m.title, mm.display_order
        FROM media m
        JOIN memory_media mm ON m.id = mm.media_id
        WHERE mm.memory_id = ?
        ORDER BY mm.display_order
    ''', (memory_id,))
    
    photos = cursor.fetchall()
    conn.close()
    return photos

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Text-based photo matching for memories')
    parser.add_argument('--memory', type=int, help='Suggest photos for specific memory ID')
    parser.add_argument('--threshold', type=int, default=40, help='Score threshold (0-100)')
    parser.add_argument('--database', default='circle_memories.db', help='Database path')
    parser.add_argument('--apply', nargs=2, type=int, metavar=('MEMORY_ID', 'PHOTO_ID'),
                       help='Link photo to memory')
    parser.add_argument('--show-linked', type=int, metavar='MEMORY_ID',
                       help='Show photos already linked to memory')
    
    args = parser.parse_args()
    
    if args.apply:
        memory_id, photo_id = args.apply
        apply_suggestion(memory_id, photo_id, args.database)
    
    elif args.show_linked:
        photos = get_linked_photos(args.show_linked, args.database)
        if photos:
            print(f"\nPhotos linked to Memory {args.show_linked}:")
            for photo_id, filename, title, order in photos:
                print(f"  {order}. {title or filename} (ID: {photo_id})")
        else:
            print(f"\nNo photos linked to Memory {args.show_linked}")
    
    elif args.memory:
        # Single memory
        suggestions = suggest_photos_for_memory(
            args.memory, 
            args.database, 
            args.threshold
        )
        
        if suggestions:
            print(f"\n{'='*80}")
            print(f"PHOTO SUGGESTIONS FOR MEMORY {args.memory}")
            print(f"{'='*80}")
            
            for i, sug in enumerate(suggestions, 1):
                print(f"\n{i}. {sug['title']}")
                print(f"   Score: {sug['score']}%")
                print(f"   Match: {sug['match_reason']}")
            
            print(f"\n\nApply suggestions:")
            print(f"  python3 ai_photo_matcher.py --apply {args.memory} <photo_id>")
        else:
            print(f"\n○ No suggestions above {args.threshold}% score")
    
    else:
        parser.print_help()
