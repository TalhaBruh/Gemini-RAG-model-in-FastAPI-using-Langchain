# store_documents_in_mongo.py
import os
import fitz  # PyMuPDF
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data/books"  # Ensure this directory contains your PDF files
MONGO_URI = os.environ['MONGO_URI']
DATABASE_NAME = "document_db"
COLLECTION_NAME = "documents"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def store_documents():
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DATA_PATH, filename)
            print(f"Processing document: {filename}")
            with fitz.open(filepath) as pdf:
                for page_num in range(len(pdf)):
                    page = pdf.load_page(page_num)
                    text = page.get_text()
                    document = {
                        "page_content": text,
                        "metadata": {"source": filename, "page": page_num}
                    }
                    collection.insert_one(document)
    print("Documents stored in MongoDB.")

if __name__ == "__main__":
    store_documents()