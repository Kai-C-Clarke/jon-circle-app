# search_engine.py - Intelligent search with relevance scoring
import re
import sqlite3
from database import get_db

class EnhancedSearch:
    def __init__(self):
        self.common_words = {
            'who', 'what', 'when', 'where', 'why', 'how',
            'was', 'is', 'are', 'were', 'did', 'do', 'does',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on',
            'at', 'to', 'for', 'of', 'with', 'by', 'about'
        }
    
    def extract_names(self, query):
        """Extract person names from natural language queries."""
        names = []
        query_lower = query.lower().strip()
        
        # Patterns like "Who was Peter Elgar?"
        patterns = [
            r'who was ([\w\s]+?)\??$',
            r'who is ([\w\s]+?)\??$',
            r'about ([\w\s]+?)\??$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                name = match.group(1).strip()
                if name and len(name.split()) <= 4:
                    names.append(name)
        
        return names
    
    def calculate_relevance(self, text, query, names):
        """Calculate relevance score (0-100)."""
        score = 0
        text_lower = text.lower()
        query_lower = query.lower()
        
        # 1. Exact phrase match
        if query_lower in text_lower:
            score += 50
        
        # 2. Person name matches
        for name in names:
            if name.lower() in text_lower:
                score += 40
        
        # 3. Word matches
        query_words = [w for w in query_lower.split() if w not in self.common_words]
        matches = sum(1 for word in query_words if word in text_lower)
        
        if matches > 0:
            score += (matches / len(query_words)) * 30
        
        return min(score, 100)
    
    def search_memories(self, query, threshold=10.0):
        """Search memories with relevance scoring."""
        names = self.extract_names(query)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get all memories
        cursor.execute("""
            SELECT m.id, m.text, m.category, m.memory_date, m.year,
                   GROUP_CONCAT(DISTINCT mp.person_name) as people
            FROM memories m
            LEFT JOIN memory_people mp ON m.id = mp.memory_id
            GROUP BY m.id
        """)
        
        results = []
        for memory in cursor.fetchall():
            search_text = f"{memory['text']}"
            if memory['people']:
                search_text += f" {memory['people']}"
            
            relevance = self.calculate_relevance(search_text, query, names)
            
            if relevance >= threshold:
                results.append({
                    'id': memory['id'],
                    'text': memory['text'],
                    'category': memory['category'],
                    'date': memory['memory_date'],
                    'year': memory['year'],
                    'relevance_score': round(relevance, 2),
                    'people': memory['people'].split(',') if memory['people'] else []
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:10]  # Return top 10