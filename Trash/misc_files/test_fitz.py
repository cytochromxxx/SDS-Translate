import fitz

def extract_icons():
    doc = fitz.open("SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf")
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        if "8.2.2" in text or "Eye/face" in text or "Skin protection" in text:
            print(f"Page {i} might have PPE icons.")
            
            # Find exact coords
            for phrase in ["Eye/face protection", "Skin protection", "Respiratory protection"]:
                rects = page.search_for(phrase)
                if rects:
                    for r in rects:
                        print(f"Found '{phrase}' at {r}")
                        # Icon is usually to the left
                        icon_rect = fitz.Rect(max(0, r.x0 - 50), r.y0 - 5, r.x0 - 5, r.y1 + 15)
                        print(f"Attempting to crop icon at {icon_rect}")
                        pix = page.get_pixmap(clip=icon_rect, matrix=fitz.Matrix(2, 2))
                        pix.save(f"icon_{phrase.replace('/', '_').replace(' ', '_')}.png")

if __name__ == '__main__':
    extract_icons()
