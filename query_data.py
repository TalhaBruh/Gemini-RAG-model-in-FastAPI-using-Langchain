import argparse
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import time
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
import google.generativeai as genai

load_dotenv()  # Load environment variables from .env file
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are an AI assistant named John. You are friendly and helpful. Carry on a natural conversation and answer the user's questions based on the context and the conversation history.

{context}

---
Question: {question}
Answer: 
"""

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["chat_db"]
collection = db["chat_history"]

def get_response(query_text, session_id):
    try:
        # Prepare the DB.
        embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_model)

        # Retrieve conversation history
        history = collection.find({"session_id": session_id}).sort("timestamp", 1)
        conversation_history = "\n".join([f"User: {entry['query_text']}\nJohn: {entry['response_text']}" for entry in history])
        print(conversation_history)
        # Append conversation history to context
        context_text = conversation_history if conversation_history else "No previous conversation."

        # Search the DB for relevant context
        results = db.similarity_search_with_relevance_scores(query_text, k=5)
        if len(results) > 0 and results[0][1] >= 0.2:
            retrieved_context = "\n".join([doc.page_content for doc, _score in results])
            context_text += f"\n\nAdditional context:\n{retrieved_context}"

        # Format the prompt with context and question
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(context=context_text, question=query_text)

        # Generate the response
        response = model.generate_content(prompt)
        response_text = response.candidates[0].content.parts[0].text
        
        # Save chat to MongoDB
        chat_entry = {
            "session_id": session_id,
            "query_text": query_text,
            "response_text": response_text,
            "timestamp": time.time()
        }
        collection.insert_one(chat_entry)
        
        return response_text

    except Exception as e:
        print(f"Error occurred: {e}.")
        raise Exception("An error occurred while processing the request. Please check your quota and try again later.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("session_id", type=str, help="The session ID.")
    args = parser.parse_args()
    query_text = args.query_text
    session_id = args.session_id

    response = get_response(query_text, session_id)
    print(response)

if __name__ == "__main__":
    main()
