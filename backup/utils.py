# utils.py - Utility functions
import re
from datetime import datetime

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

def categorize_memory(text):
    """Categorize memory based on keywords."""
    text_lower = text.lower()
    
    categories = [
        ("childhood", ['born', 'birth', 'childhood', 'kid', 'baby']),
        ("education", ['school', 'college', 'university', 'teacher', 'student']),
        ("work", ['job', 'work', 'career', 'office', 'boss', 'colleague']),
        ("family", ['family', 'mother', 'father', 'parent', 'sibling', 'daughter', 'son']),
        ("travel", ['travel', 'trip', 'vacation', 'holiday', 'journey']),
        ("hobbies", ['hobby', 'sport', 'music', 'art', 'game', 'dance'])
    ]
    
    for category, keywords in categories:
        if any(keyword in text_lower for keyword in keywords):
            return category
    
    return "other"

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