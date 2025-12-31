import PyPDF2
from typing import List, Dict
import json
import os
from google import genai
from google.genai import types
from google.cloud import storage

class PDFProcessor:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
        
        # Try Cloud Storage first, fallback to local
        self.vector_store_path = "/tmp/rulebooks.json"
        self._load_from_storage()
        
    def _load_from_storage(self):
        """Load vector database from Cloud Storage"""
        try:
            storage_client = storage.Client(project=self.project_id)
            bucket = storage_client.bucket("shattered-meridian-assistant-campaign-data")
            blob = bucket.blob("vector_db/rulebooks.json")
            
            if blob.exists():
                print("Loading vector database from Cloud Storage...")
                blob.download_to_filename(self.vector_store_path)
                print(f"✓ Loaded vector database ({os.path.getsize(self.vector_store_path) / 1024 / 1024:.1f} MB)")
            else:
                print("Vector database not found in Cloud Storage")
        except Exception as e:
            print(f"Could not load from Cloud Storage: {e}")
            # Fallback to local path
            local_path = "/home/jeffrey1871/dnd-dm-assistant/vector_db/rulebooks.json"
            if os.path.exists(local_path):
                self.vector_store_path = local_path
                print("Using local vector database")
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, str]]:
        """Extract text from PDF with page numbers"""
        pages = []
        print(f"Extracting text from {os.path.basename(pdf_path)}...")
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        pages.append({
                            'page_number': page_num + 1,
                            'text': text.strip(),
                            'source': os.path.basename(pdf_path)
                        })
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
        return pages
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > chunk_size * 0.5:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            chunks.append(chunk.strip())
            start = end - overlap
        return chunks
    
    def chunk_documents(self, pages: List[Dict[str, str]]) -> List[Dict[str, any]]:
        """Split pages into smaller chunks"""
        chunks = []
        for page in pages:
            page_chunks = self.chunk_text(page['text'])
            for i, chunk_text in enumerate(page_chunks):
                if len(chunk_text) > 50:
                    chunks.append({
                        'text': chunk_text,
                        'page_number': page['page_number'],
                        'source': page['source'],
                        'chunk_id': f"{page['source']}_p{page['page_number']}_c{i}"
                    })
        return chunks
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Vertex AI"""
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=[text]
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def save_to_vector_store(self, chunks: List[Dict[str, any]]):
        """Save chunks with embeddings to JSON file"""
        os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
        vector_store = []
        if os.path.exists(self.vector_store_path):
            with open(self.vector_store_path, 'r') as f:
                vector_store = json.load(f)
        
        print(f"Generating embeddings for {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks):
            if (i + 1) % 10 == 0:
                print(f"Processing chunk {i + 1}/{len(chunks)}...")
            embedding = self.get_embedding(chunk['text'])
            if embedding:
                vector_store.append({
                    'id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'source': chunk['source'],
                    'page_number': chunk['page_number'],
                    'embedding': embedding
                })
        
        with open(self.vector_store_path, 'w') as f:
            json.dump(vector_store, f)
        print(f"✓ Saved {len(vector_store)} chunks to vector store")
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        return dot_product / (magnitude1 * magnitude2)
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search the vector store"""
        if not os.path.exists(self.vector_store_path):
            print(f"Vector store not found at {self.vector_store_path}")
            return []
        
        with open(self.vector_store_path, 'r') as f:
            vector_store = json.load(f)
        
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        for item in vector_store:
            similarity = self.cosine_similarity(query_embedding, item['embedding'])
            results.append({
                'text': item['text'],
                'source': item['source'],
                'page_number': item['page_number'],
                'similarity': similarity
            })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:n_results]


def process_all_rulebooks(rulebooks_dir: str, project_id: str):
    """Process all PDFs"""
    processor = PDFProcessor(project_id)
    pdf_files = [f for f in os.listdir(rulebooks_dir) if f.endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files")
    
    all_chunks = []
    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(rulebooks_dir, pdf_file)
        print(f"\nProcessing: {pdf_file}")
        pages = processor.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(pages)} pages")
        chunks = processor.chunk_documents(pages)
        print(f"✓ Created {len(chunks)} chunks")
        all_chunks.extend(chunks)
    
    print(f"\nTOTAL: {len(all_chunks)} chunks from {len(pdf_files)} PDFs\n")
    processor.save_to_vector_store(all_chunks)
    print("\n✅ All rulebooks processed!")
