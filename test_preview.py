import json
from sds_translator_v4 import SDSTranslator

db_path = "phrases_library.db"
target_lang = "de"
translator = SDSTranslator(db_path, target_lang, debug=False)

with open('layout-placeholders-fixed-v2.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

translated_html = translator.translate_html(html_content)

with open('test_preview.html', 'w', encoding='utf-8') as f:
    f.write(translated_html)

print("Translation preview generated.")
