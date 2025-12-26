from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, 
                                PageBreak, Table, TableStyle, Frame, PageTemplate,
                                KeepTogether, FrameBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable
from PIL import Image as PILImage
import os
from datetime import datetime
from database import get_db
import re

# Autumn color palette
AUTUMN_GOLD = colors.HexColor('#E8B44F')
AUTUMN_BROWN = colors.HexColor('#8B4513')
AUTUMN_DARK = colors.HexColor('#654321')
BACKGROUND_CREAM = colors.HexColor('#FFF8F0')

class TimelineSidebar(Flowable):
    """Custom flowable for timeline markers in the margin."""
    
    def __init__(self, year, text="", width=60, height=30):
        Flowable.__init__(self)
        self.year = year
        self.text = text
        self.width = width
        self.height = height
    
    def draw(self):
        """Draw the timeline marker."""
        canvas = self.canv
        
        # Draw circle background
        canvas.setFillColor(AUTUMN_GOLD)
        canvas.circle(self.width/2, self.height/2, 20, fill=1, stroke=0)
        
        # Draw year text
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 10)
        year_str = str(self.year) if self.year else "?"
        canvas.drawCentredString(self.width/2, self.height/2 - 3, year_str)

class PullQuote(Flowable):
    """Custom flowable for pull quotes."""
    
    def __init__(self, text, width=200):
        Flowable.__init__(self)
        self.text = text
        self.width = width
        self.height = 100  # Estimated
    
    def draw(self):
        """Draw the pull quote."""
        canvas = self.canv
        
        # Background box
        canvas.setFillColor(BACKGROUND_CREAM)
        canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        
        # Left border accent
        canvas.setFillColor(AUTUMN_GOLD)
        canvas.rect(0, 0, 4, self.height, fill=1, stroke=0)
        
        # Quote text
        canvas.setFillColor(AUTUMN_DARK)
        canvas.setFont('Times-Italic', 14)
        
        # Word wrap the text
        words = self.text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if canvas.stringWidth(test_line, 'Times-Italic', 14) < self.width - 30:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines
        y = self.height - 20
        for line in lines:
            canvas.drawString(15, y, line)
            y -= 18

def extract_pull_quote(text):
    """Extract an interesting sentence as a pull quote."""
    # Look for sentences with quotes, exclamations, or interesting phrases
    sentences = re.split(r'[.!?]+', text)
    
    # Priority words for dramatic/interesting content
    priority_words = [
        'strangl', 'murder', 'petrified', 'furious', 'gob smacked', 'gobsmacked',
        'loved', 'remember', 'laughed', 'excited', 'amazing', 'stunned', 'shocked',
        'Abdul', 'bloody', 'fuck', 'shit', 'banned', 'arrested', 'disaster',
        'incredible', 'magnificent', 'wonderful', 'terrible', 'dreadful'
    ]
    
    best_quote = None
    best_score = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        if not sentence or len(sentence) < 15 or len(sentence) > 150:
            continue
        
        score = 0
        sentence_lower = sentence.lower()
        
        # Score based on interesting words
        for word in priority_words:
            if word in sentence_lower:
                score += 10
        
        # Bonus for quotes
        if '"' in sentence:
            score += 5
        
        # Bonus for exclamation
        if '!' in sentence:
            score += 3
        
        # Bonus for first-person narrative
        if any(word in sentence_lower for word in [' i ', "i'd", "i've", "i'm", 'my ']):
            score += 2
        
        if score > best_score:
            best_score = score
            best_quote = sentence.replace('"', '').replace('  ', ' ')
    
    # If we found something good, return it
    if best_score >= 5:
        return best_quote
    
    # Fallback: return first interesting sentence
    for sentence in sentences:
        sentence = sentence.strip()
        if 30 < len(sentence) < 120:
            return sentence.replace('"', '')
    
    return None

def get_linked_media(memory_id):
    """Get media explicitly linked to this memory via memory_media table."""
    db = get_db()
    cursor = db.execute('''
        SELECT m.id, m.filename, m.original_filename, m.file_type, 
               m.title, m.description, m.memory_date, m.year, m.created_at
        FROM media m
        JOIN memory_media mm ON m.id = mm.media_id
        WHERE mm.memory_id = ?
        ORDER BY mm.display_order
    ''', (memory_id,))
    return cursor.fetchall()

def match_images_to_story(story_text, story_year, media_items):
    """Find images that relate to this story."""
    # DISABLED: Automatic matching was producing poor results
    # To use images, manually link them to memories in the database
    # by adding a memory_id foreign key to the media table
    return []
    
    # Original auto-matching code (disabled):
    # matched = []
    # 
    # # Extract names from story (capitalized words)
    # words = story_text.split()
    # names = [w for w in words if len(w) > 2 and w[0].isupper() and w.isalpha()]
    # 
    # for media in media_items:
    #     media_id, filename, original, file_type, title, desc, mdate, year, created = media
    #     
    #     # Match by year (within 2 years)
    #     if year and story_year and abs(int(year) - int(story_year)) <= 2:
    #         matched.append(media)
    #         continue
    #     
    #     # Match by names in title or description
    #     media_text = f"{title} {desc}".lower()
    #     for name in names[:5]:  # Check first 5 names
    #         if name.lower() in media_text:
    #             matched.append(media)
    #             break
    # 
    # return matched[:2]  # Limit to 2 images per story

def create_custom_styles():
    """Create magazine-style paragraph styles."""
    styles = getSampleStyleSheet()
    
    # Title style (like landing page)
    styles.add(ParagraphStyle(
        name='MagazineTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=AUTUMN_BROWN,
        spaceAfter=30,
        alignment=TA_CENTER,
        leading=32
    ))
    
    # Decade header
    styles.add(ParagraphStyle(
        name='DecadeHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=36,
        textColor=AUTUMN_GOLD,
        spaceAfter=12,
        spaceBefore=24,
        alignment=TA_LEFT,
        leading=40
    ))
    
    # Story title
    styles.add(ParagraphStyle(
        name='StoryTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=AUTUMN_DARK,
        spaceAfter=8,
        spaceBefore=16,
        leading=18
    ))
    
    # Body text - justified, nice leading
    styles.add(ParagraphStyle(
        name='MagazineBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=8,
        firstLineIndent=12
    ))
    
    # Photo caption
    styles.add(ParagraphStyle(
        name='PhotoCaption',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=9,
        textColor=AUTUMN_DARK,
        alignment=TA_CENTER,
        leading=11,
        spaceAfter=12,
        spaceBefore=4
    ))
    
    # Tagline
    styles.add(ParagraphStyle(
        name='Tagline',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=14,
        textColor=AUTUMN_DARK,
        alignment=TA_CENTER,
        spaceAfter=20
    ))
    
    return styles

def generate_family_album_pdf():
    """Generate magazine-style family album PDF."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"family_album_{timestamp}.pdf"
        
        # Get data from database
        db = get_db()
        cursor = db.cursor()
        
        # Get memories grouped by year
        cursor.execute("""
            SELECT id, text, category, memory_date, year, created_at 
            FROM memories 
            ORDER BY year DESC, created_at DESC
        """)
        memories = cursor.fetchall()
        
        # Get all media
        cursor.execute("""
            SELECT id, filename, original_filename, file_type, title, description, 
                   memory_date, year, created_at 
            FROM media 
            WHERE file_type = 'image'
            ORDER BY created_at DESC
        """)
        media_items = cursor.fetchall()
        
        # Create document with custom page template
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        styles = create_custom_styles()
        
        # ==================== TITLE PAGE ====================
        story.append(Spacer(1, 2.5*inch))
        story.append(Paragraph("The Circle", styles['MagazineTitle']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("Family Memory Album", styles['Tagline']))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            f"Created {datetime.now().strftime('%B %d, %Y')}", 
            styles['PhotoCaption']
        ))
        story.append(PageBreak())
        
        # ==================== MEMORIES BY DECADE ====================
        if memories:
            # Group by decade
            decades = {}
            for memory in memories:
                memory_id, text, category, memory_date, year, created_at = memory
                if year:
                    decade = (int(year) // 10) * 10
                    if decade not in decades:
                        decades[decade] = []
                    decades[decade].append(memory)
            
            # Process each decade
            for decade in sorted(decades.keys(), reverse=True):
                decade_memories = decades[decade]
                
                # Decade header
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph(f"{decade}s", styles['DecadeHeader']))
                story.append(Spacer(1, 0.2*inch))
                
                # Process each memory in decade
                for memory in decade_memories:
                    memory_id, text, category, memory_date, year, created_at = memory
                    
                    # Story header
                    date_str = memory_date if memory_date else f"{year}"
                    header = f"<b>{date_str}</b>"
                    if category:
                        header += f" - <i>{category}</i>"
                    
                    story.append(Paragraph(header, styles['StoryTitle']))
                    
                    # Get explicitly linked images (replaces automatic matching)
                    related_images = get_linked_media(memory_id)
                    
                    # Split text into paragraphs
                    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                    
                    # Extract pull quote from entire text if long enough
                    pull_quote_text = None
                    if len(text) > 200:
                        pull_quote_text = extract_pull_quote(text)
                    
                    # Create story content
                    story_content = []
                    
                    # Add first paragraph
                    if paragraphs:
                        story_content.append(Paragraph(paragraphs[0], styles['MagazineBody']))
                    
                    # Add pull quote after first paragraph if we have one
                    if pull_quote_text and len(paragraphs) > 1:
                        story_content.append(Spacer(1, 0.15*inch))
                        
                        # Create pull quote table for better positioning
                        pull_quote_para = Paragraph(
                            f'<i>"{pull_quote_text}"</i>',
                            ParagraphStyle(
                                'PullQuoteStyle',
                                parent=styles['MagazineBody'],
                                fontSize=13,
                                textColor=AUTUMN_DARK,
                                alignment=TA_CENTER,
                                fontName='Times-Italic',
                                leftIndent=40,
                                rightIndent=40,
                                spaceBefore=8,
                                spaceAfter=8
                            )
                        )
                        
                        # Create decorative table
                        pull_quote_table = Table(
                            [[pull_quote_para]], 
                            colWidths=[5*inch]
                        )
                        pull_quote_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), BACKGROUND_CREAM),
                            ('LEFTPADDING', (0, 0), (-1, -1), 20),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                            ('TOPPADDING', (0, 0), (-1, -1), 12),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                            ('LINEABOVE', (0, 0), (-1, 0), 3, AUTUMN_GOLD),
                            ('LINEBELOW', (0, 0), (-1, -1), 3, AUTUMN_GOLD),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ]))
                        
                        story_content.append(pull_quote_table)
                        story_content.append(Spacer(1, 0.15*inch))
                    
                    # Add first image if available
                    if related_images:
                        img_path = os.path.join('uploads', related_images[0][1])
                        if os.path.exists(img_path):
                            try:
                                # Get image dimensions and preserve aspect ratio
                                from PIL import Image as PILImage
                                pil_img = PILImage.open(img_path)
                                img_width, img_height = pil_img.size
                                aspect_ratio = img_height / img_width
                                
                                # Set max width and calculate height
                                max_width = 3*inch
                                target_height = max_width * aspect_ratio
                                
                                # If too tall, constrain by height instead
                                if target_height > 3*inch:
                                    target_height = 3*inch
                                    max_width = target_height / aspect_ratio
                                
                                img = Image(img_path, width=max_width, height=target_height)
                                img.hAlign = 'CENTER'
                                story_content.append(Spacer(1, 0.1*inch))
                                story_content.append(img)
                                
                                # Caption
                                caption_text = related_images[0][4] or related_images[0][2]
                                if related_images[0][5]:  # description
                                    caption_text += f" - {related_images[0][5]}"
                                story_content.append(Paragraph(caption_text, styles['PhotoCaption']))
                                story_content.append(Spacer(1, 0.1*inch))
                            except Exception as e:
                                print(f"Could not load image: {e}")
                    
                    # Add remaining paragraphs
                    for para in paragraphs[1:]:
                        story_content.append(Paragraph(para, styles['MagazineBody']))
                    
                    # Add second image if available
                    if len(related_images) > 1:
                        img_path = os.path.join('uploads', related_images[1][1])
                        if os.path.exists(img_path):
                            try:
                                # Get image dimensions and preserve aspect ratio
                                from PIL import Image as PILImage
                                pil_img = PILImage.open(img_path)
                                img_width, img_height = pil_img.size
                                aspect_ratio = img_height / img_width
                                
                                # Set max width and calculate height
                                max_width = 2.5*inch
                                target_height = max_width * aspect_ratio
                                
                                # If too tall, constrain by height instead
                                if target_height > 2.5*inch:
                                    target_height = 2.5*inch
                                    max_width = target_height / aspect_ratio
                                
                                img = Image(img_path, width=max_width, height=target_height)
                                img.hAlign = 'RIGHT'
                                story_content.append(Spacer(1, 0.1*inch))
                                story_content.append(img)
                                
                                caption_text = related_images[1][4] or related_images[1][2]
                                story_content.append(Paragraph(caption_text, styles['PhotoCaption']))
                            except Exception as e:
                                print(f"Could not load image: {e}")
                    
                    # Add all story content
                    story.extend(story_content)
                    story.append(Spacer(1, 0.3*inch))
                
                # Page break between decades
                story.append(PageBreak())
        
        # ==================== PHOTO GALLERY ====================
        # Add remaining unmatched photos
        story.append(Paragraph("Photo Gallery", styles['MagazineTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # Create 2-column grid
        grid_data = []
        row = []
        
        for media in media_items[:20]:  # Limit to 20 photos in gallery
            media_id, filename, original, file_type, title, desc, mdate, year, created = media
            img_path = os.path.join('uploads', filename)
            
            if os.path.exists(img_path):
                try:
                    # Get image dimensions and preserve aspect ratio
                    from PIL import Image as PILImage
                    pil_img = PILImage.open(img_path)
                    img_width, img_height = pil_img.size
                    aspect_ratio = img_height / img_width
                    
                    # Set max dimensions for gallery grid
                    max_width = 2.75*inch
                    target_height = max_width * aspect_ratio
                    
                    # If too tall, constrain by height
                    max_height = 2.5*inch
                    if target_height > max_height:
                        target_height = max_height
                        max_width = target_height / aspect_ratio
                    
                    img = Image(img_path, width=max_width, height=target_height)
                    
                    # Caption
                    caption_text = f"<b>{title or original}</b>"
                    if desc:
                        caption_text += f"<br/>{desc}"
                    caption = Paragraph(caption_text, styles['PhotoCaption'])
                    
                    cell_content = [img, caption]
                    row.append(cell_content)
                    
                    if len(row) == 2:
                        grid_data.append(row)
                        row = []
                except Exception as e:
                    print(f"Could not load gallery image: {e}")
        
        # Add final row if not complete
        if row:
            # Pad with empty cell if odd number
            if len(row) == 1:
                row.append([Paragraph('', styles['PhotoCaption'])])
            grid_data.append(row)
        
        if grid_data:
            table = Table(grid_data, colWidths=[3.25*inch, 3.25*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(table)
        
        # Build PDF
        doc.build(story)
        print(f"✓ Magazine-style PDF generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"✗ PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_memory_pdf(pdf_type="all"):
    """Backward compatibility wrapper."""
    return generate_family_album_pdf()

def generate_simple_pdf():
    """Fallback simple PDF."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"family_album_simple_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Paragraph("Family Memory Album", styles['Heading1']))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        
        doc.build(story)
        return output_path
    except Exception as e:
        print(f"✗ Simple PDF failed: {e}")
        return None
