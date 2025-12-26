# utils.py - Utility functions
import re
from datetime import datetime
import os

def parse_date_input(date_input):
    """Parse various date formats."""
    date_input = date_input.strip()
    if not date_input:
        return None, None
    
    # Try year only
    year_match = re.match(r'^\s*(\d{4})\s*$', date_input)
    if year_match:
        return None, int(year_match.group(1))
    
    # Try month year
    month_year = re.match(r'^\s*([A-Za-z]+)\s+(\d{4})\s*$', date_input, re.IGNORECASE)
    if month_year:
        return f"{month_year.group(1)} {month_year.group(2)}", int(month_year.group(2))
    
    return None, None

def categorize_memory(text, year=None, birth_year=1955):
    """
    Categorize memory using DeepSeek AI with age context.
    Falls back to keyword matching if AI unavailable.
    """
    # Try AI categorization first
    try:
        from openai import OpenAI
        
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            # Calculate age if year provided
            age_context = ""
            if year and birth_year:
                age = year - birth_year
                age_context = f"The person was {age} years old in {year}. "
            
            prompt = f"""{age_context}Categorize this memory into ONE category. Choose the MOST appropriate:

Categories:
- childhood (ages 0-12)
- teenage (ages 13-19) 
- education (school, college, university - any age)
- work (employment, jobs, career)
- music (bands, playing instruments, performances)
- family (family members, relationships)
- travel (trips, holidays, vacations)
- military (service, armed forces)
- hobbies (sports, games, pastimes)
- life-event (major milestones like birth, marriage)
- other (if none fit)

Memory: "{text[:500]}"

Respond with ONLY the category name, nothing else."""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.3
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            # Validate it's a real category
            valid_categories = [
                'childhood', 'teenage', 'education', 'work', 'music', 
                'family', 'travel', 'military', 'hobbies', 'life-event', 'other'
            ]
            
            if category in valid_categories:
                return category
    
    except Exception as e:
        print(f"AI categorization failed: {e}")
        pass
    
    # Fallback: Improved keyword matching with age context
    text_lower = text.lower()
    
    # Calculate age for context if year provided
    age = None
    if year and birth_year:
        age = year - birth_year
    
    # Age-based categories (if we have age context)
    if age is not None:
        if age <= 12 and any(word in text_lower for word in ['born', 'baby', 'child', 'kid', 'primary']):
            return 'childhood'
        elif 13 <= age <= 19 and any(word in text_lower for word in ['teen', 'secondary', 'high school']):
            return 'teenage'
    
    # Keyword-based categorization (improved)
    categories = [
        ("music", ['band', 'bass', 'guitar', 'drums', 'singer', 'gig', 'concert', 'musician', 'rehearsal']),
        ("work", ['worked', 'job', 'career', 'office', 'boss', 'colleague', 'employed', 'serving', 'manager', 'company', 'garage', 'petrol']),
        ("education", ['school', 'college', 'university', 'teacher', 'student', 'class', 'exam', 'degree', 'studying']),
        ("military", ['army', 'navy', 'air force', 'military', 'service', 'soldier', 'regiment', 'deployed']),
        ("family", ['mother', 'father', 'parent', 'sibling', 'daughter', 'son', 'wife', 'husband', 'born', 'sister', 'brother']),
        ("travel", ['travel', 'trip', 'vacation', 'holiday', 'journey', 'visited', 'abroad']),
        ("hobbies", ['hobby', 'sport', 'game', 'fishing', 'cycling', 'running']),
        ("life-event", ['born', 'birth', 'married', 'wedding', 'died', 'funeral', 'graduated'])
    ]
    
    # Count matches for each category
    best_category = "other"
    best_score = 0
    
    for category, keywords in categories:
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > best_score:
            best_score = score
            best_category = category
    
    # If no strong matches and we have age, use age-based default
    if best_score == 0 and age is not None:
        if age <= 12:
            return 'childhood'
        elif 13 <= age <= 19:
            return 'teenage'
        elif 20 <= age <= 65:
            return 'adult-life'
        else:
            return 'later-life'
    
    return best_category

def allowed_file(filename, file_type):
    """Check if file extension is allowed."""
    allowed_extensions = {
        'image': ['jpg', 'jpeg', 'png', 'gif'],
        'audio': ['mp3', 'wav', 'ogg'],
        'video': ['mp4', 'mov', 'avi']
    }
    
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions.get(file_type, [])
