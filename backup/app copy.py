# app.py - Main Flask application
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os
from datetime import datetime

# Import our modules
from database import init_db, get_db
from search_engine import EnhancedSearch
from ai_search import ai_searcher  # NEW: Import AI search
from utils import allowed_file, parse_date_input, categorize_memory
from pdf_generator import generate_memory_pdf, generate_family_album_pdf
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize database on startup
init_db()

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

# ============================================
# BASIC ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "time": datetime.now().isoformat(),
        "ai_search": ai_searcher.client is not None
    })

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
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"status": "error", "message": "No text provided"}), 400
        
        memory_date, year = parse_date_input(data.get('date_input', ''))
        if not memory_date:
            # Try to extract from text
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', text)
            if year_match:
                year = int(year_match.group(0))
        
        category = categorize_memory(text)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO memories (text, category, memory_date, year, created_at) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (text, category, memory_date, year, datetime.now().isoformat()))
        
        db.commit()
        return jsonify({
            "status": "success",
            "id": cursor.lastrowid,
            "category": category,
            "year": year
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/memories/get', methods=['GET'])
def get_memories():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, text, category, memory_date, year FROM memories ORDER BY year DESC")
        
        memories = []
        for row in cursor.fetchall():
            memories.append({
                "id": row[0],
                "text": row[1],
                "category": row[2],
                "date": row[3],
                "year": row[4]
            })
        
        return jsonify(memories)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# SEARCH ROUTES
# ============================================

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

# NEW: AI-Powered Search Route
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
        
        # Get file size - THIS IS MISSING!
        file_size = os.path.getsize(filepath)  # <-- ADD THIS LINE
        
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
        
        # Store in database - MAKE SURE file_size IS INCLUDED
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO media 
                         (filename, original_filename, file_type, file_size, title, description, 
                          memory_date, year, people, uploaded_by, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (unique_filename, original_filename, file_type, file_size, title, description,
                       memory_date, year, people, 'user', datetime.now().isoformat()))  # <-- file_size is now included
        
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
                "file_size": file_size,  # <-- Include in response
                "title": title,
                "description": description,
                "url": f"/uploads/{unique_filename}",
                "uploaded_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Serve uploaded files directly."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # For images, serve with proper caching
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            cache_timeout = 31536000  # 1 year cache for images
            return send_file(filepath, mimetype='image/jpeg')
        
        return send_file(filepath)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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
                "file_size": row[4],  # This is file_size
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        
        # Delete from database
        cursor.execute("DELETE FROM media WHERE id = ?", (media_id,))
        db.commit()
        
        # Delete file from disk
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({"status": "success", "message": "Media deleted successfully"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/media/preview/<filename>')
def media_preview(filename):
    """Generate thumbnail/preview for images."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # For now, just serve the original image
        # In a production app, you'd resize images here
        return send_file(filepath)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
            updates.append("title = ?")
            values.append(data['title'])
        
        if 'description' in data:
            updates.append("description = ?")
            values.append(data['description'])
        
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
        return jsonify({"status": "error", "message": str(e)}), 500
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
        return jsonify({"status": "error", "message": str(e)}), 500
    
# Add this debug route to app.py temporarily
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
        "database_files": [dict(row) for row in db_files],
        "filesystem_files": fs_files,
        "uploads_folder": uploads_dir
    })    

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