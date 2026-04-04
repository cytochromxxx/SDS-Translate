import sys
import os
import shutil
from flask import Flask

# Add the current directory to sys.path so we can import app and its routes
sys.path.append(os.path.abspath('.'))

from routes.main import export_translated_pdf

app = Flask(__name__)
# Mock the current_app and context
with app.app_context():
    # Load the template content
    template_path = 'layout-placeholders-fixed-v2.html'
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Call the export function
    print("Generating PDF...")
    try:
        response = export_translated_pdf(html_content, 'de', 'Deutsch')
        
        # Save the resulting PDF bytes
        pdf_bytes = response.get_data()
        output_path = os.path.abspath('uploads/verification_output.pdf')
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
            
        print(f"PDF successfully generated at: {output_path}")
        print(f"Size: {len(pdf_bytes)} bytes")
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
