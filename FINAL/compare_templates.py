import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

print("="*70)
print("TEMPLATE COMPARISON: Word vs HTML Output")
print("="*70)

# Extract Word structure
docx = Path.home() / 'Downloads' / 'MB_SDS_Word_PERFEKT.docx'
with zipfile.ZipFile(docx) as z:
    root = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    word_texts = []
    for p in root.findall('.//w:p', ns):
        text = ''.join(t.text or '' for t in p.findall('.//w:t', ns))
        if text.strip():
            word_texts.append(text.strip())

# Parse generated HTML
html_path = Path('importer_output.html')
with open(html_path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    # Extract all text content
    html_texts = []
    for elem in soup.find_all(['p', 'div', 'td', 'th', 'span']):
        text = elem.get_text(strip=True)
        if text and len(text) > 5:
            html_texts.append(text)

# Find Section 2 (Hazards) in both
print("\n📋 SECTION 2 (Hazards) STRUCTURE COMPARISON:\n")

# Word version
word_sec2 = [t for t in word_texts if 'SECTION 2' in t or 'Hazard' in t][:30]
print("WORD FORMAT (first 15 entries):")
for i, t in enumerate(word_sec2[:15], 1):
    print(f"  {i:2d}. {t[:70]}")

# HTML version
html_sec2 = [t for t in html_texts if 'SECTION 2' in t or 'Hazard' in t or 'Signal word' in t][:30]
print("\nHTML FORMAT (first 15 entries):")
for i, t in enumerate(html_sec2[:15], 1):
    print(f"  {i:2d}. {t[:70]}")

# Check tables
print("\n" + "="*70)
print("TABLE ANALYSIS")
print("="*70)

tables_in_html = soup.find_all('table')
print(f"\nTotal tables in HTML: {len(tables_in_html)}")
print(f"Total tables in WORD: 29")

if tables_in_html:
    print(f"\nFirst table in HTML (row 0, cell 0): {tables_in_html[0].find('tr').find('td').get_text(strip=True)[:60]}")

# Check precautionary statements
print("\n" + "="*70)
print("PRECAUTIONARY STATEMENTS (P-Sätze)")
print("="*70)

p_statements_html = [t for t in html_texts if re.match(r'^P\d{3}', t)]
print(f"\nP-Statements found in HTML: {len(p_statements_html)}")
for ps in p_statements_html[:5]:
    print(f"  - {ps[:70]}")

# Formatting check
print("\n" + "="*70)
print("FORMATTING ELEMENTS CHECK")
print("="*70)

has_bold = bool(soup.find('b'))
has_strong = bool(soup.find('strong'))
has_underline = bool(soup.find('u'))

print(f"\n✓ Bold elements (<b>): {has_bold}")
print(f"✓ Strong elements (<strong>): {has_strong}")
print(f"✓ Underline elements (<u>): {has_underline}")

# GHS pictograms
ghs_imgs = soup.find_all('img', src=re.compile(r'ghs|pictogram', re.I))
print(f"✓ GHS pictogram images: {len(ghs_imgs)}")

print("\n" + "="*70)
