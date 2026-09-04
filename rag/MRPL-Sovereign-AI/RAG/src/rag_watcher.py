import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from document_processor import process_document


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")


class DocumentHandler(FileSystemEventHandler):

    def process_file(self, file_path):
        if not file_path.lower().endswith((".pdf", ".txt", ".docx")):
            return

        print(f"\nDocument change detected: {os.path.basename(file_path)}")

        try:
            process_document(file_path)
            print("Document processed successfully.")
        except Exception as e:
            print(f"Error processing document: {e}")

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            time.sleep(1)
            self.process_file(event.src_path)


if __name__ == "__main__":

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

    event_handler = DocumentHandler()
    observer = Observer()

    observer.schedule(
        event_handler,
        DOCUMENTS_DIR,
        recursive=False
    )

    observer.start()

    print("RAG Dynamic Watcher Started.")
    print(f"Watching: {DOCUMENTS_DIR}")
    print("Add or modify a PDF, TXT, or DOCX file to test.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping RAG watcher...")
        observer.stop()

    observer.join()