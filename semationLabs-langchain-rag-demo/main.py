from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
import os
import fitz  # PyMuPDF
from pymongo import MongoClient
from dotenv import load_dotenv
import subprocess
import logging

load_dotenv()

app = FastAPI()
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

@app.get("/")
async def main():
    content = """
    <html>
        <head>
            <title>Upload Documents</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f4f4f4;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: #fff;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                h1 {
                    text-align: center;
                }
                .form-group {
                    margin-bottom: 15px;
                }
                label {
                    display: block;
                    margin-bottom: 5px;
                }
                input[type="file"] {
                    width: 100%;
                    padding: 10px;
                    margin-bottom: 10px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                button {
                    display: block;
                    width: 100%;
                    padding: 10px;
                    background: #007BFF;
                    color: #fff;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button:hover {
                    background: #0056b3;
                }
                .response {
                    margin-top: 20px;
                    padding: 10px;
                    background: #e9ecef;
                    border-radius: 4px;
                }
                #loading-spinner {
                    display: none;
                    text-align: center;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Upload PDF Documents</h1>
                <form id="upload-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="files">Select PDF files:</label>
                        <input name="files" type="file" accept=".pdf" multiple>
                    </div>
                    <button type="submit">Upload</button>
                </form>
                <button onclick="updateDatabase()">Update Database</button>
                <div id="loading-spinner">Loading...</div>
                <div class="response" id="response"></div>
            </div>
            <script>
                document.getElementById('upload-form').addEventListener('submit', async function(event) {
                    event.preventDefault();
                    const form = event.target;
                    const formData = new FormData(form);
                    const loadingSpinner = document.getElementById('loading-spinner');
                    const responseDiv = document.getElementById('response');

                    loadingSpinner.style.display = 'block';
                    responseDiv.innerHTML = '';

                    try {
                        const response = await fetch('/upload/', {
                            method: 'POST',
                            body: formData
                        });

                        if (response.ok) {
                            const result = await response.json();
                            responseDiv.innerHTML = `<p>Upload successful: ${result.filenames.join(', ')}</p>`;
                        } else {
                            const errorData = await response.json();
                            responseDiv.innerHTML = `<p>Error: ${errorData.detail}</p>`;
                        }
                    } catch (error) {
                        responseDiv.innerHTML = `<p>An error occurred: ${error.message}</p>`;
                    } finally {
                        loadingSpinner.style.display = 'none';
                    }
                });

                async function updateDatabase() {
                    const responseDiv = document.getElementById('response');
                    const loadingSpinner = document.getElementById('loading-spinner');

                    loadingSpinner.style.display = 'block';
                    responseDiv.innerHTML = '';

                    try {
                        const response = await fetch('/update-database/', {
                            method: 'POST'
                        });

                        if (response.ok) {
                            const data = await response.json();
                            responseDiv.innerHTML = `<p>${data.detail}</p>`;
                        } else {
                            const errorData = await response.json();
                            responseDiv.innerHTML = `<p>Error: ${errorData.detail}</p>`;
                        }
                    } catch (error) {
                        responseDiv.innerHTML = `<p>An error occurred: ${error.message}</p>`;
                    } finally {
                        loadingSpinner.style.display = 'none';
                    }
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)