from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.cloud import storage
from google.cloud import firestore
import os
from datetime import datetime

# Initialize FastAPI
app = FastAPI(title="D&D DM Assistant API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GCP clients
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "shattared-meridian-assistant")
LOCATION = "us-central1"

# Initialize GenAI client with Vertex AI mode (no API key needed in Cloud Shell)
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

MODEL_NAME = "publishers/google/models/gemini-2.5-flash"

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    context_type: str = "general"

class ChatResponse(BaseModel):
    response: str
    timestamp: str

@app.get("/")
async def root():
    return {
        "service": "D&D DM Assistant",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for DM assistance
    """
    try:
        system_prompt = f"""You are an expert Dungeon Master assistant for Dungeons & Dragons 5th Edition.
Context Type: {request.context_type}

Help the DM with creative storytelling, rule clarifications, NPC generation, 
encounter balancing, and campaign management. Be concise but helpful."""

        full_prompt = f"{system_prompt}\n\nDM Question: {request.message}"
        
        # Create content using the new SDK
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=4096
        )
        
        # Generate response
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )
        
        response_text = response.text
        
        # Store interaction in Firestore
        interaction_ref = db.collection('chat_history').document()
        interaction_ref.set({
            'message': request.message,
            'response': response_text,
            'context_type': request.context_type,
            'timestamp': datetime.utcnow()
        })
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-npc")
async def generate_npc(
    race: str = "random",
    character_class: str = "random",
    alignment: str = "random"
):
    """
    Generate a detailed NPC
    """
    try:
        prompt = f"""Generate a detailed D&D 5e NPC with the following:
Race: {race}
Class: {character_class}
Alignment: {alignment}

Include: name, physical description, personality traits, background hook, 
stat block (simplified), and a quest they might offer. Format as structured text."""

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=4096
        )
        
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )
        
        response_text = response.text
        
        # Store NPC in Firestore
        npc_ref = db.collection('npcs').document()
        npc_ref.set({
            'content': response_text,
            'race': race,
            'class': character_class,
            'alignment': alignment,
            'created_at': datetime.utcnow()
        })
        
        return {
            "npc": response_text,
            "id": npc_ref.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaign/lore")
async def get_campaign_lore():
    """
    Retrieve all campaign lore entries
    """
    try:
        lore_ref = db.collection('campaign_lore')
        docs = lore_ref.stream()
        
        lore_entries = []
        for doc in docs:
            entry = doc.to_dict()
            entry['id'] = doc.id
            lore_entries.append(entry)
        
        return {"lore": lore_entries}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/campaign/lore")
async def add_campaign_lore(title: str, content: str, category: str = "general"):
    """
    Add new campaign lore entry
    """
    try:
        lore_ref = db.collection('campaign_lore').document()
        lore_ref.set({
            'title': title,
            'content': content,
            'category': category,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return {
            "message": "Lore entry added successfully",
            "id": lore_ref.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# RAG Rulebook Search
from app.rag.pdf_processor import PDFProcessor

# Initialize RAG processor (add after other initializations)
try:
    rag_processor = PDFProcessor(PROJECT_ID)
except Exception as e:
    print(f"Warning: RAG processor initialization failed: {e}")
    rag_processor = None

@app.post("/search-rulebooks")
async def search_rulebooks(query: str, n_results: int = 5):
    """Search D&D rulebooks using RAG"""
    try:
        if not rag_processor:
            raise HTTPException(status_code=503, detail="Rulebook search not available")
        
        results = rag_processor.search(query, n_results=n_results)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat-with-rulebooks")
async def chat_with_rulebooks(message: str, context_type: str = "rules"):
    """Chat with rulebook context"""
    try:
        if not rag_processor:
            raise HTTPException(status_code=503, detail="Rulebook search not available")
        
        # Search rulebooks for relevant context
        rulebook_results = rag_processor.search(message, n_results=3)
        
        # Build prompt with rulebook context
        context_text = "\n\n".join([
            f"[{r['source']}, Page {r['page_number']}]: {r['text']}" 
            for r in rulebook_results
        ])
        
        system_prompt = f"""You are a D&D 5e rules expert. Use the following rulebook excerpts to answer the question accurately.

Rulebook Context:
{context_text}

Question: {message}

Provide a clear answer based on the rulebook information. Cite the source and page number."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])]
        
        config = types.GenerateContentConfig(
            temperature=0.3,
            top_p=0.95,
            max_output_tokens=2048
        )
        
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )
        
        return {
            "response": response.text,
            "sources": rulebook_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
