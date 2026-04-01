import pdfplumber

try:
    with pdfplumber.open('SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf') as pdf:
        for i, p in enumerate(pdf.pages):
            images = p.images
            if images:
                print(f"Page {i} has {len(images)} images.")
                for idx, img in enumerate(images):
                    print(f"  {idx}: {img['x0']}, {img['top']}, {img['x1']}, {img['bottom']}")
except Exception as e:
    print(f"Error: {e}")
