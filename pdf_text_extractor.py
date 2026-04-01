import pdfplumber
import os

def extract_text_from_pdf(pdf_path, txt_path):
    if not os.path.exists(pdf_path):
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error: PDF file not found at {pdf_path}")
        return
    try:
        with pdfplumber.open(pdf_path) as pdf:
            with open(txt_path, 'w', encoding='utf-8') as f:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        f.write(text)
                    f.write('\\n--- Page Break ---\\n')
    except Exception as e:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error extracting text from {pdf_path}: {e}")

if __name__ == '__main__':
    extract_text_from_pdf('SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf', 'original.txt')
    extract_text_from_pdf('x.pdf', 'generated.txt')
    print("Text extraction complete. Check original.txt and generated.txt")
