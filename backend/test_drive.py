from app.services.google_drive_service import GoogleDriveService

PROJECT_ID = "shattared-meridian-assistant"
TEMPLATE_ID = "1mxeHjGBSAHXAWbj_hmSZr4ACiJBAszkExB9cIv37s2s"

drive_service = GoogleDriveService(PROJECT_ID)

print("Testing Google Drive access...")
print(f"Drive service initialized: {drive_service.service is not None}")
print(f"Docs service initialized: {drive_service.docs_service is not None}")

# Try to copy the template
print("\nTrying to copy template...")
new_doc_id = drive_service.copy_template(TEMPLATE_ID, "Test NPC - DELETE ME")
print(f"New document ID: {new_doc_id}")

if new_doc_id:
    print(f"Document URL: {drive_service.get_document_url(new_doc_id)}")
    
    # Try to fill it
    print("\nTrying to fill template...")
    test_data = {
        'name': 'Test Wizard',
        'race': 'Elf',
        'class': 'Wizard',
        'alignment': 'Neutral Good'
    }
    success = drive_service.fill_npc_template(new_doc_id, test_data)
    print(f"Fill successful: {success}")
