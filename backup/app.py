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
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        # Save file logic here (simplified)
        filename = f"temp_{datetime.now().timestamp()}.tmp"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        return jsonify({
            "status": "success",
            "filename": filename,
            "message": "File uploaded"
        })
        
    except Exception as e:
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