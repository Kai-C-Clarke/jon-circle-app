# Add this route after the suggest-photos route in app.py

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
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
