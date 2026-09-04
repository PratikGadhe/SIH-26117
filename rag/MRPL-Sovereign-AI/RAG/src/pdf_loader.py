import pymupdf
import pytesseract
from pdf2image import convert_from_path


def extract_text_from_pdf(pdf_path):
    document = pymupdf.open(pdf_path)

    pages_text = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text().strip()

        # If the PDF page has normal selectable text
        if text:
            pages_text.append(
                f"[Page {page_number}]\n{text}"
            )

        # If the page is scanned/image-based
        else:
            print(f"OCR processing page {page_number}...")

            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number
            )

            ocr_text = pytesseract.image_to_string(images[0]).strip()

            pages_text.append(
                f"[Page {page_number}]\n{ocr_text}"
            )

    document.close()

    return "\n\n".join(pages_text)


if __name__ == "__main__":
    pdf_path = r"C:\SIH\SIH-26117\rag\MRPL-Sovereign-AI\RAG\documents\Getting started with OneDrive.pdf"

    text = extract_text_from_pdf(pdf_path)

    print(text)