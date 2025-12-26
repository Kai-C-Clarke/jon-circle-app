#!/usr/bin/env python3
"""
Test Biography PDF Generator
Quick test to verify PDF generation works
"""

import sys
import os

print("\n" + "="*70)
print("TESTING BIOGRAPHY PDF GENERATOR")
print("="*70 + "\n")

# Check if file exists
if not os.path.exists('biography_pdf_generator.py'):
    print("❌ ERROR: biography_pdf_generator.py not found in current directory")
    print(f"   Current directory: {os.getcwd()}")
    print("\n   Make sure you're running from: /Users/jonstiles/Desktop/Jon_Circle")
    sys.exit(1)

print("✓ biography_pdf_generator.py found")

# Test imports
print("\nTesting imports...")
try:
    from reportlab.lib.pagesizes import A4
    print("  ✓ reportlab")
except ImportError as e:
    print(f"  ❌ reportlab not installed: {e}")
    print("\n  Install with: pip3 install reportlab --break-system-packages")
    sys.exit(1)

try:
    from PIL import Image
    print("  ✓ Pillow (PIL)")
except ImportError as e:
    print(f"  ❌ Pillow not installed: {e}")
    print("\n  Install with: pip3 install Pillow --break-system-packages")
    sys.exit(1)

# Test loading the module
print("\nLoading biography_pdf_generator module...")
try:
    from biography_pdf_generator import generate_biography_pdf
    print("  ✓ Module loaded successfully")
except Exception as e:
    print(f"  ❌ Error loading module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test generating a simple PDF
print("\nTesting PDF generation with sample data...")
try:
    sample_chapters = [
        {
            'title': 'Chapter 1: Test Chapter',
            'narrative': 'This is a test chapter to verify the PDF generator works properly. It should create a simple PDF with this text.'
        },
        {
            'title': 'Chapter 2: Second Test',
            'narrative': 'Another test chapter to ensure multiple chapters work correctly.'
        }
    ]
    
    print("  Creating sample biography PDF...")
    pdf_buffer = generate_biography_pdf(
        chapters=sample_chapters,
        title="Test Biography",
        subtitle="Testing PDF Generation",
        upload_folder="uploads",
        hero_photo=None
    )
    
    pdf_size = len(pdf_buffer.getvalue())
    print(f"  ✅ PDF generated successfully! ({pdf_size:,} bytes)")
    
    # Save to test file
    with open("test_biography_output.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    print(f"\n  ✓ Test PDF saved as: test_biography_output.pdf")
    print(f"  ✓ You can open it to verify it looks correct")
    
except Exception as e:
    print(f"  ❌ Error generating PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅ PDF GENERATOR IS WORKING CORRECTLY!")
print("="*70)
print("\nThe issue must be elsewhere. Next steps:")
print("1. Check Flask terminal for errors when clicking 'Download PDF'")
print("2. Check browser console (F12) for JavaScript errors")
print("3. Verify app.py has the correct PDF route (around line 954)")
print("="*70 + "\n")
