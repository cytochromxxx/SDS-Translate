#!/usr/bin/env python3
"""
SDS Translator Web Application
Flask-based web UI for translating Safety Data Sheets
"""

import os
import tempfile
from flask import Flask
import logging
from database import set_db_path, get_db_path, DATABASE_OPTIONS, DEFAULT_DB_PATH
from utils import AVAILABLE_LANGUAGES, LANG_TO_COLUMN, parse_flag_format

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add msys2 GTK path to system PATH for WeasyPrint
msys2_path = r'C:\msys64\mingw64\bin'
os.environ['PATH'] = msys2_path + os.pathsep + os.environ.get('PATH', '')

# Tell cffi where to find the GTK libraries
os.environ['GI_TYPELIB_PATH'] = r'C:\msys64\mingw64\lib\girepository-1.0'
os.environ['GTK_EXE_PREFIX'] = r'C:\msys64\mingw64'
os.environ['GTK_PATH'] = r'C:\msys64\mingw64'

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'sds-translator-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# --- Import checks ---
try:
    from weasyprint import HTML, CSS
    app.config['WEASYPRINT_AVAILABLE'] = True
except (ImportError, OSError) as e:
    print(f"WeasyPrint not available: {e}. PDF export will be disabled.")
    app.config['WEASYPRINT_AVAILABLE'] = False

try:
    from sds_xml_importer import import_sds_to_html
    app.config['SDSCOM_PARSER_AVAILABLE'] = True
except ImportError as e:
    print(f"Could not import the sdscom_parser or sds_xml_importer: {e}")
    app.config['SDSCOM_PARSER_AVAILABLE'] = False

try:
    from pdf_importer import PDFImporter, PDFImportConfig, PDFImportError, check_dependencies
    app.config['PDF_IMPORT_AVAILABLE'] = True
except ImportError:
    app.config['PDF_IMPORT_AVAILABLE'] = False
    print("PDF import module not available")

try:
    from sds_template_importer import SDSTemplateImporter, import_sds_to_template
    app.config['SDS_TEMPLATE_IMPORT_AVAILABLE'] = True
except ImportError:
    app.config['SDS_TEMPLATE_IMPORT_AVAILABLE'] = False
    print("SDS Template import module not available")
    
try:
    from sds_parser import parse_sds_pdf
    app.config['SDS_PARSER_V5_AVAILABLE'] = True
except ImportError:
    app.config['SDS_PARSER_V5_AVAILABLE'] = False
    print("SDS Parser v5 not available")


# --- Register Blueprints ---
from routes.main import main_bp
from routes.database import database_bp
from routes.pdf import pdf_bp
from routes.ghs import ghs_bp

app.register_blueprint(main_bp)
app.register_blueprint(database_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(ghs_bp)

# --- Logo Route ---
@app.route('/mb_logo.svg')
def serve_logo():
    from flask import send_file
    if os.path.exists('mb_logo.svg'):
        return send_file('mb_logo.svg', mimetype='image/svg+xml')
    return "Logo not found", 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
