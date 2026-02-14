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

@app.post("/generate-npc-enhanced")
async def generate_npc_enhanced(
    race: str = "random",
    character_class: str = "random",
    alignment: str = "random",
    level: int = None,
    cr: str = None,
    npc_type: str = "character",  # "character" or "creature"
    role: str = "neutral",  # ally, enemy, quest_giver, merchant, neutral
    location_id: str = None,
    faction_id: str = None
):
    """
    Generate a detailed NPC with RAG-enhanced 2024 rules accuracy
    and links to Campaign Lore
    """
    try:
        # Fetch location from Campaign Lore if provided
        location_info = ""
        if location_id:
            try:
                loc_doc = db.collection('campaign_lore').document(location_id).get()
                if loc_doc.exists:
                    loc_data = loc_doc.to_dict()
                    location_info = f"\nLocation: {loc_data.get('title', 'Unknown')}\nLocation Details: {loc_data.get('content', '')}"
            except:
                pass
        
        # Fetch faction from Campaign Lore if provided
        faction_info = ""
        if faction_id:
            try:
                fac_doc = db.collection('campaign_lore').document(faction_id).get()
                if fac_doc.exists:
                    fac_data = fac_doc.to_dict()
                    faction_info = f"\nFaction: {fac_data.get('title', 'Unknown')}\nFaction Details: {fac_data.get('content', '')}"
            except:
                pass
        
        
        # Different RAG searches based on NPC type
        creature_stats = ""
        race_rules = ""
        class_rules = ""
        
        role_descriptions = {
            "ally": "This creature is a potential ally who can help the party.",
            "enemy": "This creature is an antagonist or enemy with clear motivations for opposing the party.",
            "quest_giver": "This creature offers quests and missions.",
            "merchant": "This creature is a merchant or trader.",
            "neutral": "This creature has its own agenda that may or may not align with the party."
        }
        role_context = role_descriptions.get(role, role_descriptions["neutral"])
        
        if npc_type == "creature":
            # For creatures, search Monster Manual for stat blocks
            if race != "random" and rag_processor:
                try:
                    creature_results = rag_processor.search(f"{race} monster stat block", n_results=3)
                    if creature_results:
                        creature_stats = "\n\nMonster Manual Reference:\n"
                        for r in creature_results:
                            creature_stats += f"- {r.get('text', '')[:800]}...\n"
                except:
                    pass
            
            if cr and rag_processor:
                try:
                    cr_results = rag_processor.search(f"CR {cr} monster abilities actions", n_results=2)
                    if cr_results:
                        creature_stats += "\n\nSimilar CR Creatures:\n"
                        for r in cr_results:
                            creature_stats += f"- {r.get('text', '')[:500]}...\n"
                except:
                    pass
            
            level_cr_text = f"Challenge Rating (CR): {cr if cr else 'appropriate for the creature'}"
            
            prompt = f"""Generate a detailed D&D 5e CREATURE/MONSTER based on Monster Manual format.

**Basic Information:**
- Creature Type: {race}
- Category: {character_class if character_class else 'N/A'}
- Alignment: {alignment}
- {level_cr_text}
- Role: {role.replace('_', ' ').title()}

**Role Context:** {role_context}
{location_info}
{faction_info}
{creature_stats}

**Generate a MONSTER STAT BLOCK in official D&D 5e Monster Manual format:**

1. **Creature Name**

2. **Size, Type, Alignment** (e.g., Medium undead, neutral evil)

3. **Armor Class** (with armor type)

4. **Hit Points** (with hit dice, e.g., 45 (6d10 + 12))

5. **Speed** (walk, fly, swim, burrow, climb)

6. **Ability Scores Table:**
   STR | DEX | CON | INT | WIS | CHA
   (scores with modifiers)

7. **Saving Throws** (if proficient)

8. **Skills** (if proficient)

9. **Damage Resistances/Immunities**

10. **Condition Immunities**

11. **Senses** (darkvision, passive Perception, etc.)

12. **Languages**

13. **Challenge** (CR with XP)

14. **Traits** (special abilities like Pack Tactics, Keen Senses)

15. **Actions** (attacks with to-hit bonus and damage)

16. **Reactions** (if any)

17. **Legendary Actions** (if CR 10+)

18. **Description** (appearance, behavior, habitat)

19. **Tactics** (how it fights)

20. **Plot Hooks** (ways to use in adventures)

Format as an official Monster Manual stat block."""

        else:
            # For characters, search PHB for race and class info
            if race != "random" and rag_processor:
                try:
                    race_results = rag_processor.search(f"{race} race traits features 2024", n_results=2)
                    if race_results:
                        race_rules = "\n\nRelevant Race Rules from 2024 PHB:\n"
                        for r in race_results:
                            race_rules += f"- {r.get('text', '')[:500]}...\n"
                except:
                    pass
            
            if character_class != "random" and rag_processor:
                try:
                    level_text = f"level {level}" if level else ""
                    class_results = rag_processor.search(f"{character_class} class features {level_text} 2024", n_results=2)
                    if class_results:
                        class_rules = "\n\nRelevant Class Rules from 2024 PHB:\n"
                        for r in class_results:
                            class_rules += f"- {r.get('text', '')[:500]}...\n"
                except:
                    pass
            
            level_cr_text = f"Level: {level if level else 'appropriate for the class'}"
            
            prompt = f"""Generate a detailed D&D 5e NPC using the 2024 rules with the following specifications:

**Basic Information:**
- Race: {race}
- Class: {character_class}
- Alignment: {alignment}
- {level_cr_text}
- Type: {npc_type.title()}
- Role: {role.replace('_', ' ').title()}

**Role Context:** {role_context}
{location_info}
{faction_info}
{race_rules}
{class_rules}

**Please generate the NPC with these sections:**

1. **NPC Name:** (creative fantasy name appropriate for the race)
2. **Race:** (include any relevant racial traits from 2024 rules)
3. **Class:** (with subclass if appropriate)
4. **Alignment:** 
5. **Level/CR:** 
6. **Role:** {role.replace('_', ' ').title()}
7. **Location:** (where they can be found)
8. **Faction Affiliation:** (if any)
9. **Physical Description:** (detailed appearance, distinguishing features)
10. **Voice Suggestions:** (accent, speech patterns, mannerisms)
11. **Personality Traits:** (3-4 distinct traits)
12. **Background:** (history, motivations, goals)
13. **Stat Block (Simplified):**
    - STR, DEX, CON, INT, WIS, CHA scores
    - Armor Class, Hit Points
    - Key skills and saving throws
14. **Abilities & Features:** (class features, racial traits from 2024 PHB)
15. **Actions:** (attacks, spells, or special actions)
16. **Roleplaying Tips:** (how to portray this NPC)
17. **Plot Hooks:** (2-3 ways to involve this NPC in adventures)

Format the response with clear headers and organized sections."""


        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=0.9,
            top_p=0.95,
            max_output_tokens=8192
        )
        
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )
        
        response_text = response.text
        
        # Store NPC in Firestore with all metadata
        npc_ref = db.collection('npcs').document()
        npc_data = {
            'content': response_text,
            'race': race,
            'class': character_class,
            'alignment': alignment,
            'level': level,
            'cr': cr,
            'npc_type': npc_type,
            'role': role,
            'location_id': location_id,
            'faction_id': faction_id,
            'created_at': datetime.utcnow()
        }
        npc_ref.set(npc_data)
        
        return {
            "npc": response_text,
            "id": npc_ref.id,
            "metadata": {
                "race": race,
                "class": character_class,
                "alignment": alignment,
                "level": level,
                "cr": cr,
                "npc_type": npc_type,
                "role": role,
                "location_id": location_id,
                "faction_id": faction_id
            }
        }
        
    except Exception as e:
        print(f"NPC Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/npcs")
async def get_all_npcs():
    """Get all saved NPCs"""
    try:
        npcs_ref = db.collection('npcs')
        docs = npcs_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        npcs = []
        for doc in docs:
            npc = doc.to_dict()
            npc['id'] = doc.id
            npcs.append(npc)
        
        return {"npcs": npcs, "count": len(npcs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/npcs/{npc_id}")
async def get_npc(npc_id: str):
    """Get a single NPC by ID"""
    try:
        npc_ref = db.collection('npcs').document(npc_id)
        doc = npc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        npc = doc.to_dict()
        npc['id'] = doc.id
        return npc
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/npcs/{npc_id}")
async def delete_npc(npc_id: str):
    """Delete an NPC"""
    try:
        npc_ref = db.collection('npcs').document(npc_id)
        doc = npc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        npc_ref.delete()
        return {"message": "NPC deleted successfully", "id": npc_id}
        
    except HTTPException:
        raise
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


@app.put("/campaign/lore/{lore_id}")
async def update_campaign_lore(lore_id: str, title: str = None, content: str = None, category: str = None):
    """
    Update an existing campaign lore entry
    """
    try:
        lore_ref = db.collection('campaign_lore').document(lore_id)
        doc = lore_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Lore entry not found")
        
        update_data = {'updated_at': datetime.utcnow()}
        if title is not None:
            update_data['title'] = title
        if content is not None:
            update_data['content'] = content
        if category is not None:
            update_data['category'] = category
        
        lore_ref.update(update_data)
        
        return {"message": "Lore entry updated successfully", "id": lore_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/campaign/lore/{lore_id}")
async def delete_campaign_lore(lore_id: str):
    """
    Delete a campaign lore entry
    """
    try:
        lore_ref = db.collection('campaign_lore').document(lore_id)
        doc = lore_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Lore entry not found")
        
        lore_ref.delete()
        
        return {"message": "Lore entry deleted successfully", "id": lore_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaign/lore/search")
async def search_campaign_lore(query: str, category: str = None):
    """
    Search campaign lore entries by text or category
    """
    try:
        lore_ref = db.collection('campaign_lore')
        docs = lore_ref.stream()
        
        results = []
        query_lower = query.lower()
        
        for doc in docs:
            entry = doc.to_dict()
            entry['id'] = doc.id
            
            # Filter by category if specified
            if category and entry.get('category') != category:
                continue
            
            # Search in title and content
            if (query_lower in entry.get('title', '').lower() or 
                query_lower in entry.get('content', '').lower()):
                results.append(entry)
        
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaign/lore/categories")
async def get_lore_categories():
    """
    Get all unique categories from campaign lore
    """
    try:
        lore_ref = db.collection('campaign_lore')
        docs = lore_ref.stream()
        
        categories = set()
        for doc in docs:
            entry = doc.to_dict()
            if 'category' in entry:
                categories.add(entry['category'])
        
        return {"categories": list(categories)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaign/lore/{lore_id}")
async def get_single_lore(lore_id: str):
    """
    Get a single campaign lore entry by ID
    """
    try:
        lore_ref = db.collection('campaign_lore').document(lore_id)
        doc = lore_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Lore entry not found")
        
        entry = doc.to_dict()
        entry['id'] = doc.id
        return entry
        
    except HTTPException:
        raise
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

# Import Google Drive service
from app.services.google_drive_service import GoogleDriveService
from app.utils.npc_parser import parse_npc_text

# Initialize Google Drive service (add after other initializations)
try:
    drive_service = GoogleDriveService(PROJECT_ID)
except Exception as e:
    print(f"Warning: Google Drive service initialization failed: {e}")
    drive_service = None

@app.post("/generate-npc-to-drive")
async def generate_npc_to_drive(
    race: str = "random",
    character_class: str = "random",
    alignment: str = "random"
):
    """Generate an NPC and save it to Google Drive"""
    try:
        if not drive_service:
            raise HTTPException(status_code=503, detail="Google Drive service not available")
        
        # Template and folder IDs
        TEMPLATE_ID = "1mxeHjGBSAHXAWbj_hmSZr4ACiJBAszkExB9cIv37s2s"
        FOLDER_ID = "1s9uJh8y864acY1yAv20ughDqwztq6ao3"
        
        # Generate NPC with structured output
        prompt = f"""Generate a detailed D&D 5e NPC with these parameters:
Race: {race}
Class: {character_class}
Alignment: {alignment}

Format EXACTLY like this:

NPC Name: [Full name]
Race: [Specific race]
Class: [Class and subclass]
Alignment: [Alignment]
Level: [Level number]
World Placement: [2-3 sentences about location and role]

Physical Description: [2-3 sentences describing appearance]

Voice Suggestions: [How they speak]

Personality Traits:
*   **[Trait 1]:** [Description]
*   **[Trait 2]:** [Description]

Background: [2-3 paragraphs about history]

Str: [8-18]
Dex: [8-18]
Con: [8-18]
Int: [8-18]
Wis: [8-18]
Cha: [8-18]

Saving Throws: [Proficiencies with modifiers]
Skills: [Proficiencies with modifiers]
Senses: [Passive Perception and special senses]
Languages: [Languages known]

Abilities:
*   **[Ability 1]:** [Description]
*   **[Ability 2]:** [Description]

Actions:
*   **[Action 1]:** [Attack with bonus and damage]

Use this EXACT format."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        
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
        
        npc_text = response.text
        
        # Parse the generated NPC data
        npc_data = parse_npc_text(npc_text)
        
        # Create document title
        npc_name = npc_data.get('name', 'Unnamed NPC')
        doc_title = f"{npc_name} - NPC"
        
        # Copy template
        new_doc_id = drive_service.copy_template(TEMPLATE_ID, doc_title, FOLDER_ID)
        
        if not new_doc_id:
            raise HTTPException(status_code=500, detail="Failed to create document")
        
        # Fill template
        success = drive_service.fill_npc_template(new_doc_id, npc_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fill template")
        
        # Get document URL
        doc_url = drive_service.get_document_url(new_doc_id)
        
        # Store in Firestore
        npc_ref = db.collection('npcs').document()
        npc_ref.set({
            'name': npc_name,
            'race': race,
            'class': character_class,
            'alignment': alignment,
            'google_doc_id': new_doc_id,
            'google_doc_url': doc_url,
            'created_at': datetime.utcnow()
        })
        
        return {
            "npc_name": npc_name,
            "google_doc_url": doc_url,
            "firestore_id": npc_ref.id,
            "message": "NPC created successfully in Google Drive!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/test-npc-generation")
async def test_npc_generation(race: str = "elf", character_class: str = "wizard"):
    """Test NPC generation and return raw output"""
    try:
        prompt = f"""Generate a detailed D&D 5e NPC with the following parameters:
Race: {race}
Class: {character_class}

Format your response EXACTLY like this example:

NPC Name: Elara Meadowbrook
Race: High Elf
Class: Wizard (School of Abjuration)
Alignment: Neutral Good
Level: 5
World Placement: Elara serves as the principal archivist and magical consultant within the Grand Library of Silverhaven.

Physical Description: Elara possesses the characteristic slender grace of a high elf, standing at 5'6" with an elegant posture.

Voice Suggestions: Her voice is soft, melodic, and precise.

Personality Traits:
*   **Intellectually Curious:** Driven by an insatiable thirst for knowledge.
*   **Methodical and Prudent:** Approaches problems with careful consideration.

Background: Elara was raised in a reclusive elven conclave known for its ancient magical libraries.

Str: 8
Dex: 16
Con: 13
Int: 16
Wis: 12
Cha: 10

Saving Throws: Intelligence (+6), Wisdom (+3)
Skills: Arcana (+6), History (+6)
Senses: Passive Perception 13, Darkvision 60 ft.
Languages: Common, Elvish, Draconic

Abilities:
*   **Fey Ancestry:** Elara has advantage on saving throws.

Actions:
*   **Dagger:** Melee Weapon Attack: +5 to hit.

Use this EXACT format. Do not add extra headers or sections."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        
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
        
        return {"raw_output": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== MAP GENERATOR ==============


@app.post("/generate-map")
async def generate_map(
    description: str,
    rows: int = 20,
    columns: int = 20,
    style: str = "realistic top-down battle map",
    show_grid: bool = True
):
    """Generate a battle map using Vertex AI Imagen with optional grid overlay"""
    try:
        from vertexai.preview.vision_models import ImageGenerationModel
        from PIL import Image
        import io
        import base64
        import uuid
        from google.cloud import storage
        
        # Calculate image size based on grid (70 pixels per square - VTT standard)
        PIXELS_PER_SQUARE = 70
        width = columns * PIXELS_PER_SQUARE
        height = rows * PIXELS_PER_SQUARE
        
        # Imagen generates fixed sizes, so we'll generate and resize
        prompt = f"""Top-down fantasy battle map for D&D tabletop RPG, {style}, seamless texture, no grid lines, no axis lines, no borders.
        
Scene description: {description}

Style requirements:
- Bird's eye view / top-down perspective
- Clear terrain and features visible from above
- Suitable for virtual tabletop (VTT) use
- High detail, clean edges
- Fantasy RPG aesthetic
- NO grid lines, squares, axis lines, rulers, coordinate markers, or borders in the image
- Pure terrain and features only"""

        # Generate image using Imagen
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_few",
            person_generation="dont_allow"
        )
        
        if response.images:
            # Get the generated image
            generated_image = response.images[0]
            image_bytes = generated_image._image_bytes
            
            # Open with PIL for processing
            img = Image.open(io.BytesIO(image_bytes))
            
            # Resize to match grid dimensions
            img = img.resize((width, height), Image.LANCZOS)
            
            # Draw grid if requested
            if show_grid:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                
                # Draw vertical lines
                for x in range(0, width + 1, PIXELS_PER_SQUARE):
                    draw.line([(x, 0), (x, height)], fill=(0, 0, 0, 128), width=1)
                
                # Draw horizontal lines
                for y in range(0, height + 1, PIXELS_PER_SQUARE):
                    draw.line([(0, y), (width, y)], fill=(0, 0, 0, 128), width=1)
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='PNG')
            final_image_bytes = output_buffer.getvalue()
            
            # Convert to base64 for frontend
            base64_image = base64.b64encode(final_image_bytes).decode('utf-8')
            
            # Save to Cloud Storage for persistence
            storage_client = storage.Client()
            bucket = storage_client.bucket("dnd-dm-assistant-web")
            
            # Generate unique filename
            filename = f"maps/map_{uuid.uuid4().hex[:8]}.png"
            blob = bucket.blob(filename)
            blob.upload_from_string(final_image_bytes, content_type="image/png")
            
            # Bucket is already public
            public_url = f"https://storage.googleapis.com/dnd-dm-assistant-web/{filename}"
            
            return {
                "success": True,
                "image_base64": base64_image,
                "image_url": public_url,
                "prompt_used": prompt,
                "grid_size": f"{columns}x{rows}",
                "dimensions": f"{width}x{height}",
                "pixels_per_square": PIXELS_PER_SQUARE
            }
        else:
            return {"success": False, "error": "No image generated"}
            
    except Exception as e:
        print(f"Map generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
