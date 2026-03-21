import json
from sds_translator_v4 import SDSTranslator
from database import get_db_path

db_path = "phrases_library.db"
target_lang = "de"
translator = SDSTranslator(db_path, target_lang, debug=False)

with open('layout-placeholders-fixed-v2.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

translated_html = translator.translate_html(html_content)

# Now pass it to the PDF exporter directly
from routes.main import export_translated_pdf

# Mock response object return handling
# We just need to call the function and get the bytes
try:
    import builtins
    builtins.target_lang_mock = target_lang
    builtins.lang_name_mock = "Deutsch"
    
    # Flask make_response needs app context, so let's just make a dummy app context
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context():
        response = export_translated_pdf(translated_html, target_lang, "Deutsch")
        with open('test_weasyprint.pdf', 'wb') as f:
            f.write(response.get_data())
    print("PDF Export successful")
except Exception as e:
    print(f"Error: {e}")
