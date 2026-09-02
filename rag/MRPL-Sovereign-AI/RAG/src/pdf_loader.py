import pymupdf


def extract_text_from_pdf(pdf_path):
    document = pymupdf.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


if __name__ == "__main__":
    pdf_path = "C:\MRPL-Sovereign-AI\RAG\documents\Getting started with OneDrive.pdf"

    text = extract_text_from_pdf(pdf_path)

    print(text)