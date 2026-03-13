#!/usr/bin/env python3
"""
SDS Translator Web Application
Flask-based web UI for translating Safety Data Sheets
"""

import os
import sqlite3
import tempfile
import threading
import uuid
import shutil
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, session
from werkzeug.utils import secure_filename
import sys
import os
from pathlib import Path
import logging

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

import json
from sds_translator_v4 import SDSTranslator
# WeasyPrint Import - Optional for PDF export
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"WeasyPrint not available: {e}. PDF export will be disabled.")
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    FontConfiguration = None
import base64
from io import BytesIO
import re

# --- NEW PARSER IMPORTS ---

try:
    from sds_xml_importer import import_sds_to_html
    SDSCOM_PARSER_AVAILABLE = True
except ImportError as e:
    print(f"Could not import the sdscom_parser or sds_xml_importer: {e}")
    SDSCOM_PARSER_AVAILABLE = False
# --- END NEW PARSER IMPORT ---


# Thread-safe database configuration
_db_lock = threading.Lock()
_current_db_path = "phrases_library.db"

# Database configuration options
DATABASE_OPTIONS = {
    'legacy': {
        'path': 'phrases_library.db',
        'name': 'Legacy Database (Default)',
        'description': 'Bisherige Standard-Datenbank mit allen Phrasen'
    },
    'euphrac_excel': {
        'path': 'euphrac_excel_phrases.db',
        'name': 'EUH Excel Phrases',
        'description': 'EUH-Präfix-Phrasen aus Excel-Importen'
    },
    'sds_only': {
        'path': 'phrases_from_sds_only.db',
        'name': 'SDS-Only Phrases',
        'description': 'Rein aus bestehenden SDS-Dokumenten extrahiert'
    },
    'verified': {
        'path': 'phrases_library_verified.db',
        'name': 'Verified Phrases',
        'description': 'Menschlich verifizierte und freigegebene Phrasen'
    },
    'extracted': {
        'path': 'sds_phrases_extracted.db',
        'name': 'Extracted Raw Phrases',
        'description': 'Automatisch extrahierte Rohphrasen aus SDS-Parsing'
    }
}

# Try to import optional PDF libraries
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint not available (missing GTK libraries), PDF generation will be limited")

# Import PDF Importer Module
try:
    from pdf_importer import PDFImporter, PDFImportConfig, PDFImportError, check_dependencies
    PDF_IMPORT_AVAILABLE = True
except ImportError:
    PDF_IMPORT_AVAILABLE = False
    print("PDF import module not available")

# Import SDS Template Importer (uses layout-gemini-fixed.html)
try:
    from sds_template_importer import SDSTemplateImporter, import_sds_to_template
    SDS_TEMPLATE_IMPORT_AVAILABLE = True
except ImportError:
    SDS_TEMPLATE_IMPORT_AVAILABLE = False
    print("SDS Template import module not available")

# PDF Import Configuration
PDF_IMPORT_CONFIG = {
    'max_file_size': 50 * 1024 * 1024,  # 50MB max
    'min_file_size': 100,  # 100 bytes min
    'supported_versions': ('1.4', '1.5', '1.6', '1.7', '2.0'),
    'max_pages': 500
}

app = Flask(__name__)
app.secret_key = 'sds-translator-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = tempfile.gettempdir()

# Default database path (legacy)
DEFAULT_DB_PATH = "phrases_library.db"

# Thread-safe database path getter/setter
def get_db_path():
    """Get current database path thread-safely."""
    with _db_lock:
        return _current_db_path

def set_db_path(db_key):
    """Set database path thread-safely with fallback."""
    global _current_db_path
    with _db_lock:
        if db_key in DATABASE_OPTIONS:
            new_path = DATABASE_OPTIONS[db_key]['path']
            if os.path.exists(new_path):
                _current_db_path = new_path
                return True, f"Database switched to: {DATABASE_OPTIONS[db_key]['name']}"
            else:
                # Fallback to default if selected database doesn't exist
                if os.path.exists(DEFAULT_DB_PATH):
                    _current_db_path = DEFAULT_DB_PATH
                    return False, f"Database '{new_path}' not found, fallback to Legacy Database"
                else:
                    return False, f"Database '{new_path}' not found and no fallback available"
        return False, "Invalid database key"

def get_available_databases():
    """Get list of available databases with existence check."""
    available = {}
    for key, config in DATABASE_OPTIONS.items():
        available[key] = {
            **config,
            'exists': os.path.exists(config['path']),
            'active': get_db_path() == config['path']
        }
    return available

# For backward compatibility
DB_PATH = get_db_path()  # This will be updated dynamically through get_db_path() calls

# Allowed languages from the database
AVAILABLE_LANGUAGES = {
    'de': 'German (Deutsch)',
    'fr': 'French (Français)',
    'es': 'Spanish (Español)',
    'it': 'Italian (Italiano)',
    'nl': 'Dutch (Nederlands)',
    'pl': 'Polish (Polski)',
    'sv': 'Swedish (Svenska)',
    'da': 'Danish (Dansk)',
    'fi': 'Finnish (Suomi)',
    'el': 'Greek (Ελληνικά)',
    'cs': 'Czech (Čeština)',
    'hu': 'Hungarian (Magyar)',
    'ro': 'Romanian (Română)',
    'bg': 'Bulgarian (Български)',
    'sk': 'Slovak (Slovenčina)',
    'sl': 'Slovenian (Slovenščina)',
    'et': 'Estonian (Eesti)',
    'lv': 'Latvian (Latviešu)',
    'lt': 'Lithuanian (Lietuvių)',
    'hr': 'Croatian (Hrvatski)',
    'pt': 'Portuguese (Português)',
    'no': 'Norwegian (Norsk)',
    'is': 'Icelandic (Íslenska)',
}


def get_db_connection():
    """Get database connection using current database path."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_db_info():
    """Get information about currently selected database."""
    current_path = get_db_path()
    for key, config in DATABASE_OPTIONS.items():
        if config['path'] == current_path:
            return {
                'key': key,
                'name': config['name'],
                'description': config['description'],
                'path': current_path
            }
    return {
        'key': 'unknown',
        'name': 'Unknown Database',
        'description': 'Custom database path',
        'path': current_path
    }


@app.route('/')
def index():
    """Main page with default template loaded."""
    # Load default template (layout-gemini-fixed.html) if it exists
    default_template = "layout-gemini-fixed.html"
    template_loaded = False
    
    if os.path.exists(default_template):
        try:
            # Copy to upload folder with session ID
            import shutil
            session_id = os.urandom(16).hex()
            session['default_template_id'] = session_id
            
            default_path = os.path.join(UPLOAD_FOLDER, f"default_{session_id}.html")
            shutil.copy(default_template, default_path)
            
            # Store in session
            session['uploaded_file'] = default_path
            session['original_filename'] = default_template
            session['is_default'] = True
            template_loaded = True
        except Exception as e:
            print(f"Could not load default template: {e}")
    
    # Get current database info
    current_db_info = get_current_db_info()
    available_dbs = get_available_databases()
    
    return render_template('index.html', 
                         languages=AVAILABLE_LANGUAGES, 
                         template_loaded=template_loaded, 
                         default_template=default_template,
                         current_database=current_db_info,
                         available_databases=available_dbs)


@app.route('/api/languages')
def get_languages():
    """Get available languages."""
    return jsonify(AVAILABLE_LANGUAGES)


@app.route('/api/databases', methods=['GET'])
def get_databases():
    """Get available database options with current status."""
    return jsonify({
        'current': get_current_db_info(),
        'available': get_available_databases()
    })


@app.route('/api/databases/select', methods=['POST'])
def select_database():
    """Select a different database for translation."""
    data = request.json
    db_key = data.get('database')
    
    if not db_key:
        return jsonify({'error': 'No database key provided'}), 400
    
    success, message = set_db_path(db_key)
    
    if success:
        # Store selection in session
        session['selected_database'] = db_key
        return jsonify({
            'success': True,
            'message': message,
            'current': get_current_db_info()
        })
    else:
        return jsonify({
            'success': False,
            'error': message,
            'current': get_current_db_info()
        }), 400


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload HTML file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith('.html'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Store in session
        session['uploaded_file'] = filepath
        session['original_filename'] = filename
        
        # Read file content for preview
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'size': len(content),
            'preview': content[:5000]  # First 5000 chars for preview
        })
    
    return jsonify({'error': 'Invalid file type. Only HTML files allowed.'}), 400


# =============================================================================
# PDF Import API - NEW DYNAMIC WORKFLOW
# =============================================================================
@app.route('/api/pdf/process', methods=['POST'])
def process_pdf_dynamic():
    """
    New endpoint to process an uploaded PDF using the dynamic sds_parser
    and render it with the sds_template.html.
    """
    if not SDS_PARSER_V5_AVAILABLE:
        return jsonify({'error': 'The new SDS parser is not available.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Please select a valid PDF file.'}), 400

    temp_pdf_path = os.path.join(UPLOAD_FOLDER, f"pdf_{uuid.uuid4().hex}_{secure_filename(file.filename)}")
    
    try:
        file.save(temp_pdf_path)
        
        # Step 1: Parse the PDF using our new parser
        sds_data = parse_sds_pdf(temp_pdf_path)
        if not sds_data:
            return jsonify({'error': 'Failed to parse the SDS PDF. The document might be scanned or have an unusual format.'}), 400

        # Step 2: Render the data with the new template
        # Using render_template_string is safer and cleaner than file I/O here
        rendered_html = render_template('sds_template.html', sds=sds_data)

        # Step 3: Save the rendered HTML to a temporary file
        rendered_filename = f"imported_{Path(file.filename).stem}.html"
        rendered_filepath = os.path.join(UPLOAD_FOLDER, rendered_filename)
        with open(rendered_filepath, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
            
        # Step 4: Store file info in session for translation
        session['uploaded_file'] = rendered_filepath
        session['original_filename'] = rendered_filename
        session['is_pdf_import'] = True
        session['pdf_source_file'] = temp_pdf_path

        return jsonify({
            'success': True,
            'filename': file.filename,
            'product_name': sds_data.get('meta', {}).get('product_name', 'Unknown'),
            'preview': rendered_html[:8000] # Return a preview of the rendered HTML
        })

    except Exception as e:
        import traceback
        logger.error(f"Error in /api/pdf/process: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    # We don't clean up the temp PDF here so it can be referenced if needed,
    # it will be cleaned by the OS eventually.


# =============================================================================
# PDF Import API (Legacy)
# =============================================================================

@app.route('/api/pdf/status')

# =============================================================================
# SDScom XML Import API - NEW
# =============================================================================
@app.route('/api/sdscom/process', methods=['POST'])
def process_sdscom_xml():
    """
    New endpoint to process an uploaded SDScom XML file, inject it into the
    master layout template, and return the result.
    """
    if not SDSCOM_PARSER_AVAILABLE:
        return jsonify({'error': 'The SDScom XML parser/importer is not available.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.xml'):
        return jsonify({'error': 'Please select a valid XML file.'}), 400

    temp_xml_path = os.path.join(UPLOAD_FOLDER, f"xml_{uuid.uuid4().hex}_{secure_filename(file.filename)}")
    
    try:
        file.save(temp_xml_path)
        
        # Define the master template path
        template_path = "layout-placeholders-fixed-v2.html"
        if not os.path.exists(template_path):
             return jsonify({'error': f'Master layout template not found at {template_path}'}), 500

        # Step 1: Use the new importer to get the final HTML string
        modified_html = import_sds_to_html(temp_xml_path, template_path)
        
        if not modified_html:
            return jsonify({'error': 'Failed to import XML data into template. The XML might be malformed or the template is incompatible.'}), 400

        # Step 2: Save the final HTML to a temporary file
        rendered_filename = f"imported_{Path(file.filename).stem}.html"
        rendered_filepath = os.path.join(UPLOAD_FOLDER, rendered_filename)
        with open(rendered_filepath, 'w', encoding='utf-8') as f:
            f.write(modified_html)
            
        # Step 3: Store file info in session for translation
        session['uploaded_file'] = rendered_filepath
        session['original_filename'] = rendered_filename
        session['is_xml_import'] = True
        session['xml_source_file'] = temp_xml_path

        # We can't easily get the product name anymore without parsing twice,
        # but we can return a success message.
        return jsonify({
            'success': True,
            'filename': file.filename,
            'product_name': 'Imported from XML',
            'preview': modified_html
        })

    except Exception as e:
        logger.error(f"Error in /api/sdscom/process: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    # We don't clean up the temp XML here so it can be referenced if needed,
    # it will be cleaned by the OS eventually.


# =============================================================================
# PDF Import API (Legacy)
# =============================================================================

@app.route('/api/pdf/status')
def pdf_import_status():
    """Check PDF import module status and dependencies."""
    if not PDF_IMPORT_AVAILABLE:
        return jsonify({
            'available': False,
            'error': 'PDF import module not available',
            'dependencies': {}
        })
    
    deps = check_dependencies()
    return jsonify({
        'available': True,
        'dependencies': deps,
        'config': {
            'max_file_size': PDF_IMPORT_CONFIG['max_file_size'],
            'max_file_size_mb': PDF_IMPORT_CONFIG['max_file_size'] / (1024 * 1024),
            'min_file_size': PDF_IMPORT_CONFIG['min_file_size'],
            'supported_versions': PDF_IMPORT_CONFIG['supported_versions'],
            'max_pages': PDF_IMPORT_CONFIG['max_pages']
        }
    })


@app.route('/api/pdf/validate', methods=['POST'])
def pdf_validate():
    """Validate a PDF file before full import."""
    if not PDF_IMPORT_AVAILABLE:
        return jsonify({'error': 'PDF import module not available'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Invalid file type. Only PDF files allowed.'}), 400
    
    # Save to temp file for validation
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, f"pdf_validate_{os.urandom(8).hex()}_{filename}")
    
    try:
        file.save(filepath)
        
        # Create importer and validate
        config = PDFImportConfig(
            max_file_size=PDF_IMPORT_CONFIG['max_file_size'],
            min_file_size=PDF_IMPORT_CONFIG['min_file_size']
        )
        importer = PDFImporter(config)
        
        # Validate file
        is_valid, error_message = importer.validate_file(filepath)
        
        if not is_valid:
            return jsonify({
                'valid': False,
                'error': error_message,
                'error_type': 'validation'
            }), 400
        
        # Extract basic metadata
        metadata = importer.extract_metadata(filepath)
        content_type = importer.detect_content_type(filepath)
        
        return jsonify({
            'valid': True,
            'filename': filename,
            'metadata': {
                'title': metadata.title,
                'author': metadata.author,
                'page_count': metadata.page_count,
                'is_encrypted': metadata.is_encrypted,
                'is_form': metadata.is_form
            },
            'content_type': content_type.value,
            'size': os.path.getsize(filepath)
        })
        
    except Exception as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 500
    finally:
        # Clean up temp file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass


@app.route('/api/pdf/upload', methods=['POST'])
def pdf_upload():
    """Upload and process a PDF file using layout-gemini-fixed.html template."""
    if not PDF_IMPORT_AVAILABLE:
        return jsonify({'error': 'PDF import module not available'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Invalid file type. Only PDF files allowed.'}), 400
    
    # Save to temp file
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, f"pdf_{os.urandom(8).hex()}_{filename}")
    
    try:
        file.save(filepath)
        
        # Use template-based importer if available
        if SDS_TEMPLATE_IMPORT_AVAILABLE:
            # Use SDSTemplateImporter which uses layout-gemini-fixed.html
            importer = SDSTemplateImporter("layout-gemini-fixed.html")
            result = importer.import_pdf_to_template(
                filepath,
                output_html=os.path.join(UPLOAD_FOLDER, f"{os.path.splitext(filename)[0]}_template.html"),
                output_pdf=os.path.join(UPLOAD_FOLDER, f"{os.path.splitext(filename)[0]}_template.pdf")
            )
            
            if result.get('success'):
                # Store in session for translation
                if result.get('html_output'):
                    session['uploaded_file'] = result['html_output']
                    session['original_filename'] = os.path.basename(result['html_output'])
                    session['is_pdf_import'] = True
                    session['pdf_source_file'] = filepath
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'sections_found': result.get('sections_found', []),
                    'html_output': result.get('html_output'),
                    'pdf_output': result.get('pdf_output'),
                    'warnings': result.get('warnings', [])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Template import failed')
                }), 400
        
        # Fallback to original importer
        config = PDFImportConfig(
            max_file_size=PDF_IMPORT_CONFIG['max_file_size'],
            min_file_size=PDF_IMPORT_CONFIG['min_file_size'],
            max_pages_for_full_extraction=PDF_IMPORT_CONFIG['max_pages'],
            detect_sds_phrases=True
        )
        importer = PDFImporter(config)
        
        # Import PDF
        result = importer.import_pdf(filepath)
        
        if not result.success:
            error_type = result.error_code or 'UNKNOWN_ERROR'
            return jsonify({
                'success': False,
                'error': result.error_message,
                'error_code': error_type
            }), 400
        
        # Save HTML content to file
        if result.html_content:
            html_filename = f"{os.path.splitext(filename)[0]}.html"
            html_filepath = os.path.join(UPLOAD_FOLDER, html_filename)
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(result.html_content)
            
            # Store in session for translation
            session['uploaded_file'] = html_filepath
            session['original_filename'] = html_filename
            session['is_pdf_import'] = True
            session['pdf_source_file'] = filepath
        
        return jsonify({
            'success': True,
            'filename': filename,
            'html_filename': html_filename if result.html_content else None,
            'metadata': {
                'title': result.metadata.title if result.metadata else None,
                'author': result.metadata.author if result.metadata else None,
                'page_count': result.page_count,
                'is_encrypted': result.metadata.is_encrypted if result.metadata else False
            },
            'text_length': len(result.text_content) if result.text_content else 0,
            'extracted_phrases': result.extracted_phrases[:50],
            'phrase_count': len(result.extracted_phrases),
            'warnings': result.warnings,
            'processing_time': result.processing_time,
            'preview': result.html_content[:5000] if result.html_content else None
        })
        
    except Exception as e:
        import traceback
        return jsonify({'error': f'PDF import failed: {str(e)}', 'trace': traceback.format_exc()}), 500


@app.route('/api/pdf/progress/<task_id>', methods=['GET'])
def pdf_progress(task_id):
    """Get progress of async PDF processing (placeholder for future use)."""
    # For future async processing implementation
    return jsonify({
        'task_id': task_id,
        'status': 'completed',
        'progress': 100
    })


@app.route('/api/default-load')
def default_load():
    """Load default template (layout-gemini-fixed.html) on startup."""
    default_template = "layout-gemini-fixed.html"
    
    if os.path.exists(default_template):
        try:
            # Read the default template
            with open(default_template, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Save to temp folder
            filename = f"default_{os.urandom(8).hex()}.html"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Store in session
            session['uploaded_file'] = filepath
            session['original_filename'] = default_template
            
            return jsonify({
                'success': True,
                'filename': default_template,
                'preview': content[:5000]
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Default template not found'})


@app.route('/api/translate', methods=['POST'])
def translate():
    """Translate uploaded file."""
    data = request.json
    target_lang = data.get('language', 'de')
    
    if 'uploaded_file' not in session:
        return jsonify({'error': 'No file uploaded'}), 400
    
    input_file = session['uploaded_file']
    output_filename = f"translated_{target_lang}_{session['original_filename']}"
    output_file = os.path.join(UPLOAD_FOLDER, output_filename)
    
    try:
        # Create translator with current database
        current_db = get_db_path()
        translator = SDSTranslator(current_db, target_lang, debug=False)
        
        # Read and translate
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        translated_html = translator.translate_html(html_content)
        
        # Save output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_html)
        
        # Store output path
        session['translated_file'] = output_file
        session['target_language'] = target_lang
        
        # Get not found phrases (show all, no limit)
        not_found = translator.not_found_log
        
        return jsonify({
            'success': True,
            'stats': translator.stats,
            'coverage': translator.stats['translated_exact'] / max(translator.stats['total_texts'], 1) * 100,
            'not_found': not_found,
            'preview': translated_html,
            'database': get_current_db_info()
        })
    
    except Exception as e:
        import traceback
        with open('error.log', 'a') as f:
            f.write(f"Error in /api/translate: {e}\n{traceback.format_exc()}\n")
        logger.error(f"Error in /api/translate: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500





@app.route('/api/phrases/<phrase_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_phrase(phrase_id):
    """Get, update or delete a phrase by UUID or ID."""
    conn = get_db_connection()
    
    if request.method == 'GET':
        cursor = conn.execute(
            "SELECT * FROM phrases WHERE id = ?",
            (phrase_id,)
        )
        phrase = cursor.fetchone()
        conn.close()
        
        if phrase:
            return jsonify(dict(phrase))
        return jsonify({'error': 'Phrase not found'}), 404
    
    elif request.method == 'PUT':
        data = request.json
        
        # Build update query dynamically based on provided fields
        update_fields = []
        values = []
        
        for field in ['en_original', 'de_original', 'fr_original', 'es_original', 
                      'it_original', 'nl_original', 'pl_original', 'sv_original',
                      'da_original', 'fi_original', 'el_original', 'cs_original',
                      'hu_original', 'ro_original', 'bg_original', 'sk_original',
                      'sl_original', 'et_original', 'lv_original', 'lt_original',
                      'hr_original', 'pt_original', 'no_original', 'is_original']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        values.append(phrase_id)
        query = f"UPDATE phrases SET {', '.join(update_fields)} WHERE id = ?"
        
        try:
            conn.execute(query, values)
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Phrase updated'})
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    elif request.method == 'DELETE':
        try:
            conn.execute("DELETE FROM phrases WHERE id = ?", (phrase_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Phrase deleted'})
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500


@app.route('/api/phrases', methods=['POST'])
def add_phrase():
    """Add new phrase to database."""
    data = request.json
    
    en_text = data.get('en_original', '').strip()
    if not en_text:
        return jsonify({'error': 'English text is required'}), 400
    
    conn = get_db_connection()
    
    # Check if phrase already exists
    cursor = conn.execute(
        "SELECT id FROM phrases WHERE en_original = ?",
        (en_text,)
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Phrase already exists'}), 409
    
    # Generate UUID for new phrase
    new_id = str(uuid.uuid4())
    
    # Insert new phrase
    fields = ['id', 'en_original']
    values = [new_id, en_text]
    placeholders = ['?', '?']
    
    for lang in ['de', 'fr', 'es', 'it', 'nl', 'pl', 'sv', 'da', 'fi', 'el', 
                 'cs', 'hu', 'ro', 'bg', 'sk', 'sl', 'et', 'lv', 'lt', 'hr', 
                 'pt', 'no', 'is']:
        field = f'{lang}_original'
        if field in data and data[field].strip():
            fields.append(field)
            values.append(data[field].strip())
            placeholders.append('?')
    
    query = f"INSERT INTO phrases ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
    
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': new_id, 'message': 'Phrase added'})


# Language code mapping (2-letter ISO codes)
LANGUAGE_CODE_MAP = {
    'EN': 'en', 'EN': 'en',
    'DE': 'de', 'DE': 'de',
    'FR': 'fr', 'FR': 'fr',
    'ES': 'es', 'ES': 'es',
    'IT': 'it', 'IT': 'it',
    'NL': 'nl', 'NL': 'nl',
    'PL': 'pl', 'PL': 'pl',
    'SV': 'sv', 'SV': 'sv',
    'DA': 'da', 'DA': 'da',
    'FI': 'fi', 'FI': 'fi',
    'EL': 'el', 'EL': 'el',
    'CS': 'cs', 'CS': 'cs',
    'HU': 'hu', 'HU': 'hu',
    'RO': 'ro', 'RO': 'ro',
    'BG': 'bg', 'BG': 'bg',
    'SK': 'sk', 'SK': 'sk',
    'SL': 'sl', 'SL': 'sl',
    'ET': 'et', 'ET': 'et',
    'LV': 'lv', 'LV': 'lv',
    'LT': 'lt', 'LT': 'lt',
    'HR': 'hr', 'HR': 'hr',
    'PT': 'pt', 'PT': 'pt',
    'NO': 'no', 'NO': 'no',
    'IS': 'is', 'IS': 'is',
}

# Language code to database column mapping
LANG_TO_COLUMN = {
    'en': 'en_original',
    'de': 'de_original',
    'fr': 'fr_original',
    'es': 'es_original',
    'it': 'it_original',
    'nl': 'nl_original',
    'pl': 'pl_original',
    'sv': 'sv_original',
    'da': 'da_original',
    'fi': 'fi_original',
    'el': 'el_original',
    'cs': 'cs_original',
    'hu': 'hu_original',
    'ro': 'ro_original',
    'bg': 'bg_original',
    'sk': 'sk_original',
    'sl': 'sl_original',
    'et': 'et_original',
    'lv': 'lv_original',
    'lt': 'lt_original',
    'hr': 'hr_original',
    'pt': 'pt_original',
    'no': 'no_original',
    'is': 'is_original',
}


def parse_flag_format(text):
    """Parse the language code based multi-language phrase format."""
    import re
    
    phrases = []
    current_lang = None
    current_text = []
    source_lang = 'en'  # Default source language
    
    # Split by lines
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for language header (2-letter code + optional language name)
        # Format: "EN:" or "EN English" or "EN (Original)" or "EN:"
        match = re.match(r'^([A-Z]{2})[\s:\(]*(.*)$', line)
        if match:
            # Save previous phrase if exists
            if current_lang and current_text:
                phrase_text = '\n'.join(current_text).strip()
                if phrase_text:
                    phrases.append((current_lang, phrase_text))
            
            # Start new language
            lang_code_raw = match.group(1)
            lang_name = match.group(2).strip()
            lang_code = LANGUAGE_CODE_MAP.get(lang_code_raw, lang_code_raw.lower())
            
            if lang_code:
                current_lang = lang_code
                current_text = []
                
                # Check if this is marked as "Original" or "(Original)"
                if 'original' in lang_name.lower():
                    source_lang = lang_code
        else:
            # This is translation text
            if current_lang:
                current_text.append(line)
    
    # Add last phrase
    if current_lang and current_text:
        phrase_text = '\n'.join(current_text).strip()
        if phrase_text:
            phrases.append((current_lang, phrase_text))
    
    return phrases, source_lang


@app.route('/api/phrases/bulk/update', methods=['POST'])
def bulk_update_phrases():
    """Bulk update phrases from text format."""
    data = request.json
    text = data.get('text', '').strip()
    source_lang = data.get('source_lang', 'en')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Parse the text format
    phrases, detected_source = parse_flag_format(text)
    
    # Use detected source if not explicitly set
    if source_lang == 'auto' or not source_lang:
        source_lang = detected_source
    
    if not phrases:
        return jsonify({'error': 'No valid phrases found in text'}), 400
    
    conn = get_db_connection()
    updated_count = 0
    created_count = 0
    errors = []
    
    # Find the source phrase (the one matching source_lang)
    source_text = None
    translations = {}
    
    for lang, phrase_text in phrases:
        if lang == source_lang:
            source_text = phrase_text
        else:
            translations[lang] = phrase_text
    
    if not source_text:
        return jsonify({'error': f'No source phrase found for language: {source_lang}'}), 400
    
    # Find existing phrase or create new one
    source_column = LANG_TO_COLUMN.get(source_lang, 'en_original')
    
    try:
        # Check if phrase exists
        cursor = conn.execute(
            f"SELECT id FROM phrases WHERE {source_column} = ?",
            (source_text,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing phrase
            phrase_id = existing['id']
            update_fields = []
            values = []
            
            for lang, translated_text in translations.items():
                col = LANG_TO_COLUMN.get(lang)
                if col:
                    update_fields.append(f"{col} = ?")
                    values.append(translated_text)
            
            if update_fields:
                values.append(phrase_id)
                conn.execute(
                    f"UPDATE phrases SET {', '.join(update_fields)} WHERE id = ?",
                    values
                )
                updated_count += 1
        else:
            # Create new phrase
            new_id = str(uuid.uuid4())
            fields = ['id', source_column]
            values = [new_id, source_text]
            placeholders = ['?', '?']
            
            for lang, translated_text in translations.items():
                col = LANG_TO_COLUMN.get(lang)
                if col:
                    fields.append(col)
                    values.append(translated_text)
                    placeholders.append('?')
            
            conn.execute(
                f"INSERT INTO phrases ({', '.join(fields)}) VALUES ({', '.join(placeholders)})",
                values
            )
            created_count += 1
        
        conn.commit()
        
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    conn.close()
    
    return jsonify({
        'success': True,
        'updated': updated_count,
        'created': created_count,
        'source_language': source_lang,
        'source_phrase': source_text[:100] + '...' if len(source_text) > 100 else source_text
    })


@app.route('/api/phrases/bulk/upload', methods=['POST'])
def bulk_upload_phrases():
    """Bulk upload phrases from TXT file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    source_lang = request.form.get('source_lang', 'auto')
    
    if not file.filename.endswith('.txt'):
        return jsonify({'error': 'Only .txt files are allowed'}), 400
    
    try:
        text = file.read().decode('utf-8')
    except Exception as e:
        return jsonify({'error': 'Could not read file'}), 400
    
    # Parse the text format
    phrases, detected_source = parse_flag_format(text)
    
    # Use detected source if not explicitly set
    if source_lang == 'auto' or not source_lang:
        source_lang = detected_source
    
    if not phrases:
        return jsonify({'error': 'No valid phrases found in file'}), 400
    
    conn = get_db_connection()
    updated_count = 0
    created_count = 0
    
    # Group translations by source phrase
    source_phrases = {}
    for lang, phrase_text in phrases:
        if lang == source_lang:
            source_phrases[phrase_text] = {'translations': {}}
        else:
            # Add to the last source phrase
            if source_phrases:
                last_source = list(source_phrases.keys())[-1]
                source_phrases[last_source]['translations'][lang] = phrase_text
    
    try:
        for source_text, data in source_phrases.items():
            translations = data['translations']
            
            source_column = LANG_TO_COLUMN.get(source_lang, 'en_original')
            
            # Check if phrase exists
            cursor = conn.execute(
                f"SELECT id FROM phrases WHERE {source_column} = ?",
                (source_text,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing phrase
                phrase_id = existing['id']
                update_fields = []
                values = []
                
                for lang, translated_text in translations.items():
                    col = LANG_TO_COLUMN.get(lang)
                    if col:
                        update_fields.append(f"{col} = ?")
                        values.append(translated_text)
                
                if update_fields:
                    values.append(phrase_id)
                    conn.execute(
                        f"UPDATE phrases SET {', '.join(update_fields)} WHERE id = ?",
                        values
                    )
                    updated_count += 1
            else:
                # Create new phrase
                new_id = str(uuid.uuid4())
                fields = ['id', source_column]
                values = [new_id, source_text]
                placeholders = ['?', '?']
                
                for lang, translated_text in translations.items():
                    col = LANG_TO_COLUMN.get(lang)
                    if col:
                        fields.append(col)
                        values.append(translated_text)
                        placeholders.append('?')
                
                conn.execute(
                    f"INSERT INTO phrases ({', '.join(fields)}) VALUES ({', '.join(placeholders)})",
                    values
                )
                created_count += 1
        
        conn.commit()
        
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    conn.close()
    
    return jsonify({
        'success': True,
        'updated': updated_count,
        'created': created_count,
        'source_language': source_lang,
        'total_phrases': len(source_phrases)
    })


@app.route('/api/preview/original')
def preview_original():
    """Get original file content for preview."""
    if 'uploaded_file' not in session:
        return jsonify({'error': 'No file uploaded'}), 400
    
    with open(session['uploaded_file'], 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({'content': content})


@app.route('/api/preview/translated')
def preview_translated():
    """Get translated file content for preview."""
    if 'translated_file' not in session:
        return jsonify({'error': 'No translation available'}), 400
    
    with open(session['translated_file'], 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({'content': content})


@app.route('/api/save/original', methods=['POST'])
def save_original():
    """Save edited original content."""
    if 'uploaded_file' not in session:
        return jsonify({'error': 'No file uploaded', 'success': False}), 400
    
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No content provided', 'success': False}), 400
        
        new_content = data['content']
        
        # Save the edited content
        with open(session['uploaded_file'], 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return jsonify({'success': True, 'message': 'Original file saved successfully'})
    
    except Exception as e:
        import traceback
        return jsonify({'error': str(e) + '\n' + traceback.format_exc(), 'success': False}), 500


@app.route('/api/save/translated', methods=['POST'])
def save_translated():
    """Save edited translated content."""
    if 'translated_file' not in session:
        return jsonify({'error': 'No translation available', 'success': False}), 400
    
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No content provided', 'success': False}), 400
        
        new_content = data['content']
        
        # Clean up the content - remove any unwanted artifacts
        # The content from contenteditable might have some extra markup
        new_content = new_content.strip()
        
        # Read the original file to preserve the complete structure
        with open(session['translated_file'], 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Check if it's a complete HTML document or just body content
        if '<html' in original_content.lower():
            # It's a complete HTML document - extract head and replace body
            # Find and extract the head section
            head_match = re.search(r'(<head[^>]*>[\s\S]*?</head>)', original_content, re.IGNORECASE)
            
            if head_match:
                head_section = head_match.group(1)
                # Create new HTML with the edited content in body
                new_html = f'''<!DOCTYPE html>
<html lang="de">
{head_section}
<body>
{new_content}
</body>
</html>'''
            else:
                # No head found, try to preserve the original structure
                # Look for existing body
                body_match = re.search(r'<body[^>]*>([\s\S]*?)</body>', original_content, re.IGNORECASE)
                if body_match:
                    # Replace just the body content
                    new_html = original_content[:body_match.start()]
                    new_html += f'<body>\n{new_content}\n</body>'
                    new_html += original_content[body_match.end():]
                else:
                    # Create new complete document
                    new_html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=210mm">
    <title>Bearbeitete Übersetzung</title>
</head>
<body>
{new_content}
</body>
</html>'''
        else:
            # Not a complete HTML, treat as body content
            new_html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=210mm">
    <title>Bearbeitete Übersetzung</title>
</head>
<body>
{new_content}
</body>
</html>'''
        
        # Save the edited content
        with open(session['translated_file'], 'w', encoding='utf-8') as f:
            f.write(new_html)
        
        return jsonify({'success': True, 'message': 'Translation saved successfully'})
    
    except Exception as e:
        import traceback
        return jsonify({'error': str(e) + '\n' + traceback.format_exc(), 'success': False}), 500


@app.route('/api/download')
def download_translated():
    """Download translated file."""
    if 'translated_file' not in session:
        return jsonify({'error': 'No translation available'}), 400
    
    return send_file(
        session['translated_file'],
        as_attachment=True,
        download_name=f"translated_{session.get('target_language', 'de')}_{session['original_filename']}"
    )


@app.route('/api/download/pdf')
def download_pdf():
    """Download translated file as PDF."""
    if 'translated_file' not in session:
        return jsonify({'error': 'No translation available'}), 400
    
    try:
        # Read the translated HTML
        with open(session['translated_file'], 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Generate PDF using WeasyPrint
        if WEASYPRINT_AVAILABLE:
            # Add PDF-specific CSS for A4 format with GHS pictogram sizing
            # 23mm x 23mm @ 300 DPI for print quality
            pdf_css = CSS(string='''
                @page {
                    size: A4;
                    margin: 0;
                }
                body {
                    margin: 0 !important;
                    padding: 0 !important;
                }
                .page {
                    page-break-after: always;
                    border: none !important;
                    margin: 0 !important;
                }
                .page:last-child {
                    page-break-after: auto;
                }
                /* GHS Pictogram styling for PDF: 23x23mm at 300 DPI */
                .ghs-pictogram {
                    width: 23mm !important;
                    height: 23mm !important;
                    display: inline-block;
                    margin-right: 2mm;
                }
                .ghs-pictogram img {
                    width: 23mm !important;
                    height: 23mm !important;
                    object-fit: contain;
                }
                .ghs-pictogram-container {
                    display: flex;
                    flex-direction: row;
                    gap: 2mm;
                    flex-wrap: wrap;
                }
            ''')
            
            # Fix logo path for PDF generation - copy logo to temp directory
            # The logo should be in the app's root directory
            logo_path = os.path.abspath('mb_logo.svg')
            logo_dest = os.path.join(UPLOAD_FOLDER, 'mb_logo.svg')
            shutil.copy(logo_path, logo_dest)
            
            # Also copy GHS pictograms if they exist
            ghs_dir = os.path.abspath('ghs')
            if os.path.exists(ghs_dir):
                ghs_dest = os.path.join(UPLOAD_FOLDER, 'ghs')
                if os.path.exists(ghs_dest):
                    shutil.rmtree(ghs_dest)
                shutil.copytree(ghs_dir, ghs_dest)
            
            # Replace ghs-placeholder divs with actual images for PDF
            # Extract data-symbol attributes and replace with img tags
            import re
            ghs_pattern = re.compile(r'<div class="ghs-placeholder" data-symbol="(GHS\d+)">[\s\S]*?</div>')
            def replace_ghs_placeholder(match):
                symbol = match.group(1)
                # Map GHS code to filename (e.g., GHS02 -> ghs02.png)
                ghs_num = symbol.replace('GHS', '').lower().zfill(2)
                return f'<img src="ghs/ghs{ghs_num}.png" style="width:84px;height:84px;display:inline-block;" alt="{symbol}" title="{symbol}">'
            html_content = ghs_pattern.sub(replace_ghs_placeholder, html_content)
            
            html_obj = HTML(string=html_content, base_url=UPLOAD_FOLDER)
            pdf_bytes = html_obj.write_pdf(stylesheets=[pdf_css])
            
            # Create temporary PDF file
            pdf_filename = f"translated_{session.get('target_language', 'de')}_{session['original_filename'].replace('.html', '.pdf')}"
            pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=pdf_filename,
                mimetype='application/pdf'
            )
        else:
            # Fallback to HTML if WeasyPrint not available
            return jsonify({'error': 'PDF generation not available. Please install WeasyPrint.'}), 500
            
    except Exception as e:
        import traceback
        print(f"PDF generation error: {traceback.format_exc()}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@app.route('/api/phrases/search', methods=['POST'])
def search_phrases():
    """Search phrases in database - now with GLOBAL search across ALL languages."""
    data = request.json or {}
    query = data.get('q', '')
    lang = data.get('lang', 'de')
    search_mode = data.get('mode', 'global')  # 'global', 'en', 'target'
    
    conn = get_db_connection()
    
    # All language columns
    all_langs = ['bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'et', 'fi', 'fr',
                 'hr', 'hu', 'it', 'lt', 'lv', 'mt', 'nl', 'no', 'pl', 'pt',
                 'ro', 'sk', 'sl', 'sv', 'is']
    
    try:
        if query:
            search_pattern = f'%{query}%'
            exact_match = query
            start_match = f'{query}%'
            
            if search_mode == 'en':
                # Search only in English
                cursor = conn.execute(
                    """SELECT id, en_original, {0}_original as translation
                        FROM phrases
                        WHERE en_original LIKE ?
                        ORDER BY
                            CASE WHEN en_original = ? THEN 0
                                 WHEN en_original LIKE ? THEN 1
                                 ELSE 2
                            END,
                            en_original
                        LIMIT 100""".format(lang),
                    (search_pattern, exact_match, start_match)
                )
            elif search_mode == 'target':
                # Search only in target language
                cursor = conn.execute(
                    """SELECT id, en_original, {0}_original as translation
                        FROM phrases
                        WHERE {0}_original LIKE ?
                        ORDER BY
                            CASE WHEN {0}_original = ? THEN 0
                                 WHEN {0}_original LIKE ? THEN 1
                                 ELSE 2
                            END,
                            en_original
                        LIMIT 100""".format(lang),
                    (search_pattern, exact_match, start_match)
                )
            else:  # global - search in ALL languages (simplified)
                # Build WHERE clause for all languages - one parameter per language
                where_conditions = ' OR '.join([f'{l}_original LIKE ?' for l in all_langs])
                
                # Simplified ORDER BY - just prioritize exact matches in any language
                # We need 25 params for WHERE, then 25 for exact match check, 25 for starts-with check
                params = [search_pattern] * len(all_langs)  # For WHERE (25 params)
                params.extend([exact_match] * len(all_langs))  # For exact match ORDER (25 params)
                
                cursor = conn.execute(
                    f"""SELECT id, en_original, {lang}_original as translation
                        FROM phrases
                        WHERE {where_conditions}
                        ORDER BY
                            CASE
                                WHEN {' OR '.join([f'{l}_original = ?' for l in all_langs])} THEN 0
                                ELSE 1
                            END,
                            en_original
                        LIMIT 100""",
                    tuple(params)
                )
        else:
            # Get recent phrases
            cursor = conn.execute(
                f"""SELECT id, en_original, {lang}_original as translation
                    FROM phrases
                    ORDER BY id DESC
                    LIMIT 50"""
            )
        
        phrases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(phrases)
    
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/phrases/<phrase_id>/full', methods=['GET'])
def get_phrase_full(phrase_id):
    """Get full phrase data with ALL language fields for editing."""
    conn = get_db_connection()
    
    cursor = conn.execute(
        """SELECT * FROM phrases WHERE id = ?""",
        (phrase_id,)
    )
    phrase = cursor.fetchone()
    conn.close()
    
    if phrase:
        return jsonify(dict(phrase))
    return jsonify({'error': 'Phrase not found'}), 404


@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    conn = get_db_connection()
    
    # Total phrases
    cursor = conn.execute("SELECT COUNT(*) as count FROM phrases")
    total = cursor.fetchone()['count']
    
    # Phrases per language
    lang_stats = {}
    for lang in ['de', 'fr', 'es', 'it', 'nl', 'pl', 'sv', 'da', 'fi', 'el',
                 'cs', 'hu', 'ro', 'bg', 'sk', 'sl', 'et', 'lv', 'lt', 'hr',
                 'pt', 'no', 'is']:
        cursor = conn.execute(
            f"SELECT COUNT(*) as count FROM phrases WHERE {lang}_original IS NOT NULL AND {lang}_original != ''"
        )
        lang_stats[lang] = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_phrases': total,
        'per_language': lang_stats
    })


# =============================================================================
# GHS Pictogram Management API
# =============================================================================

from ghs_pictogram_manager import GHSPictogramManager

pictogram_manager = GHSPictogramManager()

@app.route('/api/ghs/pictograms', methods=['GET'])
def get_ghs_pictograms():
    """Get all available GHS pictograms with filtering."""
    hazard_class = request.args.get('class', None)
    
    pictograms = pictogram_manager.get_all_pictograms()
    
    if hazard_class:
        pictograms = [p for p in pictograms if p.get('hazard_class') == hazard_class]
    
    return jsonify(pictograms)

@app.route('/api/ghs/pictograms/<code>', methods=['GET'])
def get_ghs_pictogram(code):
    """Get specific GHS pictogram by code."""
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    
    if pictogram:
        return jsonify(pictogram)
    return jsonify({'error': 'Pictogram not found'}), 404

@app.route('/api/ghs/pictograms/<code>/svg')
def get_ghs_pictogram_svg(code):
    """Serve GHS pictogram SVG or PNG file."""
    # Try SVG first
    pictogram = pictogram_manager.get_pictogram_by_code(code)
    if pictogram and pictogram.get('svg_path'):
        svg_path = pictogram['svg_path']
        if os.path.exists(svg_path):
            return send_file(svg_path, mimetype='image/svg+xml')
    
    # Fallback to PNG from ghs folder
    png_path = os.path.join('ghs', f'{code.lower()}.png')
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')
    
    return jsonify({'error': 'Pictogram not found'}), 404


@app.route('/api/ghs/pictograms/<code>/png')
def get_ghs_pictogram_png(code):
    """Serve GHS pictogram PNG file directly from ghs folder."""
    png_path = os.path.join('ghs', f'{code.lower()}.png')
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')
    return jsonify({'error': 'PNG not found'}), 404

@app.route('/ghs/<path:filename>')
def serve_ghs_image(filename):
    """Serve GHS pictogram images from ghs folder."""
    return send_from_directory('ghs', filename)

@app.route('/mb_logo.svg')
def serve_logo():
    """Serve the company logo."""
    return send_from_directory('.', 'mb_logo.svg', mimetype='image/svg+xml')

@app.route('/api/sds/<sds_id>/pictograms', methods=['GET'])
def get_sds_pictograms(sds_id):
    """Get all pictograms assigned to an SDS document."""
    pictograms = pictogram_manager.get_sds_pictograms(sds_id)
    return jsonify(pictograms)

@app.route('/api/sds/<sds_id>/pictograms', methods=['POST'])
def add_sds_pictogram(sds_id):
    """Add a pictogram to an SDS document (max 3)."""
    data = request.json
    ghs_code = data.get('ghs_code')
    position = data.get('position', None)
    
    if not ghs_code:
        return jsonify({'error': 'GHS code required'}), 400
    
    success, message = pictogram_manager.add_pictogram_to_sds(sds_id, ghs_code, position)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400

@app.route('/api/sds/<sds_id>/pictograms/<ghs_code>', methods=['DELETE'])
def remove_sds_pictogram(sds_id, ghs_code):
    """Remove a pictogram from an SDS document."""
    deleted = pictogram_manager.remove_pictogram_from_sds(sds_id, ghs_code)
    
    if deleted:
        return jsonify({'success': True, 'message': 'Pictogram removed'})
    return jsonify({'error': 'Pictogram not found in SDS'}), 404

@app.route('/api/sds/<sds_id>/pictograms/reorder', methods=['PUT'])
def reorder_sds_pictograms(sds_id):
    """Update positions of pictograms."""
    data = request.json
    ordered_codes = data.get('ordered_codes', [])
    
    if not ordered_codes:
        return jsonify({'error': 'Ordered codes required'}), 400
    
    success = pictogram_manager.update_pictogram_positions(sds_id, ordered_codes)
    
    if success:
        return jsonify({'success': True, 'message': 'Positions updated'})
    return jsonify({'error': 'Failed to update positions'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
