#!/usr/bin/env python3
"""
Biography PDF Generator
Creates magazine-style PDFs from AI-generated biographies with integrated photos
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, PageTemplate, Frame, NextPageTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from io import BytesIO
from PIL import Image as PILImage
import os
import re
import sqlite3
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Autumn color palette
AUTUMN_GOLD = HexColor('#e8b44f')
AUTUMN_BURGUNDY = HexColor('#8B4513')
AUTUMN_CREAM = HexColor('#F5F5DC')
DARK_TEXT = HexColor('#2c3e50')
LIGHT_TEXT = HexColor('#666666')
PAGE_NUMBER_COLOR = HexColor('#888888')

# Default configuration
DEFAULT_CONFIG = {
    'max_photos_per_chapter': 3,
    'default_image_width': 5 * inch,
    'default_image_height': 3.5 * inch,
    'hero_image_width': 6 * inch,
    'hero_image_height': 4 * inch,
    'small_image_width': 4 * inch,
    'small_image_height': 3 * inch,
    'page_margins': (1 * inch, 1 * inch, 1 * inch, 1 * inch),  # left, right, top, bottom
    'font_name': 'Helvetica',
    'font_bold': 'Helvetica-Bold',
    'font_italic': 'Helvetica-Oblique',
    'family_names': [],  # Should be populated from application context
    'location_keywords': ['home', 'school', 'work', 'vacation', 'wedding', 'church'],
    'event_keywords': ['birthday', 'graduation', 'wedding', 'holiday', 'anniversary', 'trip']
}

class BiographyPDFGenerator:
    """Main generator class for creating biography PDFs."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the PDF generator with configuration."""
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Initialize styles
        self.styles = self._create_styles()
        
        # Track temporary files for cleanup
        self.temp_files = []
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create and return paragraph styles."""
        sample_styles = getSampleStyleSheet()
        
        styles = {}
        
        # Cover title style
        styles['cover_title'] = ParagraphStyle(
            'CoverTitle',
            parent=sample_styles['Title'],
            fontSize=36,
            textColor=AUTUMN_BURGUNDY,
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=42,
            fontName=self.config['font_bold']
        )
        
        # Cover subtitle style
        styles['cover_subtitle'] = ParagraphStyle(
            'CoverSubtitle',
            parent=sample_styles['Normal'],
            fontSize=18,
            textColor=AUTUMN_GOLD,
            alignment=TA_CENTER,
            fontName=self.config['font_italic']
        )
        
        # Chapter title style
        styles['chapter_title'] = ParagraphStyle(
            'ChapterTitle',
            parent=sample_styles['Heading1'],
            fontSize=24,
            textColor=AUTUMN_GOLD,
            spaceAfter=20,
            spaceBefore=20,
            fontName=self.config['font_bold']
        )
        
        # Chapter body style
        styles['chapter_body'] = ParagraphStyle(
            'ChapterBody',
            parent=sample_styles['Normal'],
            fontSize=11,
            textColor=DARK_TEXT,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=16,
            fontName=self.config['font_name']
        )
        
        # Photo caption style
        styles['photo_caption'] = ParagraphStyle(
            'PhotoCaption',
            parent=sample_styles['Normal'],
            fontSize=9,
            textColor=LIGHT_TEXT,
            alignment=TA_CENTER,
            fontName=self.config['font_italic'],
            spaceAfter=12
        )
        
        # Table of contents style
        styles['toc_title'] = ParagraphStyle(
            'TOCTitle',
            parent=sample_styles['Heading1'],
            fontSize=20,
            textColor=AUTUMN_BURGUNDY,
            spaceAfter=20,
            fontName=self.config['font_bold']
        )
        
        # TOC chapter style
        styles['toc_chapter'] = ParagraphStyle(
            'TOCChapter',
            parent=sample_styles['Normal'],
            fontSize=12,
            textColor=DARK_TEXT,
            leftIndent=20,
            spaceAfter=8,
            fontName=self.config['font_name']
        )
        
        # Header style
        styles['header'] = ParagraphStyle(
            'Header',
            parent=sample_styles['Normal'],
            fontSize=10,
            textColor=LIGHT_TEXT,
            alignment=TA_CENTER,
            fontName=self.config['font_name']
        )
        
        return styles
    
    def _get_safe_photo_path(self, upload_folder: str, filename: str) -> Optional[str]:
        """Get safe photo path preventing directory traversal."""
        try:
            # Remove any directory components and normalize
            safe_filename = os.path.basename(filename)
            
            # Remove any null bytes or control characters
            safe_filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', safe_filename)
            
            full_path = os.path.join(upload_folder, safe_filename)
            
            # Ensure the path stays within upload folder
            upload_folder_abs = os.path.abspath(upload_folder)
            full_path_abs = os.path.abspath(full_path)
            
            if not full_path_abs.startswith(upload_folder_abs):
                logger.warning(f"Path traversal attempt detected: {filename}")
                return None
            
            # Check if file exists and is readable
            if not os.path.exists(full_path_abs):
                logger.warning(f"Photo file not found: {full_path_abs}")
                return None
            
            if not os.access(full_path_abs, os.R_OK):
                logger.warning(f"Photo file not readable: {full_path_abs}")
                return None
            
            return full_path_abs
            
        except Exception as e:
            logger.error(f"Error getting safe photo path for {filename}: {e}")
            return None
    
    def _safe_load_and_resize_image(self, image_path: str, max_width: float, max_height: float) -> Optional[Image]:
        """Safely load and resize image for PDF with aspect ratio preservation."""
        try:
            if not image_path or not os.path.exists(image_path):
                logger.warning(f"Image path does not exist: {image_path}")
                return None
            
            # Open with PIL to check and resize
            with PILImage.open(image_path) as pil_img:
                # Convert to RGB if necessary
                if pil_img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = PILImage.new('RGB', pil_img.size, (255, 255, 255))
                    if pil_img.mode == 'P':
                        pil_img = pil_img.convert('RGBA')
                    rgb_img.paste(pil_img, mask=pil_img.split()[-1] if pil_img.mode == 'RGBA' else None)
                    pil_img = rgb_img
                
                # Calculate aspect ratio preserving dimensions
                img_width, img_height = pil_img.size
                
                if img_width == 0 or img_height == 0:
                    logger.warning(f"Invalid image dimensions for {image_path}: {img_width}x{img_height}")
                    return None
                
                # Calculate scaling factor
                width_ratio = max_width / img_width
                height_ratio = max_height / img_height
                scale_factor = min(width_ratio, height_ratio)
                
                # Don't upscale small images
                if scale_factor > 1:
                    scale_factor = 1
                
                new_width = img_width * scale_factor
                new_height = img_height * scale_factor
                
                # Resize image
                resized_img = pil_img.resize((int(new_width), int(new_height)), PILImage.Resampling.LANCZOS)
                
                # Save to temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                resized_img.save(temp_path, 'JPEG', quality=85)
                self.temp_files.append(temp_path)
                
                # Create ReportLab Image
                return Image(temp_path, width=new_width, height=new_height)
                
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None
    
    def _create_header_footer(self, canvas: Canvas, doc: SimpleDocTemplate, title: str):
        """Add header and footer to each page."""
        # Save current state
        canvas.saveState()
        
        # Header
        header_text = title
        canvas.setFont(self.config['font_name'], 10)
        canvas.setFillColor(LIGHT_TEXT)
        canvas.drawCentredString(doc.width / 2 + doc.leftMargin, doc.height + doc.topMargin - 0.5 * inch, header_text)
        
        # Footer with page number
        page_num = canvas.getPageNumber()
        footer_text = f"Page {page_num}"
        canvas.setFont(self.config['font_name'], 9)
        canvas.setFillColor(PAGE_NUMBER_COLOR)
        canvas.drawRightString(doc.width + doc.leftMargin, 0.75 * inch, footer_text)
        
        # Restore state
        canvas.restoreState()
    
    def _create_cover_page(self, title: str, subtitle: str, hero_photo_path: Optional[str] = None) -> List[Any]:
        """Create magazine-style cover page."""
        elements = []
        
        # Add hero photo if available
        if hero_photo_path:
            safe_hero_path = self._get_safe_photo_path(os.path.dirname(hero_photo_path), os.path.basename(hero_photo_path))
            if safe_hero_path:
                hero_img = self._safe_load_and_resize_image(
                    safe_hero_path,
                    self.config['hero_image_width'],
                    self.config['hero_image_height']
                )
                if hero_img:
                    elements.append(hero_img)
                    elements.append(Spacer(1, 0.3 * inch))
        
        # If no hero photo, add some space
        if not elements or not hero_photo_path:
            elements.append(Spacer(1, 2 * inch))
        
        # Title
        elements.append(Paragraph(title, self.styles['cover_title']))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Subtitle
        elements.append(Paragraph(subtitle, self.styles['cover_subtitle']))
        elements.append(Spacer(1, 1 * inch))
        
        # Decorative line
        line_table = Table([['']], colWidths=[4 * inch])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, AUTUMN_GOLD),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Generation date
        date_text = f"Generated on {datetime.now().strftime('%B %d, %Y')}"
        date_style = ParagraphStyle(
            'DateStyle',
            parent=getSampleStyleSheet()['Normal'],
            fontSize=10,
            textColor=LIGHT_TEXT,
            alignment=TA_CENTER,
            fontName=self.config['font_italic']
        )
        elements.append(Paragraph(date_text, date_style))
        
        elements.append(PageBreak())
        
        return elements
    
    def _create_table_of_contents(self, chapters: List[Dict[str, Any]]) -> List[Any]:
        """Generate table of contents."""
        elements = []
        
        elements.append(Paragraph("Table of Contents", self.styles['toc_title']))
        elements.append(Spacer(1, 0.3 * inch))
        
        for i, chapter in enumerate(chapters, 1):
            # Truncate long chapter titles
            chapter_title = chapter['title']
            if len(chapter_title) > 60:
                chapter_title = chapter_title[:57] + "..."
            
            elements.append(Paragraph(f"{i}. {chapter_title}", self.styles['toc_chapter']))
        
        elements.append(PageBreak())
        return elements
    
    def _match_photos_to_chapter(self, chapter_title: str, chapter_text: str, 
                                 available_photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match photos to chapter based on content, years, and keywords."""
        matched_photos = []
        chapter_content = (chapter_title + ' ' + chapter_text).lower()
        
        # Extract year range from chapter title
        year_match = re.search(r'\((\d{4})\s*[-–]\s*(\d{4})\)', chapter_title)
        if year_match:
            start_year = int(year_match.group(1))
            end_year = int(year_match.group(2))
            
            # Find photos within year range
            for photo in available_photos:
                if photo in matched_photos:
                    continue
                    
                if photo.get('year'):
                    try:
                        photo_year = int(photo['year'])
                        if start_year <= photo_year <= end_year:
                            matched_photos.append(photo)
                            continue  # Don't check this photo again
                    except (ValueError, TypeError):
                        pass
        
        # Score-based matching for remaining photos
        photo_scores = []
        
        for photo in available_photos:
            if photo in matched_photos:
                continue
                
            score = 0
            photo_title = photo.get('title', '').lower()
            photo_desc = photo.get('description', '').lower()
            photo_content = photo_title + ' ' + photo_desc
            
            # Check for family name mentions
            for name in self.config['family_names']:
                name_lower = name.lower()
                if name_lower in chapter_content and name_lower in photo_content:
                    score += 10
            
            # Check for location keywords
            for keyword in self.config['location_keywords']:
                if keyword in chapter_content and keyword in photo_content:
                    score += 5
            
            # Check for event keywords
            for keyword in self.config['event_keywords']:
                if keyword in chapter_content and keyword in photo_content:
                    score += 5
            
            # Check for exact year mentions
            if photo.get('year'):
                photo_year = str(photo['year'])
                if photo_year in chapter_content:
                    score += 8
            
            if score > 0:
                photo_scores.append((score, photo))
        
        # Sort by score and add top matches
        photo_scores.sort(key=lambda x: x[0], reverse=True)
        for score, photo in photo_scores[:self.config['max_photos_per_chapter'] - len(matched_photos)]:
            matched_photos.append(photo)
        
        return matched_photos[:self.config['max_photos_per_chapter']]
    
    def _create_chapter_content(self, chapter: Dict[str, Any], photos: List[Dict[str, Any]], 
                                upload_folder: str) -> List[Any]:
        """Create formatted chapter with integrated photos."""
        elements = []
        
        # Chapter title
        elements.append(Paragraph(chapter['title'], self.styles['chapter_title']))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Split narrative into paragraphs
        paragraphs = [p.strip() for p in chapter['narrative'].split('\n\n') if p.strip()]
        
        if not paragraphs:
            logger.warning(f"Chapter '{chapter['title']}' has no content")
            return elements
        
        # Add first paragraph
        elements.append(Paragraph(paragraphs[0], self.styles['chapter_body']))
        
        # Insert first photo after first paragraph if available
        if photos:
            first_photo = photos[0]
            photo_path = self._get_safe_photo_path(upload_folder, first_photo['filename'])
            
            if photo_path:
                photo_img = self._safe_load_and_resize_image(
                    photo_path,
                    self.config['default_image_width'],
                    self.config['default_image_height']
                )
                
                if photo_img:
                    elements.append(Spacer(1, 0.2 * inch))
                    elements.append(photo_img)
                    
                    # Photo caption
                    caption = first_photo.get('title', os.path.splitext(first_photo['filename'])[0])
                    if first_photo.get('year'):
                        caption += f" ({first_photo['year']})"
                    
                    elements.append(Paragraph(caption, self.styles['photo_caption']))
                    elements.append(Spacer(1, 0.2 * inch))
        
        # Add remaining paragraphs
        for para in paragraphs[1:]:
            elements.append(Paragraph(para, self.styles['chapter_body']))
        
        # Add remaining photos at the end
        for photo in photos[1:]:
            photo_path = self._get_safe_photo_path(upload_folder, photo['filename'])
            
            if photo_path:
                photo_img = self._safe_load_and_resize_image(
                    photo_path,
                    self.config['small_image_width'],
                    self.config['small_image_height']
                )
                
                if photo_img:
                    elements.append(Spacer(1, 0.3 * inch))
                    elements.append(photo_img)
                    
                    # Photo caption
                    caption = photo.get('title', os.path.splitext(photo['filename'])[0])
                    if photo.get('year'):
                        caption += f" ({photo['year']})"
                    
                    elements.append(Paragraph(caption, self.styles['photo_caption']))
        
        elements.append(PageBreak())
        return elements
    
    def generate_biography_pdf(self, chapters: List[Dict[str, Any]], title: str, subtitle: str, 
                               upload_folder: str, db_connection: Optional[sqlite3.Connection] = None,
                               hero_photo: Optional[str] = None, family_names: Optional[List[str]] = None) -> BytesIO:
        """Generate complete biography PDF with cover, TOC, and photos."""
        
        # Update family names in config
        if family_names:
            self.config['family_names'] = family_names
        
        # Validate input
        if not chapters:
            raise ValueError("No chapters provided for PDF generation")
        
        if not os.path.exists(upload_folder):
            raise ValueError(f"Upload folder does not exist: {upload_folder}")
        
        # Create buffer for PDF
        buffer = BytesIO()
        
        try:
            # Get available photos from database
            available_photos = []
            
            if db_connection:
                try:
                    cursor = db_connection.execute('''
                        SELECT id, filename, title, description, year, people
                        FROM media
                        WHERE file_type = 'image'
                        ORDER BY year DESC NULLS LAST, created_at DESC
                    ''')
                    
                    for row in cursor.fetchall():
                        available_photos.append({
                            'id': row[0],
                            'filename': row[1] or '',
                            'title': row[2] or '',
                            'description': row[3] or '',
                            'year': row[4],
                            'people': row[5] or ''
                        })
                    
                    logger.info(f"Loaded {len(available_photos)} photos from database")
                    
                except Exception as e:
                    logger.error(f"Error loading photos from database: {e}")
                    # Continue without photos rather than failing completely
            
            # Create PDF document with header/footer support
            left_margin, right_margin, top_margin, bottom_margin = self.config['page_margins']
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=right_margin,
                leftMargin=left_margin,
                topMargin=top_margin + 0.5 * inch,  # Extra space for header
                bottomMargin=bottom_margin + 0.5 * inch  # Extra space for footer
            )
            
            # Build story elements
            story = []
            
            # Create cover page
            hero_photo_path = None
            if hero_photo:
                hero_photo_path = self._get_safe_photo_path(upload_folder, hero_photo)
            
            cover_elements = self._create_cover_page(title, subtitle, hero_photo_path)
            story.extend(cover_elements)
            
            # Create table of contents
            toc_elements = self._create_table_of_contents(chapters)
            story.extend(toc_elements)
            
            # Create chapters with photos
            for i, chapter in enumerate(chapters, 1):
                logger.info(f"Processing chapter {i}: {chapter['title'][:50]}...")
                
                # Match photos to this chapter
                chapter_photos = self._match_photos_to_chapter(
                    chapter['title'],
                    chapter['narrative'],
                    available_photos
                )
                
                if chapter_photos:
                    logger.info(f"  Matched {len(chapter_photos)} photos to chapter")
                
                # Create chapter content
                chapter_elements = self._create_chapter_content(
                    chapter,
                    chapter_photos,
                    upload_folder
                )
                
                story.extend(chapter_elements)
            
            # Build PDF with header/footer
            def add_header_footer(canvas, doc):
                self._create_header_footer(canvas, doc, title)
            
            doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
            
            # Reset buffer position
            buffer.seek(0)
            
            logger.info(f"Successfully generated PDF with {len(chapters)} chapters")
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
        finally:
            # Clean up temporary files
            self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Clean up temporary files created during PDF generation."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")
        
        self.temp_files.clear()


# Legacy function for backward compatibility
def generate_biography_pdf(chapters: List[Dict[str, Any]], title: str, subtitle: str, 
                          upload_folder: str, hero_photo: Optional[str] = None) -> BytesIO:
    """Legacy function for backward compatibility."""
    
    # Try to get database connection from app context
    db_connection = None
    try:
        # This would need to be adapted based on your application structure
        # For now, create a new connection
        db_path = os.getenv('DATABASE_PATH', 'circle_memories.db')
        if os.path.exists(db_path):
            db_connection = sqlite3.connect(db_path)
    except Exception as e:
        logger.warning(f"Could not connect to database: {e}")
    
    # Create generator instance
    generator = BiographyPDFGenerator()
    
    try:
        # Try to extract family names from chapters
        family_names = []
        for chapter in chapters:
            # Simple extraction - look for common name patterns
            text = chapter['title'] + ' ' + chapter['narrative']
            # This is a simple heuristic - in production, you'd want a better method
            name_matches = re.findall(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', text)
            family_names.extend(name_matches[:2])  # Take first 2 names as family
        
        # Remove duplicates
        family_names = list(set(family_names))[:5]  # Max 5 unique names
        
        return generator.generate_biography_pdf(
            chapters=chapters,
            title=title,
            subtitle=subtitle,
            upload_folder=upload_folder,
            db_connection=db_connection,
            hero_photo=hero_photo,
            family_names=family_names
        )
    finally:
        if db_connection:
            db_connection.close()


# Example usage
if __name__ == "__main__":
    # Example chapters (for testing)
    example_chapters = [
        {
            'title': 'Chapter 1: Early Years (1950-1960)',
            'narrative': '''John was born in a small town in 1950. His early years were marked by...'''
        },
        {
            'title': 'Chapter 2: College Years (1968-1972)',
            'narrative': '''John attended State University where he met his future wife, Mary...'''
        }
    ]
    
    # Generate example PDF
    try:
        pdf_buffer = generate_biography_pdf(
            chapters=example_chapters,
            title="The Life of John",
            subtitle="A Family Memoir",
            upload_folder="./uploads",
            hero_photo=None
        )
        
        # Save to file for testing
        with open("test_biography.pdf", "wb") as f:
            f.write(pdf_buffer.read())
        
        print("Test PDF generated successfully: test_biography.pdf")
        
    except Exception as e:
        print(f"Error generating test PDF: {e}")