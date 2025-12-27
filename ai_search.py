# ai_search.py - DeepSeek-powered intelligent search
import os
from openai import OpenAI
from typing import List, Dict, Any
import json
from database import get_db
from datetime import datetime
import re

class DeepSeekSearch:
    def __init__(self, api_key=None):
        """
        Initialize DeepSeek search engine.
        Get your API key from: https://platform.deepseek.com/api_keys
        """
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        if not self.api_key:
            print("⚠️  Warning: No DeepSeek API key found. Search will use basic matching.")
            print("   Get a free API key from: https://platform.deepseek.com/api_keys")
            print("   Then add to ~/.zshrc: export DEEPSEEK_API_KEY='your-key-here'")
        
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
                print("✓ DeepSeek AI search initialized")
            except Exception as e:
                print(f"✗ Failed to initialize DeepSeek: {e}")
                self.client = None
        
        # Cache for common questions
        self.cache = {}
    
    def understand_query(self, query: str) -> Dict[str, Any]:
        """
        Use DeepSeek to understand what the user is asking.
        """
        if not self.client:
            return self._basic_understanding(query)
        
        try:
            # Ask DeepSeek to analyze the question
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """You are a family memory search assistant. 
                    Analyze questions about family memories and extract key information.
                    
                    Return ONLY valid JSON with this structure:
                    {
                        "intent": "find_person_info" | "find_event" | "find_location" | "find_date" | "general_search",
                        "person_names": ["list", "of", "names"],
                        "locations": ["list", "of", "locations"],
                        "dates": ["list", "of", "dates"],
                        "keywords": ["important", "keywords"],
                        "question_type": "who" | "what" | "when" | "where" | "why" | "how" | "general",
                        "main_subject": "what the question is mainly about"
                    }
                    """},
                    {"role": "user", "content": f"Analyze this question about family memories: {query}"}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"DeepSeek query understanding error: {e}")
            return self._basic_understanding(query)
    
    def _basic_understanding(self, query: str) -> Dict[str, Any]:
        """
        Fallback basic query understanding without AI.
        """
        query_lower = query.lower()
        
        result = {
            "intent": "general_search",
            "person_names": [],
            "locations": [],
            "dates": [],
            "keywords": [],
            "question_type": "general",
            "main_subject": query
        }
        
        # Extract question type
        question_words = {
            "who": "who",
            "what": "what", 
            "when": "when",
            "where": "where",
            "why": "why",
            "how": "how"
        }
        
        for word, q_type in question_words.items():
            if word in query_lower:
                result["question_type"] = q_type
                break
        
        # Extract person names (capitalized words that could be names)
        words = query.split()
        for i, word in enumerate(words):
            if len(word) > 1 and word[0].isupper():
                # Check if it's likely a name (not start of sentence)
                if i > 0 or word in ["I", "A", "The"]:
                    result["person_names"].append(word)
        
        # Extract locations for "where" questions
        if result["question_type"] == "where":
            location_indicators = ["born", "live", "located", "from", "place", "city", "town", "country"]
            for indicator in location_indicators:
                if indicator in query_lower:
                    result["intent"] = "find_location"
                    result["keywords"].append(indicator)
                    break
        
        # Extract dates
        date_patterns = [
            r'\b\d{4}\b',  # Years
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            result["dates"].extend(matches)
        
        return result
    
    def search_with_context(self, query: str) -> Dict[str, Any]:
        """
        Perform intelligent search using DeepSeek with full context.
        Returns both direct answer and relevant memories.
        """
        # First, get memories from database
        memories = self._get_all_memories()
        if not memories:
            return {
                "answer": "No family memories found yet.",
                "confidence": 0.0,
                "memories": [],
                "direct_answer": False
            }
        
        # If AI is available, use it
        if self.client:
            try:
                # Prepare context for DeepSeek
                memory_context = self._prepare_memory_context(memories)
                
                # Ask DeepSeek to answer the question based on memories
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": """You are a family memory expert. 
                        Answer questions based ONLY on the provided family memories.
                        If the information isn't in the memories, say so clearly.
                        
                        IMPORTANT: Be specific and direct. If asked "Where was [person] born?"
                        and you find "He was born in London" in the memories, answer "London".
                        
                        Format your response as JSON:
                        {
                            "answer": "direct answer to the question",
                            "supporting_memory_ids": [list of memory IDs that support the answer],
                            "confidence": 0.0 to 1.0,
                            "direct_answer": true/false
                        }
                        """},
                        {"role": "user", "content": f"""Family Memories:
                        {memory_context}
                        
                        Question: {query}
                        
                        Answer based ONLY on the memories above. Be specific and direct."""}
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # Get full memory details for the supporting memories
                memory_details = []
                for mem_id in result.get("supporting_memory_ids", [])[:3]:  # Limit to 3
                    memory = next((m for m in memories if m["id"] == mem_id), None)
                    if memory:
                        memory_details.append(memory)
                
                return {
                    "answer": result.get("answer", "I couldn't find that information in the family memories."),
                    "confidence": result.get("confidence", 0.0),
                    "memories": memory_details,
                    "direct_answer": result.get("direct_answer", False),
                    "ai_generated": True
                }
                
            except Exception as e:
                print(f"DeepSeek search error: {e}")
                # Fall back to enhanced search
                return self._enhanced_search(query, memories)
        else:
            # Use enhanced search without AI
            return self._enhanced_search(query, memories)
    
    def _prepare_memory_context(self, memories: List[Dict]) -> str:
        """
        Prepare memory context for DeepSeek.
        """
        context_lines = []
        for memory in memories:
            context = f"[Memory ID: {memory['id']}] {memory['text']}"
            if memory.get('date'):
                context += f" (Date: {memory['date']})"
            if memory.get('people') and memory['people']:
                context += f" [People: {', '.join(memory['people'])}]"
            context_lines.append(context)
        
        return "\n\n".join(context_lines[:30])  # Limit to 30 memories to avoid token limit
    
    def _enhanced_search(self, query: str, memories: List[Dict]) -> Dict[str, Any]:
        """
        Enhanced search without AI - better than basic keyword matching.
        """
        query_analysis = self.understand_query(query)
        query_lower = query.lower()
        
        # Score each memory for relevance
        scored_memories = []
        for memory in memories:
            score = 0
            memory_text = memory['text'].lower()
            
            # Person name matches (highest priority)
            for name in query_analysis["person_names"]:
                name_lower = name.lower()
                if name_lower in memory_text:
                    score += 40
                    # Bonus for exact name match
                    if re.search(r'\b' + re.escape(name_lower) + r'\b', memory_text):
                        score += 20
            
            # Location intent special handling
            if query_analysis["intent"] == "find_location" and "born" in query_lower:
                # Look for birth-related phrases
                birth_phrases = [
                    "born in",
                    "born at", 
                    "birthplace",
                    "delivered in",
                    "native of",
                    "originated from"
                ]
                
                for phrase in birth_phrases:
                    if phrase in memory_text:
                        score += 50
                        # Try to extract location
                        start = memory_text.find(phrase) + len(phrase)
                        end = min(start + 50, len(memory_text))
                        location_hint = memory['text'][start:end].strip()
                        memory['location_hint'] = f"Possible location: {location_hint}"
                        break
            
            # Keyword matches
            keywords = [w for w in query_lower.split() if len(w) > 3]
            for keyword in keywords:
                if keyword in memory_text:
                    score += 10
            
            # Question-type specific bonuses
            if query_analysis["question_type"] == "where":
                location_words = ["in", "at", "from", "to", "near", "by"]
                for word in location_words:
                    if word in memory_text:
                        score += 5
            
            memory['relevance_score'] = score
            if score > 20:  # Only include if somewhat relevant
                scored_memories.append(memory)
        
        # Sort by relevance
        scored_memories.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Generate answer if we have high-scoring memories
        answer = None
        if scored_memories and scored_memories[0]['relevance_score'] > 50:
            best_memory = scored_memories[0]
            if query_analysis["question_type"] == "where" and "born" in query_lower:
                # Try to extract birth location
                for phrase in ["born in", "born at", "birthplace"]:
                    if phrase in best_memory['text'].lower():
                        start = best_memory['text'].lower().find(phrase) + len(phrase)
                        end = best_memory['text'].find('.', start)
                        if end == -1:
                            end = min(start + 50, len(best_memory['text']))
                        location = best_memory['text'][start:end].strip()
                        answer = f"According to family memories: {location}"
                        break
        
        return {
            "answer": answer or f"I found {len(scored_memories)} relevant memories, but couldn't extract a direct answer. Try looking at the memories below.",
            "confidence": min(0.7, len(scored_memories) / 10),
            "memories": scored_memories[:5],  # Top 5
            "direct_answer": answer is not None,
            "ai_generated": False
        }
    
    def _get_all_memories(self) -> List[Dict]:
        """Get all memories from database."""
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Get memories with people information
            cursor.execute("""
                SELECT m.id, m.text, m.category, m.memory_date, m.year
                FROM memories m
                ORDER BY m.year DESC
            """)
            
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    "id": row[0],
                    "text": row[1],
                    "category": row[2],
                    "date": row[3],
                    "year": row[4],
                    "people": []  # Will be populated if we have the people table
                })
            
            return memories
            
        except Exception as e:
            print(f"Error getting memories: {e}")
            return []

# Global instance
ai_searcher = DeepSeekSearch()