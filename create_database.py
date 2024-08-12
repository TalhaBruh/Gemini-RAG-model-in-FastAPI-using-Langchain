# import logging
# from langchain_community.document_loaders import DirectoryLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.schema import Document
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma
# import openai 
# from dotenv import load_dotenv
# import os
# import shutil
# from pymongo import MongoClient

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Load environment variables. Assumes that project contains .env file with API keys
# load_dotenv()

# # Set OpenAI API key 
# openai.api_key = os.environ['OPENAI_API_KEY']

# CHROMA_PATH = "chroma"
# MONGO_URI = os.environ['MONGO_URI']
# DATABASE_NAME = "document_db"
# COLLECTION_NAME = "documents"

# client = MongoClient(MONGO_URI)
# db = client[DATABASE_NAME]
# collection = db[COLLECTION_NAME]

# def main():
#     try:
#         logger.info("Starting database update...")
#         generate_data_store()
#         logger.info("Database updated successfully.")
#     except Exception as e:
#         logger.error(f"Error updating database: {str(e)}")
#     finally:
#         logger.info("Exiting script.")

# def generate_data_store():
#     documents = load_documents()
#     chunks = split_text(documents)
#     save_to_chroma(chunks)

# def load_documents():
#     documents = []
#     for doc in collection.find():
#         documents.append(Document(page_content=doc["page_content"], metadata=doc["metadata"]))
#     logger.info(f"Loaded {len(documents)} documents from MongoDB.")
#     return documents

# def split_text(documents: list[Document]):
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=500,
#         chunk_overlap=250,
#         length_function=len,
#         add_start_index=True,
#     )
#     chunks = text_splitter.split_documents(documents)
#     logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks.")

#     document = chunks[10]
#     logger.debug(document.page_content)
#     logger.debug(document.metadata)

#     return chunks

# def save_to_chroma(chunks: list[Document]):
#     # Clear out the database first.
#     if os.path.exists(CHROMA_PATH):
#         shutil.rmtree(CHROMA_PATH)
#         logger.info(f"Cleared existing Chroma database at {CHROMA_PATH}.")

#     # Create a new DB from the documents.
#     db = Chroma.from_documents(
#         chunks, OpenAIEmbeddings(), persist_directory=CHROMA_PATH
#     )
#     db.persist()
#     logger.info(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")

# if __name__ == "__main__":
#     main()

import logging
from colorlog import ColoredFormatter
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.schema import Document
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer
import openai 
from dotenv import load_dotenv
import os
import shutil
from pymongo import MongoClient
import tiktoken
from datetime import datetime

# Configure logging with colorlog
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)s:%(name)s:%(message)s",  # Fixed format string
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Load environment variables. Assumes that project contains .env file with API keys
load_dotenv()

CHROMA_PATH = "chroma"
MONGO_URI = os.environ['MONGO_URI']
DATABASE_NAME = "document_db"
COLLECTION_NAME = "documents"
TOKEN_LOG_FILE = "token_log.txt"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

class SentenceTransformerEmbeddings:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: list[Document]):
        print("Embedding documents...")
        return [self.model.encode(doc).tolist() for doc in documents]

def main():
    try:
        logger.info("Starting database update...")
        generate_data_store()
        logger.info("Database updated successfully.")
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
    finally:
        logger.info("Exiting script.")

def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)

def load_documents():
    documents = []
    for doc in collection.find():
        # Log the raw data coming from the database
        # logger.info(f"Raw document from MongoDB: {doc}")
        
        # Ensure the document is correctly converted from JSON to Document object
        if isinstance(doc, dict) and "page_content" in doc and "metadata" in doc:
            
            documents.append(Document(page_content=doc["page_content"], metadata=doc["metadata"]))
        else:
            logger.warning(f"Skipping invalid document: {doc}")
    # print(documents[0])
    logger.info(f"Loaded {len(documents)} documents from MongoDB.")
    return documents

def split_text(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=250,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    logger.info(type(chunks[0]))
    # Check the type of each chunk
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, Document):
            logger.debug(f"Chunk {i}: Document content: {chunk.page_content[:50]}")
        else:
            logger.error(f"Chunk {i} is not a Document object: {chunk}")
            # Convert chunk back to Document if needed
            chunks[i] = Document(page_content=str(chunk), metadata={})
    # print(chunks[2])
    return chunks

# def log_token_count(documents):
#     encoding = tiktoken.encoding_for_model("gpt-3.5")
#     total_tokens = sum(len(encoding.encode(doc.page_content)) for doc in documents)

#     with open(TOKEN_LOG_FILE, "a") as log_file:
#         log_file.write(f"{datetime.now()}: Total Tokens: {total_tokens}\n")



def save_to_chroma(chunks):
    # Validate chunks before proceeding

    for i, chunk in enumerate(chunks):
        if not isinstance(chunk, Document):
            logger.error(f"Invalid chunk at index {i}: {chunk}")
            return

        logger.debug(f"Chunk {i} - page_content: {chunk.page_content[:50]}, metadata: {chunk.metadata}")

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logger.info(f"Cleared existing Chroma database at {CHROMA_PATH}.")

    embedding_model = SentenceTransformerEmbeddings('sentence-transformers/all-MiniLM-L6-v2')
    try:
        # print("Creating Chroma database...",chunks)
        # print(chunks[0].page_content)
        db = Chroma.from_documents(
            chunks, embedding_model, persist_directory=CHROMA_PATH
        )
        db.persist()
        logger.info(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")
    except Exception as e:
        logger.error(f"Failed to create Chroma database: {str(e)}")

if __name__ == "__main__":
    main()