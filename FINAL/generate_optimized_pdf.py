from weasyprint import HTML, CSS
from pathlib import Path

html_path = Path('importer_output.html')
pdf_path = Path('test_export_optimized.pdf')

# Render PDF
HTML(str(html_path)).write_pdf(str(pdf_path))

print(f"✓ PDF generated: {pdf_path.name}")
print(f"✓ Size: {pdf_path.stat().st_size / 1024:.1f} KB")
