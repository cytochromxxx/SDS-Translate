import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

docx = Path.home() / 'Downloads' / 'MB_SDS_Word_PERFEKT.docx'

with zipfile.ZipFile(docx) as z:
    root = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    print('=== SECTION STRUCTURE WITH FORMATTING ===\n')
    
    for p in root.findall('.//w:p', ns):
        text = ''.join(t.text or '' for t in p.findall('.//w:t', ns))
        if text.strip() and ('SECTION' in text or text.startswith('Product') or 'Trade name' in text or 'Classification' in text):
            # Check style
            pPr = p.find('w:pPr', ns)
            style_elem = pPr.find('w:pStyle', ns) if pPr is not None else None
            style = style_elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') if style_elem is not None else 'Normal'
            
            # Check bold/italic
            rPr_list = p.findall('.//w:rPr', ns)
            has_bold = any(r.find('w:b', ns) is not None for r in rPr_list)
            
            bold_text = "BOLD" if has_bold else ""
            print(f'[{style}] {bold_text} {text[:70]}')

print('\n=== TABLE STRUCTURE FROM SECTION 2 ===\n')
tables = root.findall('.//w:tbl', ns)
print(f'Total tables: {len(tables)}')

if len(tables) > 0:
    first_table = tables[0]
    rows = first_table.findall('.//w:tr', ns)
    print(f'First table rows: {len(rows)}')
    
    for i, row in enumerate(rows[:3]):
        cells = row.findall('.//w:tc', ns)
        print(f'  Row {i}: {len(cells)} cells')
        for j, cell in enumerate(cells[:2]):
            cell_text = ''.join(t.text or '' for t in cell.findall('.//w:t', ns))
            print(f'    Cell {j}: {cell_text[:50]}')
