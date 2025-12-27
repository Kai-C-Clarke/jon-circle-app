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
        
        # Parse date - parse_date_input returns (date_string, year) tuple
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
        return jsonify({"status": "error", "message": str(e)}), 500
