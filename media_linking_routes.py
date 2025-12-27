"""
API Routes for Memory-Media Linking
Add these routes to your Flask app.py
"""

from flask import Blueprint, request, jsonify
from database import get_db

# Create a blueprint (or add directly to your main app)
media_linking_bp = Blueprint('media_linking', __name__)

@media_linking_bp.route('/api/memories/<int:memory_id>/media', methods=['GET'])
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
        
        return jsonify({'success': True, 'media': media})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@media_linking_bp.route('/api/memories/<int:memory_id>/media', methods=['POST'])
def link_media_to_memory(memory_id):
    """Link multiple media items to a memory."""
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
            'success': True, 
            'message': f'Linked {len(media_ids)} media items to memory'
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@media_linking_bp.route('/api/memories/<int:memory_id>/media/<int:media_id>', methods=['POST'])
def add_single_media_to_memory(memory_id, media_id):
    """Add a single media item to a memory."""
    try:
        db = get_db()
        
        # Get current max display_order
        cursor = db.execute(
            'SELECT COALESCE(MAX(display_order), -1) FROM memory_media WHERE memory_id = ?',
            (memory_id,)
        )
        max_order = cursor.fetchone()[0]
        
        # Insert new link
        db.execute(
            'INSERT OR IGNORE INTO memory_media (memory_id, media_id, display_order) VALUES (?, ?, ?)',
            (memory_id, media_id, max_order + 1)
        )
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Media linked to memory'})
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@media_linking_bp.route('/api/memories/<int:memory_id>/media/<int:media_id>', methods=['DELETE'])
def remove_media_from_memory(memory_id, media_id):
    """Remove a specific media item from a memory."""
    try:
        db = get_db()
        
        db.execute(
            'DELETE FROM memory_media WHERE memory_id = ? AND media_id = ?',
            (memory_id, media_id)
        )
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Media unlinked from memory'})
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@media_linking_bp.route('/api/media/available', methods=['GET'])
def get_available_media():
    """Get all available media for linking."""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT id, filename, original_filename, file_type, 
                   title, description, media_date, year, created_at
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
        
        return jsonify({'success': True, 'media': media})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# To use in your app.py:
# from media_linking_routes import media_linking_bp
# app.register_blueprint(media_linking_bp)
