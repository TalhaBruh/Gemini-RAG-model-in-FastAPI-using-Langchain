from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from query_data import get_response
import os
import fitz  # PyMuPDF
from pymongo import MongoClient
from dotenv import load_dotenv
import subprocess
import logging
import shutil
from fastapi.staticfiles import StaticFiles

load_dotenv()

# Initialize the main FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Allow all origins for simplicity, but you should restrict this in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query_text: str
    session_id: str

@app.post("/ask")
def ask_question(request: QueryRequest):
    response = get_response(request.query_text, request.session_id)
    if response == "Unable to find matching results.":
        raise HTTPException(status_code=404, detail=response)
    return {"response": response}

UPLOAD_FOLDER = 'uploads'
MONGO_URI = os.environ['MONGO_URI']
DATABASE_NAME = "document_db"
COLLECTION_NAME = "documents"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def store_documents(file_path, filename):
    with fitz.open(file_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf.load_page(page_num)
            text = page.get_text()
            document = {
                "page_content": text,
                "metadata": {"source": filename, "page": page_num}
            }
            collection.insert_one(document)
    logger.info(f"Document {filename} stored in MongoDB.")

@app.post("/upload/")
async def upload_files(files: list[UploadFile] = File(...)):
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        store_documents(file_path, file.filename)
    return {"filenames": [file.filename for file in files]}

@app.post("/update-database/")
async def update_database():
    try:
        logger.info("Starting database update...")
        result = subprocess.run(["python3", "create_database.py"], capture_output=True, text=True)
        logger.info(f"Subprocess result: {result}")
        if result.returncode != 0:
            logger.error(f"Error updating database: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Error updating database: {result.stderr}")
        return {"detail": "Database updated successfully."}
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear-data/")
async def clear_data():
    try:
        # Clear MongoDB collection
        collection.delete_many({})
        logger.info("MongoDB collection cleared.")

        # Delete all files in uploads/ directory
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        logger.info("Uploads directory cleared.")

                # Delete files inside chroma/ directory
        chroma_dir = 'chroma'
        if os.path.exists(chroma_dir):
            for filename in os.listdir(chroma_dir):
                file_path = os.path.join(chroma_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}. Reason: {e}")
            logger.info("Files inside Chroma directory deleted.")

        return {"detail": "All data cleared successfully."}
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def main():
    with open("index.html", "r") as file:
        content = file.read()
    return HTMLResponse(content=content)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)