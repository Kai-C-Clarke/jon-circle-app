#!/usr/bin/env python3
"""
Biography PDF Generator
Creates magazine-style PDFs from AI-generated biographies with integrated photos
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from PIL import Image as PILImage
import os

# Autumn color palette
AUTUMN_GOLD = HexColor('#e8b44f')
AUTUMN_BURGUNDY = HexColor('#8B4513')
AUTUMN_CREAM = HexColor('#F5F5DC')
DARK_TEXT = HexColor('#2c3e50')
LIGHT_TEXT = HexColor('#666666')

def create_cover_page(story, title, subtitle, hero_photo_path=None):
    """Create magazine-style cover page."""
    
    elements = []
    
    # Add hero photo if available
    if hero_photo_path and os.path.exists(hero_photo_path):
        try:
            img = Image(hero_photo_path, width=6*inch, height=4*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        except:
            pass
    else:
        elements.append(Spacer(1, 2*inch))
    
    # Title
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=getSampleStyleSheet()['Title'],
        fontSize=36,
        textColor=AUTUMN_BURGUNDY,
        alignment=TA_CENTER,
        spaceAfter=12,
        leading=42,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Subtitle
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=18,
        textColor=AUTUMN_GOLD,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 1*inch))
    
    # Decorative line
    line_table = Table([['']], colWidths=[4*inch])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,0), 2, AUTUMN_GOLD),
    ]))
    elements.append(line_table)
    
    elements.append(PageBreak())
    
    return elements


def match_photos_to_chapter(chapter_title, chapter_text, available_photos):
    """Match photos to chapter based on content and years."""
    matched_photos = []
    
    # Extract year range from chapter title
    import re
    year_match = re.search(r'\((\d{4})-(\d{4})\)', chapter_title)
    if year_match:
        start_year = int(year_match.group(1))
        end_year = int(year_match.group(2))
        
        # Find photos within year range
        for photo in available_photos:
            if photo.get('year'):
                try:
                    photo_year = int(photo['year'])
                    if start_year <= photo_year <= end_year:
                        matched_photos.append(photo)
                except:
                    pass
    
    # Also match by keywords in chapter text
    chapter_lower = (chapter_title + ' ' + chapter_text).lower()
    keywords_found = {}
    
    for photo in available_photos:
        if photo in matched_photos:
            continue
            
        score = 0
        title = photo.get('title', '').lower()
        desc = photo.get('description', '').lower()
        
        # Check for name mentions
        if 'gloria' in chapter_lower and 'gloria' in (title + desc):
            score += 10
        if 'john' in chapter_lower and 'john' in (title + desc):
            score += 10
        if 'jane' in chapter_lower and 'jane' in (title + desc):
            score += 10
        
        # Check for location mentions
        if 'battle' in chapter_lower and 'battle' in (title + desc):
            score += 5
        if 'garage' in chapter_lower and 'garage' in (title + desc):
            score += 5
        
        if score > 0:
            keywords_found[photo['id']] = score
    
    # Add top keyword matches
    for photo_id, score in sorted(keywords_found.items(), key=lambda x: x[1], reverse=True)[:2]:
        for photo in available_photos:
            if photo['id'] == photo_id and photo not in matched_photos:
                matched_photos.append(photo)
    
    return matched_photos[:3]  # Max 3 photos per chapter


def create_chapter_content(chapter, photos, upload_folder):
    """Create formatted chapter with integrated photos."""
    
    elements = []
    
    # Chapter title
    chapter_style = ParagraphStyle(
        'ChapterTitle',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=24,
        textColor=AUTUMN_GOLD,
        spaceAfter=20,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(chapter['title'], chapter_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Chapter text - split into paragraphs
    body_style = ParagraphStyle(
        'ChapterBody',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=11,
        textColor=DARK_TEXT,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=16,
        fontName='Helvetica'
    )
    
    paragraphs = chapter['narrative'].split('\n\n')
    
    # Insert first photo after first paragraph if available
    if paragraphs and photos:
        elements.append(Paragraph(paragraphs[0], body_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add first photo
        photo = photos[0]
        photo_path = os.path.join(upload_folder, photo['filename'])
        
        if os.path.exists(photo_path):
            try:
                # Resize image to fit
                img = Image(photo_path, width=5*inch, height=3.5*inch)
                elements.append(img)
                
                # Photo caption
                caption_style = ParagraphStyle(
                    'PhotoCaption',
                    parent=getSampleStyleSheet()['Normal'],
                    fontSize=9,
                    textColor=LIGHT_TEXT,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Oblique',
                    spaceAfter=12
                )
                
                caption = photo.get('title', '')
                if photo.get('year'):
                    caption += f" ({photo['year']})"
                
                elements.append(Paragraph(caption, caption_style))
                elements.append(Spacer(1, 0.2*inch))
            except:
                pass
        
        # Add remaining paragraphs
        for para in paragraphs[1:]:
            if para.strip():
                elements.append(Paragraph(para, body_style))
    else:
        # No photos, just add all text
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para, body_style))
    
    # Add remaining photos at end of chapter if any
    for photo in photos[1:]:
        photo_path = os.path.join(upload_folder, photo['filename'])
        
        if os.path.exists(photo_path):
            try:
                elements.append(Spacer(1, 0.2*inch))
                img = Image(photo_path, width=4*inch, height=3*inch)
                elements.append(img)
                
                caption_style = ParagraphStyle(
                    'PhotoCaption',
                    parent=getSampleStyleSheet()['Normal'],
                    fontSize=9,
                    textColor=LIGHT_TEXT,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Oblique',
                    spaceAfter=12
                )
                
                caption = photo.get('title', '')
                if photo.get('year'):
                    caption += f" ({photo['year']})"
                
                elements.append(Paragraph(caption, caption_style))
            except:
                pass
    
    elements.append(PageBreak())
    
    return elements


def generate_biography_pdf(chapters, title, subtitle, upload_folder, hero_photo=None):
    """Generate complete biography PDF with cover and photos."""
    
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    story = []
    
    # Get all available photos
    import sqlite3
    db = sqlite3.connect('circle_memories.db')
    cursor = db.execute('''
        SELECT id, filename, title, description, year
        FROM media
        WHERE file_type = 'image'
    ''')
    
    available_photos = []
    for row in cursor.fetchall():
        available_photos.append({
            'id': row[0],
            'filename': row[1],
            'title': row[2] or '',
            'description': row[3] or '',
            'year': row[4]
        })
    
    db.close()
    
    # Create cover
    cover_elements = create_cover_page(story, title, subtitle, hero_photo)
    story.extend(cover_elements)
    
    # Create chapters with photos
    for chapter in chapters:
        # Match photos to this chapter
        chapter_photos = match_photos_to_chapter(
            chapter['title'],
            chapter['narrative'],
            available_photos
        )
        
        # Create chapter content
        chapter_elements = create_chapter_content(
            chapter,
            chapter_photos,
            upload_folder
        )
        
        story.extend(chapter_elements)
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer


# Add route to app.py:
"""
@app.route('/api/export/biography/pdf', methods=['POST'])
def generate_biography_pdf_route():
    try:
        data = request.json
        chapters = data.get('chapters', [])
        title = data.get('title', 'The Making of a Life')
        subtitle = data.get('subtitle', 'A Family Story')
        
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
        
        # Generate PDF
        pdf_buffer = generate_biography_pdf(
            chapters,
            title,
            subtitle,
            UPLOAD_FOLDER,
            hero_photo=None  # TODO: Let user select hero photo
        )
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='family_biography.pdf'
        )
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
"""
