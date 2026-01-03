import base64
import uuid
from google.cloud import storage

def save_map_to_storage(image_bytes: bytes) -> str:
    """Save map image to Cloud Storage and return public URL"""
    storage_client = storage.Client()
    bucket = storage_client.bucket("dnd-dm-assistant-web")
    
    # Generate unique filename
    filename = f"maps/map_{uuid.uuid4().hex[:8]}.png"
    blob = bucket.blob(filename)
    
    # Upload with public read access via metadata
    blob.upload_from_string(
        image_bytes, 
        content_type="image/png"
    )
    
    # Return the public URL (bucket is already public)
    public_url = f"https://storage.googleapis.com/dnd-dm-assistant-web/{filename}"
    return public_url
