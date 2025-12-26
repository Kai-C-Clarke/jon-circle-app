## REPLACE THE /api/export/biography/pdf ROUTE in app.py (lines 954-1000)
## WITH THIS DEBUG VERSION:

@app.route('/api/export/biography/pdf', methods=['POST'])
def generate_biography_pdf_route():
    """Generate magazine-style PDF from approved biography draft."""
    print("\n" + "="*70)
    print("📄 PDF GENERATION REQUEST RECEIVED")
    print("="*70)
    
    try:
        data = request.json or {}
        chapters = data.get('chapters', [])
        title = data.get('title', 'The Making of a Life')
        subtitle = data.get('subtitle', 'A Family Story')
        include_photos = data.get('includePhotos', True)
        
        print(f"📖 Title: {title}")
        print(f"📝 Subtitle: {subtitle}")
        print(f"🖼️  Include photos: {include_photos}")
        print(f"📚 Chapters provided: {len(chapters)}")
        
        if not chapters:
            # Try to get from session
            print("⚠️  No chapters in request, checking session...")
            draft = session.get('biography_draft')
            if draft:
                chapters = draft['chapters']
                print(f"✓ Found {len(chapters)} chapters in session")
            else:
                print("❌ No chapters in session either")
                return jsonify({
                    'status': 'error',
                    'message': 'No biography chapters found'
                }), 400
        
        # Import the generator functions
        print("📦 Importing biography_pdf_generator...")
        try:
            from biography_pdf_generator import generate_biography_pdf
            print("✓ Module imported successfully")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            raise
        
        # Generate PDF
        print(f"🎨 Generating PDF with {len(chapters)} chapters...")
        pdf_buffer = generate_biography_pdf(
            chapters,
            title,
            subtitle,
            UPLOAD_FOLDER,
            hero_photo=None
        )
        
        pdf_size = len(pdf_buffer.getvalue())
        print(f"✅ PDF generated! Size: {pdf_size:,} bytes")
        
        filename = f'family_biography_{title.replace(" ", "_").lower()}.pdf'
        print(f"📥 Sending file: {filename}")
        print("="*70 + "\n")
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        print(f"\n❌ PDF GENERATION ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
