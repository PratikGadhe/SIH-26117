import os
import zipfile
import xml.etree.ElementTree as ET
import pymupdf


def extract_pages_from_pdf(pdf_path):
    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text().strip()

        if text:
            pages.append({
                "page": page_number,
                "text": text
            })

    document.close()

    return pages


def extract_pages_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as file:
        text = file.read().strip()

    if not text:
        return []

    return [{
        "page": 1,
        "text": text
    }]


def extract_pages_from_docx(docx_path):
    with zipfile.ZipFile(docx_path, "r") as docx_zip:

        xml_content = docx_zip.read("word/document.xml")

    root = ET.fromstring(xml_content)

    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }

    paragraphs = []

    for paragraph in root.findall(".//w:p", namespace):

        words = []

        for text_element in paragraph.findall(".//w:t", namespace):
            if text_element.text:
                words.append(text_element.text)

        paragraph_text = "".join(words).strip()

        if paragraph_text:
            paragraphs.append(paragraph_text)

    full_text = "\n".join(paragraphs)

    if not full_text:
        return []

    return [{
        "page": 1,
        "text": full_text
    }]


def split_text_into_chunks(text, chunk_size=800, overlap=100):
    words = text.split()

    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:

        word_length = len(word) + 1

        if current_length + word_length > chunk_size:

            chunks.append(" ".join(current_chunk))

            overlap_words = []
            overlap_length = 0

            for previous_word in reversed(current_chunk):

                if overlap_length + len(previous_word) + 1 > overlap:
                    break

                overlap_words.insert(0, previous_word)
                overlap_length += len(previous_word) + 1

            current_chunk = overlap_words
            current_length = overlap_length

        current_chunk.append(word)
        current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def create_document_chunks(file_path):

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        pages = extract_pages_from_pdf(file_path)

    elif extension == ".txt":
        pages = extract_pages_from_txt(file_path)

    elif extension == ".docx":
        pages = extract_pages_from_docx(file_path)

    else:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    all_chunks = []

    for page in pages:

        chunks = split_text_into_chunks(page["text"])

        for chunk in chunks:

            all_chunks.append({
                "text": chunk,
                "page": page["page"]
            })

    return all_chunks

if __name__ == "__main__":

    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "documents",
        "Getting started with OneDrive.pdf"
    )

    chunks = create_document_chunks(pdf_path)

    print("Chunks created:", len(chunks))

    for i, chunk in enumerate(chunks):

        print(f"\n--- Chunk {i + 1} ---")
        print("Page:", chunk["page"])
        print("Content:")
        print(chunk["text"])