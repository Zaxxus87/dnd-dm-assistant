#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/jeffrey1871/dnd-dm-assistant/backend')

from app.rag.pdf_processor import process_all_rulebooks

if __name__ == "__main__":
    rulebooks_dir = "/home/jeffrey1871/dnd-dm-assistant/campaign-data/rulebooks"
    project_id = "shattared-meridian-assistant"
    
    print("Starting D&D Rulebook Processing...")
    print(f"Project ID: {project_id}")
    print(f"Rulebooks Directory: {rulebooks_dir}")
    print()
    
    process_all_rulebooks(rulebooks_dir, project_id)
