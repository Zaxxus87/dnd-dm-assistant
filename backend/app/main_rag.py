from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.cloud import storage
from google.cloud import firestore
import os
from datetime import datetime
from typing import Optional, List
from app.rag.pdf_processor import PDFProcessor

app = FastAPI(title="D&D DM Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "shattared-meridian-assistant")
LOCATION = "us-central1"

genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
rag_processor = PDFProcessor(PROJECT_ID)

MODEL_NAME = "publishers/google/models/gemini-2.5-flash"

class ChatRequest(BaseModel):
    message: str
    context_type: str = "general"
    use_rulebooks: bool = False

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    sources: Optional[List[dict]] = None

@app.get("/")
async def root():
    return {"service": "D&D DM Assistant", "status": "online", "version": "2.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/search-rulebooks")
async def search_rulebooks(query: str, n_results: int = 5):
    try:
        results = rag_processor.search(query, n_results=n_results)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
