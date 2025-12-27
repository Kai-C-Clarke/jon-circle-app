# app.py - Main Flask application
import os
from openai import OpenAI
from anthropic import Anthropic
from flask import Flask, render_template, jsonify, request, send_file, session
from flask_cors import CORS
from datetime import datetime
from ai_photo_matcher import suggest_photos_for_memory, apply_suggestion, suggest_all_memories

# Import our modules
from database import init_db, get_db, migrate_db
from database_improved import init_db as init_improved_db, migrate_db as migrate_improved_db
from search_engine import EnhancedSearch
from ai_search import ai_searcher  # NEW: Import AI search
from utils import allowed_file, parse_date_input, categorize_memory
from pdf_generator import generate_memory_pdf, generate_family_album_pdf
from werkzeug.utils import secure_filename
import uuid
import traceback

# Import authentication modules
from auth import AuthService, require_auth, InvalidCredentialsError, AccountLockedError, TokenExpiredError, InvalidTokenError
from logger_config import security_logger, get_client_ip
from security_config import SecurityConfig
from flask import g

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize database with authentication support
init_improved_db()
migrate_improved_db()

# Add to app.py after init_db()
def scan_existing_uploads():
    """Scan uploads folder and add any missing files to database."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        uploads_dir = app.config['UPLOAD_FOLDER']
        if not os.path.exists(uploads_dir):
            return
        
        # Get existing filenames from database
        cursor.execute("SELECT filename FROM media")
        existing = {row[0] for row in cursor.fetchall()}
        
        added = 0
        for filename in os.listdir(uploads_dir):
            if filename.startswith('.') or filename in existing:
                continue
                
            filepath = os.path.join(uploads_dir, filename)
            if os.path.isfile(filepath):
                # Auto-add to database
                file_size = os.path.getsize(filepath)
                file_ext = os.path.splitext(filename)[1].lower().replace('.', '')
                
                if file_ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    file_type = 'image'
                elif file_ext in {'mp4', 'mov', 'avi'}:
                    file_type = 'video'
                elif file_ext == 'pdf':
                    file_type = 'document'
                else:
                    continue
                
                cursor.execute('''INSERT INTO media 
                                 (filename, original_filename, file_type, file_size, 
                                  title, uploaded_by, created_at) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                              (filename, filename, file_type, file_size, 
                               os.path.splitext(filename)[0], 'auto_import', 
                               datetime.now().isoformat()))
                added += 1
        
        if added > 0:
            db.commit()
            print(f"📁 Auto-added {added} files from uploads folder")
            
    except Exception as e:
        print(f"Error scanning uploads: {e}")

# Call this after init_db()
scan_existing_uploads()

def generate_biography_deepseek(memories):
    """Generate biography using DeepSeek API."""
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # Prepare memories text
        memories_text = "\n\n".join([
            f"Year: {m['year'] or 'Unknown'}\n{m['text']}"
            for m in memories
        ])
        
        prompt = f"""You are a professional biographer. Synthesize these personal memories into a flowing biographical narrative.

MEMORIES TO SYNTHESIZE:
{memories_text}

INSTRUCTIONS:
1. Write in third person past tense (e.g., "Jon was born...")
2. Create a magazine-style narrative with smooth transitions between events
3. Organize chronologically by decade or life phase
4. Preserve ALL factual details - names, dates, places, events
5. Add context where helpful but never invent facts
6. Write in a warm, engaging style suitable for family reading
7. Use chapter breaks for major life phases
8. Total length: 2000-3000 words

FORMAT:
# Chapter 1: [Decade/Phase Name]

[Narrative text...]

# Chapter 2: [Next Phase]

[Narrative text...]

Begin the biography now:"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        raise

def generate_biography_claude(memories):
    """Generate biography using Claude API."""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        
        client = Anthropic(api_key=api_key)
        
        # Prepare memories text
        memories_text = "\n\n".join([
            f"Year: {m['year'] or 'Unknown'}\n{m['text']}"
            for m in memories
        ])
        
        prompt = f"""You are a professional biographer synthesizing personal memories into a compelling narrative.

MEMORIES TO SYNTHESIZE:
{memories_text}

TASK:
Create a flowing biographical narrative suitable for a family memoir or magazine feature.

REQUIREMENTS:
1. Write in third person past tense
2. Organize chronologically, creating natural chapter breaks by life phase or decade
3. Preserve all factual details exactly - names, dates, places, specific events
4. Add contextual transitions and connections between events
5. Never invent facts not present in the source memories
6. Write in a warm, accessible style - not academic or clinical
7. Include vivid details from the original memories (they matter!)
8. Aim for 2000-3000 words total

STRUCTURE:
Use markdown with # for chapter headings. Each chapter should flow naturally.

Begin writing the biography now:"""

        response = client.messages.create(
            model="claude-sonnet-4-5",  # Alias - auto-updates to latest
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        print(f"Claude API error: {e}")
        raise

def parse_biography_into_chapters(narrative_text):
    """Parse narrative text into chapter structure."""
    import re
    
    # Split by markdown headers (# Chapter...)
    chapters = []
    current_chapter = None
    
    for line in narrative_text.split('\n'):
        # Check for chapter header
        if line.startswith('#'):
            if current_chapter:
                chapters.append(current_chapter)
            
            title = re.sub(r'^#+\s*', '', line).strip()
            current_chapter = {
                'title': title,
                'narrative': [],
                'suggested_photos': []
            }
        elif current_chapter and line.strip():
            current_chapter['narrative'].append(line)
    
    # Add final chapter
    if current_chapter:
        chapters.append(current_chapter)
    
    # Join narrative lines
    for chapter in chapters:
        chapter['narrative'] = '\n'.join(chapter['narrative']).strip()
    
    return chapters

# ============================================
# BASIC ROUTES
# ============================================

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/app')
def main_app():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "time": datetime.now().isoformat(),
        "ai_search": ai_searcher.client is not None
    })

@app.route('/goodbye')
def goodbye():
    """Exit/goodbye page with instructions on how to close the browser."""
    return render_template('goodbye.html')

# ============================================
# PROFILE ROUTES
# ============================================

@app.route('/api/profile/save', methods=['POST'])
def save_profile():
    try:
        data = request.json
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("DELETE FROM user_profile")
        cursor.execute('''INSERT INTO user_profile (name, birth_date, family_role, birth_place, created_at) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (data['name'], data['birth_date'], data['family_role'], 
                       data.get('birth_place', ''), datetime.now().isoformat()))
        
        db.commit()
        return jsonify({"status": "success", "message": "Profile saved"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/profile/get', methods=['GET'])
def get_profile():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user_profile LIMIT 1")
        profile = cursor.fetchone()
        
        if profile:
            return jsonify({
                "exists": True,
                "name": profile[1],
                "birth_date": profile[2],
                "family_role": profile[3],
                "birth_place": profile[4]
            })
        return jsonify({"exists": False})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# MEMORY ROUTES
# ============================================

@app.route('/api/memories/save', methods=['POST'])
def save_memory():
    """Save a new memory with optional audio recording."""
    try:
        data = request.json
        text = data.get('text', '').strip()
        memory_date = data.get('memory_date', '').strip()
        audio_filename = data.get('audio_filename', '').strip()
        
        if not text:
            return jsonify({"status": "error", "message": "Memory text is required"}), 400
        
        # Parse date
        parsed_date = None
        year = None
        if memory_date:
            date_result = parse_date_input(memory_date)
            if date_result:
                if isinstance(date_result, tuple):
                    parsed_date, year = date_result
                else:
                    parsed_date = date_result
                    # Try to extract year
                    try:
                        import re
                        year_match = re.search(r'\b(?:19|20)\d{2}\b', parsed_date)
                        if year_match:
                            year = int(year_match.group())
                    except:
                        year = None
        
        # Categorize memory
        category = categorize_memory(text, year=year)
        
        # Save to database
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO memories 
                         (text, category, memory_date, year, audio_filename, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (text, category, parsed_date, year, 
                       audio_filename if audio_filename else None,
                       datetime.now().isoformat()))
        
        db.commit()
        memory_id = cursor.lastrowid
        
        # If audio was recorded, update the transcription record
        if audio_filename:
            cursor.execute('''UPDATE audio_transcriptions 
                             SET transcription_text = ? 
                             WHERE audio_filename = ?''',
                          (text, audio_filename))
            db.commit()
        
        return jsonify({
            "status": "success",
            "memory_id": memory_id,
            "category": category,
            "has_audio": bool(audio_filename)
        })
        
    except Exception as e:
        print(f"Error saving memory: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to save memory"}), 500

@app.route('/api/memories/delete/<int:memory_id>', methods=['DELETE'])
def delete_memory(memory_id):
    """Delete a memory and its associated audio file."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get memory details before deleting
        cursor.execute('SELECT audio_filename FROM memories WHERE id = ?', (memory_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({"status": "error", "message": "Memory not found"}), 404
        
        audio_filename = row[0]
        
        # Delete the memory from database
        cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
        
        # Delete associated comments if any
        cursor.execute('DELETE FROM comments WHERE memory_id = ?', (memory_id,))
        
        # Delete associated media links
        cursor.execute('DELETE FROM memory_media WHERE memory_id = ?', (memory_id,))
        
        db.commit()
        
        # Delete audio file if it exists
        if audio_filename:
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Delete from audio_transcriptions table
            cursor.execute('DELETE FROM audio_transcriptions WHERE audio_filename = ?', (audio_filename,))
            db.commit()
        
        return jsonify({
            "status": "success",
            "message": "Memory deleted successfully",
            "deleted_audio": bool(audio_filename)
        })
        
    except Exception as e:
        print(f"Error deleting memory: {e}")
        return jsonify({"status": "error", "message": "Failed to delete memory"}), 500

@app.route('/api/memories/get', methods=['GET'])
def get_memories():
    """Get all memories for the timeline."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''SELECT id, text, category, memory_date, year, 
                         audio_filename, created_at 
                         FROM memories 
                         ORDER BY COALESCE(year, 9999) ASC, created_at ASC''')
        
        memories = []
        for row in cursor.fetchall():
            memories.append({
                'id': row[0],
                'text': row[1],
                'category': row[2],
                'memory_date': row[3],
                'year': row[4],
                'audio_filename': row[5],
                'created_at': row[6],
                'has_audio': bool(row[5])
            })
        
        return jsonify({
            "status": "success",
            "memories": memories
        })
        
    except Exception as e:
        print(f"Error getting memories: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve memories"}), 500

@app.route('/api/memories/<int:memory_id>/media', methods=['GET'])
def get_memory_media(memory_id):
    """Get all media linked to a specific memory."""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT m.id, m.filename, m.original_filename, m.file_type, 
                   m.title, m.description, m.media_date, m.year, 
                   mm.display_order
            FROM media m
            JOIN memory_media mm ON m.id = mm.media_id
            WHERE mm.memory_id = ?
            ORDER BY mm.display_order
        ''', (memory_id,))
        
        media = []
        for row in cursor.fetchall():
            media.append({
                'id': row[0],
                'filename': row[1],
                'original_filename': row[2],
                'file_type': row[3],
                'title': row[4],
                'description': row[5],
                'media_date': row[6],
                'year': row[7],
                'display_order': row[8]
            })
        
        return jsonify({'status': 'success', 'media': media})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/memories/<int:memory_id>/media/<int:media_id>', methods=['POST'])
def add_media_to_memory(memory_id, media_id):
    """Link a single media item to a memory."""
    try:
        db = get_db()
        cursor = db.execute(
            'SELECT COALESCE(MAX(display_order), -1) FROM memory_media WHERE memory_id = ?',
            (memory_id,)
        )
        max_order = cursor.fetchone()[0]
        
        db.execute(
            'INSERT OR IGNORE INTO memory_media (memory_id, media_id, display_order) VALUES (?, ?, ?)',
            (memory_id, media_id, max_order + 1)
        )
        db.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/memories/<int:memory_id>/media/<int:media_id>', methods=['DELETE'])
def remove_media_from_memory(memory_id, media_id):
    """Remove a media link."""
    try:
        db = get_db()
        db.execute('DELETE FROM memory_media WHERE memory_id = ? AND media_id = ?', 
                  (memory_id, media_id))
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/memories/<int:memory_id>/media', methods=['POST'])
def link_multiple_media_to_memory(memory_id):
    """Link multiple media items to a memory at once (bulk operation)."""
    try:
        data = request.json
        media_ids = data.get('media_ids', [])
        
        db = get_db()
        
        # Clear existing links for this memory
        db.execute('DELETE FROM memory_media WHERE memory_id = ?', (memory_id,))
        
        # Add new links with order
        for order, media_id in enumerate(media_ids):
            db.execute(
                'INSERT INTO memory_media (memory_id, media_id, display_order) VALUES (?, ?, ?)',
                (memory_id, media_id, order)
            )
        
        db.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f'Linked {len(media_ids)} media items to memory'
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/media/available', methods=['GET'])
def get_available_media():
    """Get all available media for linking (used by photo picker UI)."""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT id, filename, original_filename, file_type, 
                   title, description, memory_date, year, created_at
            FROM media
            ORDER BY 
                CASE WHEN year IS NOT NULL THEN year ELSE 9999 END DESC,
                created_at DESC
        ''')
        
        media = []
        for row in cursor.fetchall():
            media.append({
                'id': row[0],
                'filename': row[1],
                'original_filename': row[2],
                'file_type': row[3],
                'title': row[4],
                'description': row[5],
                'media_date': row[6],
                'year': row[7],
                'created_at': row[8]
            })
        
        return jsonify({'status': 'success', 'media': media})
    
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ============================================
# SEARCH ROUTES
# ============================================

@app.route('/api/memories/<int:memory_id>', methods=['PUT'])
def update_memory(memory_id):
    """Update an existing memory."""
    try:
        data = request.json
        text = data.get('text', '').strip()
        date_input = data.get('date', '').strip()
        
        if not text:
            return jsonify({"status": "error", "message": "Memory text is required"}), 400
        
        db = get_db()
        
        # Parse date
        fuzzy_date = None
        year = None
        
        if date_input:
            # New date provided - parse it
            date_result = parse_date_input(date_input)
            if date_result:
                if isinstance(date_result, tuple):
                    fuzzy_date, year = date_result
                else:
                    fuzzy_date = date_result
        else:
            # No date provided - preserve existing date and year
            cursor = db.execute('SELECT year, memory_date FROM memories WHERE id = ?', (memory_id,))
            existing = cursor.fetchone()
            if existing:
                year = existing[0]
                fuzzy_date = existing[1]
        
        # Get category
        category = categorize_memory(text, year=year)
        
        # Update memory
        db.execute('''
            UPDATE memories 
            SET text = ?, category = ?, memory_date = ?, year = ?
            WHERE id = ?
        ''', (text, category, fuzzy_date, year, memory_id))
        
        db.commit()
        
        return jsonify({
            "status": "success",
            "message": "Memory updated successfully",
            "memory": {
                "id": memory_id,
                "text": text,
                "category": category,
                "year": year,
                "date": fuzzy_date
            }
        })
        
    except Exception as e:
        print(f"Error updating memory: {e}")
        return jsonify({"status": "error", "message": "Failed to update memory"}), 500

@app.route('/api/memories/<int:memory_id>', methods=['GET'])
def get_memory(memory_id):
    """Get a specific memory for editing."""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT id, text, category, memory_date, year, created_at
            FROM memories
            WHERE id = ?
        ''', (memory_id,))
        
        memory = cursor.fetchone()
        
        if not memory:
            return jsonify({"status": "error", "message": "Memory not found"}), 404
        
        mem_id, text, category, memory_date, year, created_at = memory
        
        return jsonify({
            "status": "success",
            "memory": {
                "id": mem_id,
                "text": text,
                "category": category,
                "memory_date": memory_date,
                "year": year,
                "created_at": created_at
            }
        })
        
    except Exception as e:
        print(f"Get memory error: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve memory"}), 500

@app.route('/api/search/smart', methods=['POST'])
def smart_search():
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"status": "error", "message": "No query provided"}), 400
        
        search_engine = EnhancedSearch()
        results = search_engine.search_memories(query)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/search/ai', methods=['POST'])
def ai_search():
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"status": "error", "message": "No query provided"}), 400
        
        # Use AI-powered search
        result = ai_searcher.search_with_context(query)
        
        return jsonify({
            "query": query,
            "result": result,
            "ai_available": ai_searcher.client is not None
        })
        
    except Exception as e:
        print(f"AI search error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# MEDIA ROUTES
# ============================================

@app.route('/api/audio/save', methods=['POST'])
def save_audio_recording():
    """Save voice recording to server."""
    try:
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No audio file"}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"voice_recording_{timestamp}.webm"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save audio file
        audio_file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Save to database
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO audio_transcriptions 
                         (audio_filename, transcription_text, created_at) 
                         VALUES (?, ?, ?)''',
                      (filename, '', datetime.now().isoformat()))
        db.commit()
        audio_id = cursor.lastrowid
        
        return jsonify({
            "status": "success",
            "filename": filename,
            "audio_id": audio_id,
            "size": file_size
        })
        
    except Exception as e:
        print(f"Error saving audio: {e}")
        return jsonify({"status": "error", "message": "Failed to save audio"}), 500

@app.route('/api/audio/<filename>', methods=['GET'])
def serve_audio(filename):
    """Serve audio file for playback."""
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "Audio file not found"}), 404
        
        return send_file(filepath, mimetype='audio/webm')
    except Exception as e:
        print(f"Error serving audio: {e}")
        return jsonify({"status": "error", "message": "Failed to serve audio"}), 404

@app.route('/api/media/upload', methods=['POST'])
def upload_media():
    try:
        if 'media' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        
        file = request.files['media']
        title = request.form.get('title', 'Untitled')
        description = request.form.get('description', '')
        memory_date = request.form.get('memory_date', '')
        year = request.form.get('year', '')
        people = request.form.get('people', '')
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp3', 'wav', 'mp4', 'mov', 'avi'}
        file_ext = os.path.splitext(file.filename)[1].lower().replace('.', '')
        
        if file_ext not in allowed_extensions:
            return jsonify({
                "status": "error", 
                "message": f"File type .{file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
            }), 400
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        original_filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_id}_{original_filename}"
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Get file size - CRITICAL FIX: Add this line
        file_size = os.path.getsize(filepath)
        
        # Determine file type category
        if file_ext in {'png', 'jpg', 'jpeg', 'gif'}:
            file_type = 'image'
        elif file_ext in {'mp3', 'wav'}:
            file_type = 'audio'
        elif file_ext in {'mp4', 'mov', 'avi'}:
            file_type = 'video'
        elif file_ext == 'pdf':
            file_type = 'document'
        else:
            file_type = 'other'
        
        # Store in database
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO media 
                         (filename, original_filename, file_type, file_size, title, description, 
                          memory_date, year, people, uploaded_by, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (unique_filename, original_filename, file_type, file_size, title, description,
                       memory_date, year, people, 'user', datetime.now().isoformat()))
        
        db.commit()
        media_id = cursor.lastrowid
        
        return jsonify({
            "status": "success",
            "message": "File uploaded successfully",
            "data": {
                "id": media_id,
                "filename": unique_filename,
                "original_filename": original_filename,
                "file_type": file_type,
                "file_size": file_size,
                "title": title,
                "description": description,
                "url": f"/uploads/{unique_filename}",
                "uploaded_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"status": "error", "message": "Failed to upload file"}), 500

@app.route('/api/export/biography/generate', methods=['POST'])
def generate_biography_draft():
    """Generate biography drafts using both DeepSeek and Claude."""
    try:
        data = request.json or {}
        model = data.get('model', 'both')
        
        # Check API keys
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if model in ['deepseek', 'both'] and not deepseek_key:
            return jsonify({
                'status': 'error',
                'message': 'DeepSeek API key not configured'
            }), 400
        
        if model in ['claude', 'both'] and not anthropic_key:
            return jsonify({
                'status': 'error',
                'message': 'Anthropic API key not configured'
            }), 400
        
        # Fetch all memories
        db = get_db()
        cursor = db.execute('''
            SELECT id, text, year, category, memory_date
            FROM memories
            ORDER BY COALESCE(year, 9999) ASC, created_at ASC
        ''')
        
        memories = []
        for row in cursor.fetchall():
            memories.append({
                'id': row[0],
                'text': row[1],
                'year': row[2],
                'category': row[3],
                'memory_date': row[4]
            })
        
        if not memories:
            return jsonify({
                'status': 'error',
                'message': 'No memories found to generate biography'
            }), 400
        
        result = {
            'status': 'success',
            'memory_count': len(memories)
        }
        
        # Generate with DeepSeek
        if model in ['deepseek', 'both']:
            try:
                deepseek_narrative = generate_biography_deepseek(memories)
                deepseek_chapters = parse_biography_into_chapters(deepseek_narrative)
                result['deepseek'] = {
                    'chapters': deepseek_chapters,
                    'full_text': deepseek_narrative
                }
            except Exception as e:
                print(f"DeepSeek generation error: {e}")
                result['deepseek'] = {'error': str(e)}
        
        # Generate with Claude
        if model in ['claude', 'both']:
            try:
                claude_narrative = generate_biography_claude(memories)
                claude_chapters = parse_biography_into_chapters(claude_narrative)
                result['claude'] = {
                    'chapters': claude_chapters,
                    'full_text': claude_narrative
                }
            except Exception as e:
                print(f"Claude generation error: {e}")
                result['claude'] = {'error': str(e)}
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Biography generation error: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate biography'
        }), 500

@app.route('/api/export/biography/save-edits', methods=['POST'])
def save_biography_edits():
    """Save user's edited biography version."""
    try:
        data = request.json
        chapters = data.get('chapters', [])
        model_used = data.get('model', 'unknown')
        
        # Validate chapters
        if not chapters or not isinstance(chapters, list):
            return jsonify({
                'status': 'error',
                'message': 'Invalid chapters data'
            }), 400
        
        # Store in session
        session['biography_draft'] = {
            'chapters': chapters,
            'model': model_used,
            'edited': True,
            'saved_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Biography draft saved',
            'chapter_count': len(chapters)
        })
    
    except Exception as e:
        print(f"Error saving biography edits: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save biography'
        }), 500

@app.route('/api/export/biography/pdf', methods=['POST'])
def generate_biography_pdf_route():
    """Generate magazine-style PDF from approved biography draft."""
    try:
        data = request.json or {}
        chapters = data.get('chapters', [])
        title = data.get('title', 'The Making of a Life')
        subtitle = data.get('subtitle', 'A Family Story')
        include_photos = data.get('include_photos', True)
        
        if not chapters:
            # Try to get from session
            draft = session.get('biography_draft')
            if draft:
                chapters = draft['chapters']
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No biography chapters found'
                }), 400
        
        # Validate chapters
        if not isinstance(chapters, list) or len(chapters) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Invalid chapters data'
            }), 400
        
        # Import the generator functions
        try:
            from biography_pdf_generator import generate_biography_pdf
        except ImportError as e:
            print(f"Import error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'PDF generation module not available'
            }), 500
        
        # Generate PDF
        pdf_buffer = generate_biography_pdf(
            chapters,
            title,
            subtitle,
            UPLOAD_FOLDER,
            hero_photo=None
        )
        
        filename = f'family_biography_{title.replace(" ", "_").lower()}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        print(f"PDF generation error: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate PDF'
        }), 500

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Serve uploaded files directly."""
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # Determine MIME type
        if safe_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            mimetype = 'image/jpeg'
            cache_timeout = 31536000
        elif safe_filename.lower().endswith('.pdf'):
            mimetype = 'application/pdf'
            cache_timeout = 3600
        elif safe_filename.lower().endswith(('.mp3', '.wav')):
            mimetype = 'audio/mpeg'
            cache_timeout = 3600
        elif safe_filename.lower().endswith(('.mp4', '.mov', '.avi')):
            mimetype = 'video/mp4'
            cache_timeout = 3600
        else:
            mimetype = 'application/octet-stream'
            cache_timeout = 3600
        
        return send_file(filepath, mimetype=mimetype, max_age=cache_timeout)
        
    except Exception as e:
        print(f"Error serving file: {e}")
        return jsonify({"status": "error", "message": "Failed to serve file"}), 500

@app.route('/api/media/all', methods=['GET'])
def get_all_media():
    """Get all uploaded media files."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, filename, original_filename, file_type, file_size, title, 
                   description, memory_date, year, people, created_at 
            FROM media 
            ORDER BY created_at DESC
        """)
        
        media_items = []
        for row in cursor.fetchall():
            media_items.append({
                "id": row[0],
                "filename": row[1],
                "original_filename": row[2],
                "file_type": row[3],
                "file_size": row[4],
                "title": row[5],
                "description": row[6],
                "memory_date": row[7],
                "year": row[8],
                "people": row[9],
                "created_at": row[10],
                "url": f"/uploads/{row[1]}"
            })
        
        return jsonify(media_items)
        
    except Exception as e:
        print(f"Error getting media: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve media"}), 500

@app.route('/api/media/delete/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    """Delete a media file."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get filename before deleting
        cursor.execute("SELECT filename FROM media WHERE id = ?", (media_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"status": "error", "message": "Media not found"}), 404
        
        filename = result[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Delete from memory_media links first
        cursor.execute("DELETE FROM memory_media WHERE media_id = ?", (media_id,))
        
        # Delete from database
        cursor.execute("DELETE FROM media WHERE id = ?", (media_id,))
        db.commit()
        
        # Delete file from disk
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Warning: Could not delete file {filepath}: {e}")
        
        return jsonify({"status": "success", "message": "Media deleted successfully"})
        
    except Exception as e:
        print(f"Error deleting media: {e}")
        db.rollback()
        return jsonify({"status": "error", "message": "Failed to delete media"}), 500

@app.route('/api/media/preview/<filename>')
def media_preview(filename):
    """Generate thumbnail/preview for images."""
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # For now, just serve the original image
        # In production, you'd want to resize images here
        return send_file(filepath)
        
    except Exception as e:
        print(f"Error serving preview: {e}")
        return jsonify({"status": "error", "message": "Failed to serve preview"}), 500

@app.route('/api/media/<int:media_id>/update', methods=['PUT'])
def update_media(media_id):
    """Update media title and description."""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({"status": "error", "message": "Title cannot be empty"}), 400
            updates.append("title = ?")
            values.append(title)
        
        if 'description' in data:
            updates.append("description = ?")
            values.append(data['description'].strip())
        
        if not updates:
            return jsonify({"status": "error", "message": "Nothing to update"}), 400
        
        # Add media_id to values
        values.append(media_id)
        
        # Execute update
        query = f"UPDATE media SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        db.commit()
        
        if cursor.rowcount == 0:
            return jsonify({"status": "error", "message": "Media not found"}), 404
        
        return jsonify({
            "status": "success",
            "message": "Media updated successfully",
            "updates": data
        })
        
    except Exception as e:
        print(f"Update media error: {e}")
        return jsonify({"status": "error", "message": "Failed to update media"}), 500

# ============================================
# AI PHOTO MATCHING ROUTES
# ============================================

@app.route('/api/memories/<int:memory_id>/suggest-photos', methods=['GET'])
def get_photo_suggestions(memory_id):
    """Get AI-suggested photos for a memory."""
    try:
        threshold = request.args.get("threshold", 50, type=int)
        
        suggestions = suggest_photos_for_memory(
            memory_id, 
            confidence_threshold=threshold
        )
        
        return jsonify({
            'status': 'success',
            'memory_id': memory_id,
            'suggestions': suggestions,
            'threshold': threshold
        })
    
    except Exception as e:
        print(f"Photo suggestion error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Failed to get photo suggestions'
        }), 500

@app.route('/api/memories/<int:memory_id>/browse-photos', methods=['GET'])
def browse_all_photos(memory_id):
    """Get all unlinked photos for manual selection."""
    try:
        db = get_db()
        
        # Get all photos NOT already linked to this memory
        cursor = db.execute('''
            SELECT m.id, m.filename, m.title, m.description, m.year
            FROM media m
            WHERE m.file_type = 'image'
            AND m.id NOT IN (
                SELECT media_id FROM memory_media WHERE memory_id = ?
            )
            ORDER BY m.year DESC, m.created_at DESC
        ''', (memory_id,))
        
        photos = cursor.fetchall()
        
        results = []
        for photo in photos:
            photo_id, filename, title, desc, year = photo
            results.append({
                'id': photo_id,
                'filename': filename,
                'title': title or filename,
                'description': desc or '',
                'year': year or 'Unknown'
            })
        
        return jsonify({
            'status': 'success',
            'memory_id': memory_id,
            'photos': results,
            'count': len(results)
        })
    
    except Exception as e:
        print(f"Browse photos error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to browse photos'
        }), 500

@app.route('/api/memories/<int:memory_id>/accept-suggestion', methods=['POST'])
def accept_photo_suggestion(memory_id):
    """Accept an AI photo suggestion and link it."""
    try:
        data = request.json
        photo_id = data.get('photo_id')
        
        if not photo_id:
            return jsonify({
                'status': 'error',
                'error': 'photo_id required'
            }), 400
        
        apply_suggestion(memory_id, photo_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Photo {photo_id} linked to memory {memory_id}'
        })
    
    except Exception as e:
        print(f"Accept suggestion error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Failed to accept suggestion'
        }), 500

@app.route('/api/memories/suggest-all', methods=['POST'])
def suggest_all_photos():
    """Get AI suggestions for all memories (batch processing)."""
    try:
        data = request.json or {}
        threshold = data.get('threshold', 70)
        
        all_suggestions = suggest_all_memories(
            confidence_threshold=threshold
        )
        
        # Count totals
        total_suggestions = sum(len(sug) for sug in all_suggestions.values())
        
        return jsonify({
            'status': 'success',
            'suggestions': all_suggestions,
            'summary': {
                'memories_with_suggestions': len(all_suggestions),
                'total_suggestions': total_suggestions,
                'threshold': threshold
            }
        })
    
    except Exception as e:
        print(f"Suggest all error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Failed to get suggestions'
        }), 500

# ============================================
# PDF ROUTES
# ============================================

@app.route('/api/pdf/generate/<pdf_type>', methods=['POST'])
def generate_pdf(pdf_type):
    try:
        if pdf_type == 'album':
            pdf_path = generate_family_album_pdf()
        else:
            pdf_path = generate_memory_pdf(pdf_type)
        
        return send_file(pdf_path, as_attachment=True)
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        return jsonify({"status": "error", "message": "Failed to generate PDF"}), 500

@app.route('/api/debug/media', methods=['GET'])
def debug_media():
    """Debug endpoint to see what's in database vs filesystem."""
    import os
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, filename, original_filename FROM media ORDER BY id")
    db_files = cursor.fetchall()
    
    uploads_dir = app.config['UPLOAD_FOLDER']
    fs_files = os.listdir(uploads_dir) if os.path.exists(uploads_dir) else []
    
    return jsonify({
        "database_files": [{"id": row[0], "filename": row[1], "original_filename": row[2]} for row in db_files],
        "filesystem_files": fs_files,
        "uploads_folder": uploads_dir
    })

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')

        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400

        # Register user
        user = AuthService.register_user(username, email, password, full_name)

        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'user': user
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        security_logger.log_error(f"Registration error: {str(e)}", e)
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return tokens."""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Authenticate user
        result = AuthService.login(username, password)

        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'user': result['user'],
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token']
        }), 200

    except InvalidCredentialsError as e:
        return jsonify({'error': str(e)}), 401
    except AccountLockedError as e:
        return jsonify({'error': str(e)}), 423
    except Exception as e:
        security_logger.log_error(f"Login error: {str(e)}", e)
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user and revoke refresh token."""
    try:
        data = request.json or {}
        refresh_token = data.get('refresh_token')

        # Logout user
        AuthService.logout(g.current_user['id'], refresh_token)

        return jsonify({
            'status': 'success',
            'message': 'Logout successful'
        }), 200

    except Exception as e:
        security_logger.log_error(f"Logout error: {str(e)}", e)
        return jsonify({'error': 'Logout failed'}), 500


@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token."""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400

        # Generate new tokens
        access_token, new_refresh_token = AuthService.refresh_access_token(refresh_token)

        return jsonify({
            'status': 'success',
            'access_token': access_token,
            'refresh_token': new_refresh_token
        }), 200

    except TokenExpiredError:
        return jsonify({'error': 'Refresh token has expired'}), 401
    except InvalidTokenError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        security_logger.log_error(f"Token refresh error: {str(e)}", e)
        return jsonify({'error': 'Token refresh failed'}), 500


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change user password."""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({'error': 'Old password and new password are required'}), 400

        # Change password
        AuthService.change_password(g.current_user['id'], old_password, new_password)

        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        }), 200

    except InvalidCredentialsError as e:
        return jsonify({'error': str(e)}), 401
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        security_logger.log_error(f"Password change error: {str(e)}", e)
        return jsonify({'error': 'Password change failed'}), 500


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user information."""
    try:
        user = g.current_user

        return jsonify({
            'status': 'success',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role'],
                'is_active': user['is_active'],
                'last_login': user['last_login'],
                'created_at': user['created_at']
            }
        }), 200

    except Exception as e:
        security_logger.log_error(f"Get user error: {str(e)}", e)
        return jsonify({'error': 'Failed to get user information'}), 500


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"status": "error", "message": "File too large"}), 413

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("THE CIRCLE - Family Memory Preservation App")
    print("="*60)
    print(f"Local URL: http://localhost:5000")
    print(f"AI Search: {'ENABLED' if ai_searcher.client else 'DISABLED (set DEEPSEEK_API_KEY)'}")
    print("="*60)
    print("Press Ctrl+C to stop the server\n")
    
    app.run(debug=True, port=5000)