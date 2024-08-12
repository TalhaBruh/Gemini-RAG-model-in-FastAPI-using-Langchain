# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from query_data import get_response
# from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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

@app.post("/ask")
def ask_question(request: QueryRequest):
    response = get_response(request.query_text)
    if response == "Unable to find matching results.":
        raise HTTPException(status_code=404, detail=response)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)